"""Narrative Directive tests (docs/03 §24, docs/04 §14, §18.4).

When a Narrative Event is selected, the current character receives a
Narrative Directive — the per-turn story goal this reply must carry. The
directive is authored on the Event, flows through the Narrative Decision into
CharacterRequest.narrative_directive, and is rendered by the Prompt Builder
between the authorized context and the conversation. Ordinary turns carry no
directive. A directive is text, never a Game State mutation: it states the
goal / allowed scope / forbidden reveals without prescribing exact lines.
"""

from __future__ import annotations

import json

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative import signals
from app.narrative.events import NarrativeEvent
from app.narrative.interpreter import Interpretation
from app.narrative.poc import build_poc_events
from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider


class _RecordingRuntime(CharacterRuntime):
    """Records every CharacterRequest it receives."""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        self.requests: list[CharacterRequest] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(character_id=self.character_id, dialogue="……")


class _FixedInterpreter:
    def __init__(self, signal: str) -> None:
        self._signal = signal

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        return Interpretation(self._signal)


class _RecordingProvider(LLMProvider):
    """Answers valid structured output and records every user prompt."""

    def __init__(self) -> None:
        self.users: list[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.users.append(user)
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": "好的。",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


def _orchestrator(runtimes, interpreter=None, events=()):
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    return GameOrchestrator(store, runtimes, interpreter=interpreter, events=events), session_id


def test_character_request_default_directive_is_empty():
    request = CharacterRequest(character_id="deepseek", player_message="你好")
    assert request.narrative_directive == ""


def test_event_directive_flows_to_character_request():
    # The captor question selects EV_POC_CLAUDE_APPEARS; its authored directive
    # reaches the current character as a bounded instruction, not a state dump.
    runtime = _RecordingRuntime("deepseek")
    orchestrator, session_id = _orchestrator(
        {"deepseek": runtime},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert "过渡到 Claude 的出现" in runtime.requests[0].narrative_directive
    assert "不得提前透露" in runtime.requests[0].narrative_directive


def test_noop_turn_has_no_directive():
    runtime = _RecordingRuntime("deepseek")
    orchestrator, session_id = _orchestrator(
        {"deepseek": runtime},
        interpreter=_FixedInterpreter(signals.OUTCOME_NOOP),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "随便聊聊")
    assert runtime.requests[0].narrative_directive == ""


def test_directive_reaches_switched_character():
    # Criterion 2 is about the *current* character, not the default one: when a
    # player switches to Claude and the event fires, Claude — not DeepSeek —
    # receives the directive.
    deepseek = _RecordingRuntime("deepseek")
    claude = _RecordingRuntime("claude")
    orchestrator, session_id = _orchestrator(
        {"deepseek": deepseek, "claude": claude},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？", character_id="claude")
    assert "过渡到 Claude 的出现" in claude.requests[0].narrative_directive
    assert not deepseek.requests


def test_directive_reaches_the_prompt():
    # The Prompt Builder renders the directive between the authorized context
    # and the conversation (docs/04 §18), so the model actually sees it.
    provider = _RecordingProvider()
    orchestrator, session_id = _orchestrator(
        {"deepseek": DeepSeekRuntime(provider)},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert "本轮叙事指令" in provider.users[0]
    assert "过渡到 Claude 的出现" in provider.users[0]


def test_ordinary_chat_prompt_has_no_directive():
    provider = _RecordingProvider()
    orchestrator, session_id = _orchestrator(
        {"deepseek": DeepSeekRuntime(provider)},
        interpreter=_FixedInterpreter(signals.OUTCOME_NOOP),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "随便聊聊")
    assert "本轮叙事指令" not in provider.users[0]


def test_directive_does_not_inject_hidden_facts_into_prompt():
    # Criterion 5: the directive states the goal and forbids early reveals
    # WITHOUT itself carrying hidden plot or future Facts. The rendered DeepSeek
    # prompt must not contain the visual ground truth or Claude's hidden role.
    provider = _RecordingProvider()
    orchestrator, session_id = _orchestrator(
        {"deepseek": DeepSeekRuntime(provider)},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    prompt = provider.users[0]
    assert "0317" not in prompt  # visual ground truth never reaches DeepSeek
    assert "反派" not in prompt  # Claude's hidden role stays hidden
    assert "幕后" not in prompt
    # The directive forbids the reveal without naming what is hidden.
    assert "不得提前透露" in prompt


def test_directive_does_not_modify_state():
    # A directive that says "让 Claude 出现" is an instruction, not an Effect:
    # with empty effects the event records only its own id and no flag / scene
    # / fact / objective moves (docs/03 §24 — only an Effect can write Game
    # State; a directive is text that reaches the character, not the state).
    runtime = _RecordingRuntime("deepseek")
    event = NarrativeEvent(
        event_id="EV_DIRECTIVE_ONLY",
        trigger_signals=frozenset({"SIG_TEST"}),
        directive="本轮需要让 Claude 出现。",
        effects=(),
    )
    orchestrator, session_id = _orchestrator(
        {"deepseek": runtime},
        interpreter=_FixedInterpreter("SIG_TEST"),
        events=[event],
    )
    orchestrator.handle_turn(session_id, "测试")
    state = orchestrator._narrative_states[session_id]
    assert runtime.requests[0].narrative_directive == "本轮需要让 Claude 出现。"
    # The directive reached the character but moved no narrative content.
    assert state.completed_events == {"EV_DIRECTIVE_ONLY"}  # event id is tracked
    assert state.narrative_flags == set()
    assert state.current_scene == "binding_room"
    assert state.story_phase == "prologue"
    assert state.revealed_facts == set()
    assert state.active_objective is None
