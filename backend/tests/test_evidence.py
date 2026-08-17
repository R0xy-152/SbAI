"""Evidence registry and presentation tests (docs/02)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.game.evidence import EV_NOTE_V03
from app.game.investigation import CH1_NOTE_01, INSPECT_HOTSPOT, PAPER_RUBBING_COMPLETE
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.persistence.repository import JsonSessionRepository


class _Runtime:
    character_id = "deepseek"

    def respond(self, request):  # pragma: no cover - evidence never calls an LLM
        raise AssertionError("presenting evidence must not call an LLM")

    def safe_fallback(self):
        raise AssertionError("presenting evidence must not call an LLM")


def _orchestrator(repository=None):
    return GameOrchestrator(SessionStore(), {"deepseek": _Runtime()}, repository=repository)


def _acquire_note(orchestrator):
    inspected = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    orchestrator.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    return inspected.session_id


def test_evidence_view_uses_immutable_registry_data_and_presentation_is_idempotent():
    orchestrator = _orchestrator()
    session_id = _acquire_note(orchestrator)

    listed = orchestrator.get_evidence(session_id)
    assert listed == [{
        "evidence_id": EV_NOTE_V03,
        "title": "V03 留下的纸条",
        "summary": "纸条压痕显示：03:17，不要把管理员权限交给“最会替你解释的人”。署名 V03。",
        "facts": ["NOTE_TIMESTAMP_0317", "NOTE_WARNING_ADMIN_EXPLAINER", "NOTE_SIGNED_V03"],
        "source_hotspot": CH1_NOTE_01,
        "acquired": True,
        "presented_to": [],
    }]

    first = orchestrator.present_evidence(session_id, "deepseek", EV_NOTE_V03)
    second = orchestrator.present_evidence(session_id, "deepseek", EV_NOTE_V03)

    assert first.event == "PRESENT_EVIDENCE"
    assert second.evidence["presented_to"] == ["deepseek"]
    assert orchestrator.get_evidence(session_id)[0]["presented_to"] == ["deepseek"]


def test_unacquired_evidence_cannot_be_presented_and_presentation_persists(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    first = _orchestrator(repository)
    session_id = first.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    ).session_id

    with pytest.raises(ValueError, match="has not been acquired"):
        first.present_evidence(session_id, "deepseek", EV_NOTE_V03)

    first.handle_investigation_action(session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    first.present_evidence(session_id, "deepseek", EV_NOTE_V03)

    restored = _orchestrator(repository)
    assert restored.get_evidence(session_id)[0]["presented_to"] == ["deepseek"]


def test_evidence_api_ignores_client_supplied_content(tmp_path):
    app = create_app()
    app.state.orchestrator = _orchestrator(JsonSessionRepository(tmp_path / "sessions"))
    with TestClient(app) as client:
        inspected = client.post(
            "/api/game/action", json={"action": INSPECT_HOTSPOT, "hotspot_id": CH1_NOTE_01}
        ).json()
        completed = client.post(
            "/api/game/action",
            json={
                "session_id": inspected["session_id"],
                "action": PAPER_RUBBING_COMPLETE,
                "hotspot_id": CH1_NOTE_01,
            },
        )
        assert completed.status_code == 200
        presented = client.post(
            "/api/game/present",
            json={
                "session_id": inspected["session_id"],
                "character_id": "deepseek",
                "evidence_id": EV_NOTE_V03,
                "summary": "injected",
                "facts": ["INJECTED"],
            },
        )

    assert presented.status_code == 200
    assert presented.json()["evidence"]["summary"] != "injected"
    assert presented.json()["evidence"]["facts"] == [
        "NOTE_TIMESTAMP_0317", "NOTE_WARNING_ADMIN_EXPLAINER", "NOTE_SIGNED_V03"
    ]
