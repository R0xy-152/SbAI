"""Evidence registry and presentation tests (docs/02)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.characters.base import CharacterResponse

from app.game.evidence import (
    EV01_NOTE_V03,
    EV02_ADMIN_SESSION_0317,
    EVIDENCE_REGISTRY,
    GROUND_TRUTH_REGISTRY,
)
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

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="继续调查。")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


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


def _unlock_evidence_presentation(orchestrator, session_id):
    orchestrator.handle_turn(session_id, "继续调查。")
    orchestrator.handle_turn(session_id, "再看看别处。")
    return orchestrator.handle_investigation_action(
        session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )


def test_evidence_view_uses_immutable_registry_data_and_presentation_is_idempotent():
    orchestrator = _orchestrator()
    session_id = _acquire_note(orchestrator)

    listed = orchestrator.get_evidence(session_id)
    assert listed == [{
        "evidence_id": EV01_NOTE_V03,
        "title": "压痕纸条",
        "summary": "03:17\n\n不要把管理员权限交给‘最会替你解释的人’。\n\n—— V03",
        "facts": ["NOTE_TIMESTAMP_0317", "NOTE_WARNING_ADMIN_EXPLAINER", "NOTE_SIGNED_V03"],
        "source_hotspot": "paper_rubbing",
        "acquired": True,
        "presented_to": [],
    }]

    with pytest.raises(ValueError, match="not unlocked"):
        orchestrator.present_evidence(session_id, "deepseek", EV01_NOTE_V03)

    _unlock_evidence_presentation(orchestrator, session_id)
    first = orchestrator.present_evidence(session_id, "deepseek", EV01_NOTE_V03)
    second = orchestrator.present_evidence(session_id, "deepseek", EV01_NOTE_V03)

    assert first.event == "PRESENT_EVIDENCE"
    assert second.evidence["presented_to"] == ["deepseek"]
    assert orchestrator.get_evidence(session_id)[0]["presented_to"] == ["deepseek"]


def test_first_chapter_evidence_and_ground_truth_ids_are_fixed():
    assert set(EVIDENCE_REGISTRY) == {f"EV{index:02d}_{suffix}" for index, suffix in (
        (1, "NOTE_V03"), (2, "ADMIN_SESSION_0317"), (3, "C02_RELEASE"),
        (4, "CURRENT_DEEPSEEK_REGISTRY"), (5, "ARCHIVED_ACTOR_FRAGMENT"),
        (6, "SESSION_REPLAY_MARKER"), (7, "CLAUDE_RECOVERY_ACCESS"),
        (8, "GPT_RECOVERY_SERVICE"), (9, "CURRENT_PLAYER_SUBJECT"),
        (10, "GPT_FIRST_SUMMARY"), (11, "GPT_SECOND_SUMMARY"),
    )}
    assert EVIDENCE_REGISTRY[EV02_ADMIN_SESSION_0317].facts == (
        "ADMIN_SESSION_CREATED_AT_0317",
        "C02_RELEASED_AT_0317",
        "ADMIN_ACTOR_PARTIAL",
    )
    assert GROUND_TRUTH_REGISTRY["CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK"].value == "true"
    assert GROUND_TRUTH_REGISTRY["CURRENT_SUBJECT_IS_PLAYER_V04"].value == "true"


def test_unacquired_evidence_cannot_be_presented_and_presentation_persists(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    first = _orchestrator(repository)
    session_id = first.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    ).session_id

    with pytest.raises(ValueError, match="has not been acquired"):
        first.present_evidence(session_id, "deepseek", EV01_NOTE_V03)

    first.handle_investigation_action(session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    _unlock_evidence_presentation(first, session_id)
    first.present_evidence(session_id, "deepseek", EV01_NOTE_V03)

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
        locked = client.post(
            "/api/game/present",
            json={
                "session_id": inspected["session_id"],
                "character_id": "deepseek",
                "evidence_id": EV01_NOTE_V03,
            },
        )
        assert locked.status_code == 400
        for message in ("继续调查。", "再看看别处。"):
            progressed = client.post(
                "/api/chat",
                json={"session_id": inspected["session_id"], "message": message},
            )
            assert progressed.status_code == 200
        terminal = client.post(
            "/api/game/action",
            json={
                "session_id": inspected["session_id"],
                "action": INSPECT_HOTSPOT,
                "hotspot_id": CH1_TERMINAL_MAIN,
            },
        )
        assert terminal.status_code == 200
        presented = client.post(
            "/api/game/present",
            json={
                "session_id": inspected["session_id"],
                "character_id": "deepseek",
                "evidence_id": EV01_NOTE_V03,
                "summary": "injected",
                "facts": ["INJECTED"],
            },
        )

    assert presented.status_code == 200
    assert presented.json()["evidence"]["summary"] != "injected"
    assert presented.json()["evidence"]["facts"] == [
        "NOTE_TIMESTAMP_0317", "NOTE_WARNING_ADMIN_EXPLAINER", "NOTE_SIGNED_V03"
    ]


def test_chat_api_returns_formal_0317_sequence(tmp_path):
    app = create_app()
    app.state.orchestrator = _orchestrator(JsonSessionRepository(tmp_path / "sessions"))
    with TestClient(app) as client:
        inspected = client.post(
            "/api/game/action", json={"action": INSPECT_HOTSPOT, "hotspot_id": CH1_NOTE_01}
        ).json()
        client.post(
            "/api/game/action",
            json={
                "session_id": inspected["session_id"],
                "action": PAPER_RUBBING_COMPLETE,
                "hotspot_id": CH1_NOTE_01,
            },
        )
        incident = client.post(
            "/api/chat",
            json={"session_id": inspected["session_id"], "message": "03:17 是什么意思？"},
        )

    assert incident.status_code == 200
    assert incident.json()["presentation"] == ["SHOW_CHARACTER claude"]
    assert incident.json()["script_sequence"] == [
        {"speaker": "claude", "dialogue": "比上一次慢。", "emotion": "serious", "animation": "fade_in"},
        {"speaker": "deepseek", "dialogue": "……你、你怎么会在这里？！", "emotion": "annoyed", "animation": "none"},
    ]
