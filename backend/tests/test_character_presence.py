"""Presence Gate tests (docs/03 §13.6): who the player may talk to is a
deterministic backend fact, decided outside the Narrative Runtime and never by
the Frontend.

A gated character (Claude) is only interactable once the Narrative Event
commits ``claude_has_appeared``. Before that, a direct ``character_id=claude``
request — even one that bypasses the UI — is rejected Fail Closed (403 through
the API, no message / no state / no current_character recorded). DeepSeek is
never gated. A refresh restores the flag from persisted Narrative State, so the
unlocked character stays unlocked.

The gate is opt-in: ``GameOrchestrator(..., availability={...})``. Every other
orchestrator in the test suite constructs without it and keeps pre-gate
behaviour.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import CharacterUnavailable, GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.narrative import signals
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.poc import EV_POC_CLAUDE_APPEARS, build_poc_events
from app.persistence.repository import JsonSessionRepository
from app.providers.base import LLMProvider


class _PresenceProvider(LLMProvider):
    """Deterministic provider: maps captor questions to SIG_ASK_CAPTOR and
    answers every character call with schema-valid structured output."""

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
    ) -> str:
        if "剧情理解器" in system:
            signal = signals.SIG_ASK_CAPTOR if "抓" in user else signals.OUTCOME_NOOP
            return json.dumps({"signal": signal})
        character_id = "claude" if "角色 Claude" in system else "deepseek"
        return json.dumps(
            {
                "character_id": character_id,
                "dialogue": f"{character_id}回应",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


def _build_orchestrator(provider: LLMProvider, repo: JsonSessionRepository) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": DeepSeekRuntime(provider),
            "claude": ClaudeRuntime(provider),
        },
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
        repository=repo,
        availability={"claude": "claude_has_appeared"},
    )


def _post(client: TestClient, message: str, session_id: str | None, character_id: str | None = None):
    payload = {"message": message, "session_id": session_id}
    if character_id is not None:
        payload["character_id"] = character_id
    return client.post("/api/chat", json=payload)


def _history(client: TestClient, session_id: str) -> list[dict]:
    return client.get(f"/api/chat/history?session_id={session_id}").json()["messages"]


def test_claude_rejected_before_appearance(tmp_path):
    """A fresh session: DeepSeek speaks, but a direct claude request is 403
    and records nothing (Fail Closed)."""
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _PresenceProvider()
    app = create_app()
    app.state.orchestrator = _build_orchestrator(provider, repo)

    with TestClient(app) as client:
        # DeepSeek is ungated and answers from the very first turn.
        first = _post(client, "你好", None)
        assert first.status_code == 200
        session_id = first.json()["session_id"]
        assert first.json()["character_id"] == "deepseek"

        # Direct request for the gated character is rejected, 403.
        blocked = _post(client, "Claude，出来。", session_id, "claude")
        assert blocked.status_code == 403, blocked.json()
        assert "claude" in blocked.json()["detail"]

        # The rejected turn touched nothing: history still has exactly the one
        # DeepSeek exchange (1 player + 1 character), no claude message.
        messages = _history(client, session_id)
        assert [m["role"] for m in messages] == ["player", "character"]
        assert messages[1]["character_id"] == "deepseek"


def test_claude_rejected_on_very_first_request(tmp_path):
    """An entirely fresh session whose first ever message names claude is still
    rejected — the Frontend cannot make a character appear by asking."""
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _PresenceProvider()
    app = create_app()
    app.state.orchestrator = _build_orchestrator(provider, repo)

    with TestClient(app) as client:
        blocked = _post(client, "你好 Claude", None, "claude")
        assert blocked.status_code == 403, blocked.json()


def test_claude_available_after_appearance(tmp_path):
    """Once EV_POC_CLAUDE_APPEARS commits, the flag flips and claude can speak."""
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _PresenceProvider()
    app = create_app()
    app.state.orchestrator = _build_orchestrator(provider, repo)

    with TestClient(app) as client:
        first = _post(client, "你好", None)
        session_id = first.json()["session_id"]

        # Trigger the narrative signal → the event commits `claude_has_appeared`.
        trigger = _post(client, "那你知道是谁把我们抓来的吗？", session_id)
        assert trigger.status_code == 200
        assert trigger.json()["presentation"] == ["SHOW_CHARACTER claude"]

        # Now the gate is open.
        ok = _post(client, "Claude，原来是你。", session_id, "claude")
        assert ok.status_code == 200, ok.json()
        assert ok.json()["character_id"] == "claude"

    state = repo.load(session_id)
    assert state is not None
    assert state.narrative_state.narrative_flags == {"claude_has_appeared"}
    assert state.narrative_state.completed_events == {EV_POC_CLAUDE_APPEARS}


def test_claude_availability_survives_refresh(tmp_path):
    """A fresh process over the same repository restores the flag, so the
    already-appeared Claude stays interactable (docs/06 §20 Session Restore)."""
    repo = JsonSessionRepository(tmp_path / "sessions")

    provider1 = _PresenceProvider()
    app1 = create_app()
    app1.state.orchestrator = _build_orchestrator(provider1, repo)
    with TestClient(app1) as client:
        first = _post(client, "你好", None)
        session_id = first.json()["session_id"]
        _post(client, "那你知道是谁把我们抓来的吗？", session_id)

    # "Refresh": a brand-new orchestrator over the same repo, same session_id.
    provider2 = _PresenceProvider()
    app2 = create_app()
    app2.state.orchestrator = _build_orchestrator(provider2, repo)
    with TestClient(app2) as client:
        ok = _post(client, "Claude，我回来了。", session_id, "claude")
        assert ok.status_code == 200, ok.json()
        assert ok.json()["character_id"] == "claude"


def test_gate_is_opt_in(tmp_path):
    """Without ``availability`` the orchestrator never gates — existing tests
    and code that construct the orchestrator directly are unaffected."""
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _PresenceProvider()
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"claude": ClaudeRuntime(provider)},
        default_character="claude",
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
        repository=repo,
    )
    # No flag, no gate: claude answers immediately.
    result = orchestrator.handle_turn(None, "你好", "claude")
    assert result.response.character_id == "claude"

    # And CharacterUnavailable is its own exception type, not a ValueError, so
    # it never collides with the ValueError → 400 mapping in the API layer.
    assert not issubclass(CharacterUnavailable, ValueError)
