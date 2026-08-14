"""TV-07 Short-term Context tests (docs/06 §13, docs/05 §7-8, docs/04 §13).

The runtime must receive a recent-conversation window, not just the current
message, and the player's name must be recoverable from that context — without
any hardcoding in the character runtime.
"""

from __future__ import annotations

import json
import re

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import RECENT_WINDOW_MESSAGES, GameOrchestrator
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider


def _valid_json(dialogue: str) -> str:
    return json.dumps(
        {
            "character_id": "deepseek",
            "dialogue": dialogue,
            "emotion": "neutral",
            "animation_proposal": "none",
            "memory_proposals": [],
            "action_proposals": [],
            "fact_refs": [],
        },
        ensure_ascii=False,
    )


class _RecordingProvider(LLMProvider):
    """Records every user prompt the runtime sends."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls.append(user)
        return _valid_json("好的。")


class _NameRecallingProvider(LLMProvider):
    """Mimics the model recalling the player's name from the transcript.

    Deterministic stand-in for the real model: if the name is present in the
    recent context it is echoed back; otherwise a placeholder is used. This
    proves the answer derives from the conversation, not from runtime state.
    """

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        match = re.search(r"Player：我叫(.+?)。", user)
        name = match.group(1) if match else "？？？"
        return _valid_json(f"我记得你叫{name}呀。")


class _CapturingRuntime(CharacterRuntime):
    """Observes exactly what the orchestrator hands to a runtime."""

    character_id = "deepseek"

    def __init__(self) -> None:
        self.requests: list[CharacterRequest] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(character_id="deepseek", dialogue="好的。")


def test_first_message_has_no_transcript():
    provider = _RecordingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(sessions, {"deepseek": DeepSeekRuntime(provider)})
    orchestrator.handle_turn(None, "这里是什么地方？")
    assert provider.calls[0] == "这里是什么地方？"


def test_second_turn_receives_first_turn_in_context():
    provider = _RecordingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(sessions, {"deepseek": DeepSeekRuntime(provider)})
    first = orchestrator.handle_turn(None, "我叫阿明。")
    orchestrator.handle_turn(first.session_id, "墙上有什么？")
    # The transcript must carry the prior player message into the next turn.
    assert "我叫阿明。" in provider.calls[1]
    # Speakers are marked so the model can tell who said what.
    assert "Player：" in provider.calls[1]
    assert "deepseek：" in provider.calls[1]


def test_orchestrator_caps_recent_conversation_to_window():
    runtime = _CapturingRuntime()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(sessions, {"deepseek": runtime})
    session_id = orchestrator.handle_turn(None, "开始").session_id
    for turn in range(1, 25):
        orchestrator.handle_turn(session_id, f"第 {turn} 句话")
    recent = runtime.requests[-1].recent_conversation
    assert len(recent) <= RECENT_WINDOW_MESSAGES
    assert len(recent) == RECENT_WINDOW_MESSAGES


def test_player_name_answered_from_conversation_not_hardcoded():
    provider = _NameRecallingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(sessions, {"deepseek": DeepSeekRuntime(provider)})
    session_id = orchestrator.handle_turn(None, "我叫阿明。").session_id
    for question in [
        "墙上有字吗？",
        "我们怎么出去？",
        "你饿吗？",
        "我好害怕。",
        "这是哪儿？",
        "你听到什么声音了吗？",
        "门上有什么？",
        "你有手机吗？",
        "别怕，我在。",
    ]:
        orchestrator.handle_turn(session_id, question)
    result = orchestrator.handle_turn(session_id, "我刚刚说我叫什么？")
    assert "阿明" in result.response.dialogue


def test_answer_tracks_the_name_in_context_not_a_constant():
    # Same fixture with a different name must yield a different answer —
    # the reply is derived from the conversation, not a hardcoded "阿明".
    provider = _NameRecallingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(sessions, {"deepseek": DeepSeekRuntime(provider)})
    session_id = orchestrator.handle_turn(None, "我叫小红。").session_id
    orchestrator.handle_turn(session_id, "墙上有什么？")
    result = orchestrator.handle_turn(session_id, "我刚刚说我叫什么？")
    assert "小红" in result.response.dialogue


def test_name_outside_window_is_dropped():
    # Once the name falls out of the recent window, it must not be recalled
    # from short-term context (that is episodic memory's job, later).
    provider = _NameRecallingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(sessions, {"deepseek": DeepSeekRuntime(provider)})
    session_id = orchestrator.handle_turn(None, "我叫阿明。").session_id
    for turn in range(1, 31):
        orchestrator.handle_turn(session_id, f"第 {turn} 句话")
    result = orchestrator.handle_turn(session_id, "我刚刚说我叫什么？")
    assert "阿明" not in result.response.dialogue
