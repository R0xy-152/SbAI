"""Scene investigation runtime tests (docs/01)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.game.investigation import (
    CH1_NOTE_01,
    CH1_TERMINAL_MAIN,
    INSPECT_HOTSPOT,
    PAPER_RUBBING_COMPLETE,
)
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.persistence.repository import JsonSessionRepository


class _Runtime:
    character_id = "deepseek"

    def respond(self, request):  # pragma: no cover - investigation never calls it
        raise AssertionError("scene investigation must not call an LLM")

    def safe_fallback(self):
        raise AssertionError("scene investigation must not call an LLM")


def _orchestrator(repository=None):
    return GameOrchestrator(
        SessionStore(), {"deepseek": _Runtime()}, repository=repository
    )


def test_paper_completion_requires_investigation_and_grants_evidence_once():
    orchestrator = _orchestrator()
    first = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )

    assert first.outcome == "INVESTIGATED"
    assert first.state["acquired_evidence"] == []
    complete = orchestrator.handle_investigation_action(
        first.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    repeated = orchestrator.handle_investigation_action(
        first.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )

    assert complete.evidence_id == "EV01_NOTE_V03"
    assert complete.state["hotspots"][CH1_NOTE_01] == "completed"
    assert complete.state["acquired_evidence"] == ["EV01_NOTE_V03"]
    assert repeated.outcome == "ALREADY_COMPLETED"
    assert repeated.state["acquired_evidence"] == ["EV01_NOTE_V03"]


def test_completion_before_investigation_fails_closed():
    with pytest.raises(ValueError):
        _orchestrator().handle_investigation_action(
            None, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
        )


def test_terminal_log_is_acquired_once_by_actual_investigation():
    orchestrator = _orchestrator()
    first = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )
    repeated = orchestrator.handle_investigation_action(
        first.session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )

    assert first.outcome == "COMPLETED"
    assert first.evidence_id == "EV02_ADMIN_SESSION_0317"
    assert first.state["acquired_evidence"] == ["EV02_ADMIN_SESSION_0317"]
    assert repeated.outcome == "ALREADY_COMPLETED"
    assert repeated.state["acquired_evidence"] == ["EV02_ADMIN_SESSION_0317"]


def test_first_case_links_paper_claude_and_terminal_without_llm():
    orchestrator = _orchestrator()
    inspected = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    paper = orchestrator.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    terminal = orchestrator.handle_investigation_action(
        inspected.session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )
    state = orchestrator._state.state_for(inspected.session_id)

    assert paper.presentation == ("SHOW_CHARACTER claude",)
    assert "claude" in state.chapter1.available_characters
    assert "claude_has_appeared" in state.narrative_flags
    assert terminal.evidence_id == "EV02_ADMIN_SESSION_0317"
    assert "FIRST_IMPOSSIBLE_EVENT_RESOLVED" in state.revealed_facts
    assert state.active_objective == "向 Claude 追问 03:17 的记录来源"


def test_hotspot_state_survives_repository_restore(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    first = _orchestrator(repository)
    inspected = first.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    first.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )

    restored = _orchestrator(repository).get_investigation_state(
        inspected.session_id
    )

    assert restored["hotspots"][CH1_NOTE_01] == "completed"
    assert restored["acquired_evidence"] == ["EV01_NOTE_V03"]


def test_action_api_only_accepts_allow_listed_hotspot_actions(tmp_path):
    app = create_app()
    app.state.orchestrator = _orchestrator(JsonSessionRepository(tmp_path / "sessions"))

    with TestClient(app) as client:
        inspected = client.post(
            "/api/game/action",
            json={"action": INSPECT_HOTSPOT, "hotspot_id": CH1_NOTE_01},
        )
        assert inspected.status_code == 200
        body = inspected.json()
        completed = client.post(
            "/api/game/action",
            json={
                "session_id": body["session_id"],
                "action": PAPER_RUBBING_COMPLETE,
                "hotspot_id": CH1_NOTE_01,
                "evidence_id": "EV_INJECTED_BY_CLIENT",
            },
        )

    assert completed.status_code == 200
    assert completed.json()["evidence_id"] == "EV01_NOTE_V03"
