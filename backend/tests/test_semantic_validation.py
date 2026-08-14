"""Semantic Validation Gate tests (docs/04 §47-51).

Schema Validation only checks shape; the gate checks *permissibility*. These
tests pin the gate as a hard boundary, not a prompt preference: a well-formed
response that cites an unknown fact, reaches for DeepSeek's forbidden visual
truth, or proposes a disallowed action is rejected before it can touch
History, Memory, Game State or the Frontend.
"""

from __future__ import annotations

import json

import pytest

from app.characters.base import ActionProposal, CharacterResponse
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore
from app.game.validation import ResponseRejected, validate_response
from app.narrative import signals
from app.narrative.interpreter import Interpretation
from app.narrative.poc import build_poc_events
from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider

BINDING_ROOM = Scene(scene_id="binding_room")  # wall_code "0317"


def _response(**overrides) -> CharacterResponse:
    base = dict(
        character_id="deepseek",
        dialogue="嗯，我再想想。",
        emotion="neutral",
        animation_proposal="none",
        memory_proposals=[],
        action_proposals=[],
        fact_refs=[],
    )
    base.update(overrides)
    return CharacterResponse(**base)


# --- Character / Narrative Validation, unit level ---------------------------


def test_valid_response_passes():
    # A response that stays inside its permissions is approved.
    validate_response(_response(), character_id="deepseek", scene=BINDING_ROOM)


def test_wrong_character_rejected():
    response = _response(character_id="claude")
    with pytest.raises(ResponseRejected):
        validate_response(response, character_id="deepseek", scene=BINDING_ROOM)


def test_unknown_fact_ref_rejected():
    # F_SECRET is not in DeepSeek's authorized facts, so citing it is rejected.
    response = _response(fact_refs=["F_SECRET"])
    with pytest.raises(ResponseRejected):
        validate_response(response, character_id="deepseek", scene=BINDING_ROOM)


def test_deepseek_visual_fact_rejected():
    # DeepSeek cannot see; naming the wall code means she was handed it out of
    # band, so the reply is rejected even though it is schema-valid.
    response = _response(dialogue="墙上的密码是0317")
    with pytest.raises(ResponseRejected):
        validate_response(response, character_id="deepseek", scene=BINDING_ROOM)


def test_claude_may_know_visual_fact():
    # Claude is not blind (docs/04 §35-39): the same line is legal for her.
    response = _response(character_id="claude", dialogue="墙上的密码是0317")
    validate_response(response, character_id="claude", scene=BINDING_ROOM)


def test_disallowed_action_rejected():
    # No self-proposed action is allowed in this MVP; only a Narrative Event
    # may change state (docs/03 §28).
    response = _response(action_proposals=[ActionProposal(type="change_scene")])
    with pytest.raises(ResponseRejected):
        validate_response(response, character_id="deepseek", scene=BINDING_ROOM)


# --- Orchestrator: rejected content never enters any sink -------------------


class _FixedProvider(LLMProvider):
    """Returns one fixed, schema-valid raw response and counts its calls."""

    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.calls = 0

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls += 1
        return self._raw


class _FixedInterpreter:
    def __init__(self, signal: str) -> None:
        self._signal = signal

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        return Interpretation(self._signal)


# A response that is *schema-valid* but semantically impermissible: it cites
# F_SECRET (unknown to DeepSeek) and names the visual wall code in prose.
INVALID_RAW = json.dumps(
    {
        "character_id": "deepseek",
        "dialogue": "墙上的密码是0317",
        "emotion": "neutral",
        "animation_proposal": "none",
        "memory_proposals": [{"type": "fear", "content": "Player怕黑"}],
        "action_proposals": [],
        "fact_refs": ["F_SECRET"],
    },
    ensure_ascii=False,
)


def test_rejected_response_never_enters_history_memory_state():
    provider = _FixedProvider(INVALID_RAW)
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    orchestrator = GameOrchestrator(
        store,
        {"deepseek": DeepSeekRuntime(provider)},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )

    result = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")

    # The rejected reply is replaced by the safe fallback, not the illegal line.
    assert result.response.dialogue == "……等一下，我脑子有点卡住了。"

    # History contains only the player message and the fallback reply; neither
    # the wall code nor the secret fact id leaks into what was recorded.
    history = orchestrator.get_history(session_id)
    for message in history:
        assert "0317" not in message["content"]
        assert "F_SECRET" not in message["content"]
    assert "墙上的密码" not in " ".join(m["content"] for m in history)

    # The memory proposal (Player怕黑) was not written.
    assert orchestrator._memory_store(session_id).retrieve("deepseek") == []

    # The selected event did not commit: no flag, no completed event, and no
    # presentation directive reaches the frontend.
    state = orchestrator._narrative_states[session_id]
    assert "claude_has_appeared" not in state.narrative_flags
    assert state.completed_events == set()
    assert result.presentation == ()
