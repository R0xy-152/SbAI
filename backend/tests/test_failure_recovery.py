"""TV-15 Failure Recovery tests (docs/06 §21).

A single external-model or generation failure must not destroy the session.
The three required cases:

  Case A  Provider Timeout        → recoverable ProviderError, nothing committed
  Case B  Invalid Structured Output → repair → safe fallback, nothing leaks
  Case C  空Response               → provider-empty → recoverable; empty-dialogue
                                    JSON → safe fallback

The docs/06 §21 PASS contract, asserted for each case:
  - Game State不被错误提交
  - Completed Event不被提前写入
  - Invalid内容不进入正式Memory
  - Player得到可恢复反馈
  - Retry后Session可以继续
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.narrative import signals
from app.narrative.interpreter import Interpretation
from app.narrative.poc import build_poc_events
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository
from app.providers.base import LLMProvider, ProviderError
from app.providers.mock import MockProvider


class _FixedInterpreter:
    def __init__(self, signal: str) -> None:
        self._signal = signal

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        return Interpretation(self._signal)


class _FlakyRuntime(CharacterRuntime):
    """Succeeds except on the `fail_on_turn`-th call (docs/04 §55 recoverable)."""

    character_id = "deepseek"

    def __init__(self, fail_on_turn: int = 1) -> None:
        self.fail_on_turn = fail_on_turn
        self.count = 0

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.count += 1
        if self.count == self.fail_on_turn:
            raise ProviderError("timeout (injected)")
        return CharacterResponse(character_id="deepseek", dialogue="……")


class _RecordingFlakyRuntime(CharacterRuntime):
    """Fails on the second respond call, and records each recent conversation
    so a test can assert what short-term context the character actually saw."""

    character_id = "deepseek"

    def __init__(self) -> None:
        self.count = 0
        self.recent: list[list[dict]] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.count += 1
        self.recent.append(request.recent_conversation)
        if self.count == 2:
            raise ProviderError("timeout (injected)")
        return CharacterResponse(character_id="deepseek", dialogue="……")


class _FlakyProvider(LLMProvider):
    """Answers valid structured output except on the `fail_on_call`-th call."""

    def __init__(self, fail_on_call: int = 2) -> None:
        self.fail_on_call = fail_on_call
        self.count = 0

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
    ) -> str:
        self.count += 1
        if self.count == self.fail_on_call:
            raise ProviderError("timeout (injected)")
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": f"模拟回复：{user}",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


class _EmptyDialogueProvider(LLMProvider):
    """Valid structured JSON whose dialogue is empty (Case C)."""

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
    ) -> str:
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": "",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            }
        )


def _orchestrator(
    runtime: CharacterRuntime,
    signal: str = signals.OUTCOME_NOOP,
    repo: JsonSessionRepository | None = None,
):
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    return (
        GameOrchestrator(
            store,
            {"deepseek": runtime},
            interpreter=_FixedInterpreter(signal),
            events=build_poc_events(),
            repository=repo,
        ),
        session_id,
    )


# ---- Case A: Provider Timeout (recoverable failure) ----

def test_case_a_timeout_does_not_commit_and_retry_continues():
    # The failed turn would have fired EV_POC_CLAUDE_APPEARS; it must not.
    orchestrator, session_id = _orchestrator(
        _FlakyRuntime(fail_on_turn=1), signal=signals.SIG_ASK_CAPTOR
    )
    with pytest.raises(ProviderError):  # Player gets a recoverable error
        orchestrator.handle_turn(session_id, "是谁把我们抓来的？")

    # Game State不被错误提交 / Completed Event不被提前写入.
    state = orchestrator._state.state_for(session_id)
    assert state.narrative_flags == set()
    assert state.completed_events == set()

    # Retry后Session可以继续: the same turn now fires the event correctly.
    turn = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert turn.session_id == session_id
    # The failed attempt recorded no player message, so this is turn 1.
    assert turn.message_count == 1
    state = orchestrator._state.state_for(session_id)
    assert "claude_has_appeared" in state.narrative_flags
    assert "EV_POC_CLAUDE_APPEARS" in state.completed_events


def test_failed_turn_records_nothing_and_retry_does_not_duplicate():
    # A failed turn must leave no player or character message in history, so a
    # retry records the player message exactly once (docs/05 §8).
    orchestrator, session_id = _orchestrator(
        _FlakyRuntime(fail_on_turn=1), signal=signals.SIG_ASK_CAPTOR
    )
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    # The failed turn wrote nothing into the history.
    assert orchestrator._sessions.get(session_id).messages == []

    turn = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert turn.message_count == 1
    messages = orchestrator._sessions.get(session_id).messages
    assert [m["role"] for m in messages] == ["player", "character"]
    assert messages[0]["content"] == "是谁把我们抓来的？"


def test_failed_player_message_not_in_recent_context():
    # The failed player message must not leak into a later turn's short-term
    # context (docs/05 §8): the window only carries committed turns.
    runtime = _RecordingFlakyRuntime()
    orchestrator, session_id = _orchestrator(runtime)
    orchestrator.handle_turn(session_id, "成功的第一句")
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session_id, "失败的这句")
    orchestrator.handle_turn(session_id, "成功的第三句")

    recent_contents = [m["content"] for m in runtime.recent[-1]]
    assert "成功的第一句" in recent_contents
    assert "失败的这句" not in recent_contents


def test_case_a_recovery_then_persist_then_restore(tmp_path):
    # The same recovery also holds with persistence (TV-14): only the
    # successful turn persists, and a fresh orchestrator restores it.
    repo = JsonSessionRepository(tmp_path / "sessions")
    orchestrator, session_id = _orchestrator(
        _FlakyRuntime(fail_on_turn=1), signal=signals.SIG_ASK_CAPTOR, repo=repo
    )
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert repo.load(session_id) is None  # the failed turn wrote nothing

    turn = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    # The failed attempt recorded no player message, so this is turn 1.
    assert turn.message_count == 1
    persisted = repo.load(session_id)
    assert persisted is not None
    assert "EV_POC_CLAUDE_APPEARS" in persisted.narrative_state.completed_events

    # A fresh orchestrator restores the committed event and will not re-fire it.
    fresh = GameOrchestrator(
        SessionStore(),
        {"deepseek": _FlakyRuntime(fail_on_turn=99)},  # never fails on this short run
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
        repository=repo,
    )
    fresh.handle_turn(session_id, "随便聊聊")
    restored = fresh._state.state_for(session_id)
    assert restored.completed_events == {"EV_POC_CLAUDE_APPEARS"}


# ---- Case B: Invalid Structured Output ----

def test_case_b_invalid_output_falls_back_clean():
    # The model answers with non-JSON prose every time → repair fails → the
    # player gets the safe fallback line, never the invalid content.
    runtime = DeepSeekRuntime(MockProvider(malformed=True))
    orchestrator, session_id = _orchestrator(runtime)

    turn = orchestrator.handle_turn(session_id, "你好")
    assert turn.response.dialogue == DeepSeekRuntime.fallback_lines[0]

    # Invalid内容不进入正式Memory / history.
    assert orchestrator._memory.store_for(session_id).retrieve("deepseek") == []
    messages = orchestrator._sessions.get(session_id).messages
    assert not any("没听清" in m.get("content", "") for m in messages)

    # No narrative state was committed (noop signal; nothing leaked).
    state = orchestrator._state.state_for(session_id)
    assert state.narrative_flags == set()
    assert state.completed_events == set()

    # Retry后Session可以继续.
    next_turn = orchestrator.handle_turn(session_id, "在吗")
    assert next_turn.message_count == 2
    assert next_turn.session_id == session_id


# ---- Case C: 空Response ----

def test_case_c_empty_dialogue_falls_back_clean():
    # Valid JSON whose dialogue is empty → schema validation rejects it →
    # repair fails (same empty dialogue) → safe fallback. Nothing leaks.
    runtime = DeepSeekRuntime(_EmptyDialogueProvider())
    orchestrator, session_id = _orchestrator(runtime)

    turn = orchestrator.handle_turn(session_id, "你好")
    assert turn.response.dialogue == DeepSeekRuntime.fallback_lines[0]
    assert orchestrator._memory.store_for(session_id).retrieve("deepseek") == []

    next_turn = orchestrator.handle_turn(session_id, "继续")
    assert next_turn.message_count == 2
    assert next_turn.session_id == session_id


def test_case_c_empty_provider_content_is_recoverable():
    # The DeepSeek adapter raises ProviderError for empty content (see
    # test_provider_deepseek.py); through the orchestrator that is a
    # recoverable failure, not a destroyed session.
    runtime = DeepSeekRuntime(MockProvider(fail=True))
    orchestrator, session_id = _orchestrator(runtime)
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session_id, "你好")
    assert orchestrator._state.state_for(session_id).completed_events == set()


# ---- API level: recoverable feedback + retry continues the same session ----

def test_api_503_then_retry_continues_same_session(monkeypatch):
    monkeypatch.setenv("GAL_PROVIDER", "mock")
    app = create_app()
    app.state.orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(_FlakyProvider(fail_on_call=2))},
    )
    with TestClient(app) as client:
        first = client.post("/api/chat", json={"message": "你好"})
        assert first.status_code == 200
        session_id = first.json()["session_id"]

        # A mid-session failure surfaces as a recoverable 503 — never a
        # fabricated reply (docs/04 §55).
        second = client.post(
            "/api/chat", json={"message": "第二句", "session_id": session_id}
        )
        assert second.status_code == 503

        # Retry with the known session id continues the SAME session.
        third = client.post(
            "/api/chat", json={"message": "第二句", "session_id": session_id}
        )
        assert third.status_code == 200
        body = third.json()
        assert body["session_id"] == session_id
        # The failed mid-session turn recorded no player message, so only the
        # first and the successful retry count: "你好" + "第二句" = 2.
        assert body["message_count"] == 2
