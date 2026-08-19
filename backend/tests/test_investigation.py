"""Scene investigation runtime tests (docs/01)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.characters.base import CharacterResponse

from app.game.investigation import (
    CH1_NOTE_01,
    CH1_C02_DOOR,
    CH1_CHARACTER_REGISTRY,
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
    return GameOrchestrator(
        SessionStore(), {"deepseek": _Runtime()}, repository=repository
    )


def _trigger_0317_incident(orchestrator, session_id):
    orchestrator.handle_turn(session_id, "先看看这个房间。")
    return orchestrator.handle_turn(session_id, "我们再整理一下线索。")


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


def test_paper_visible_before_the_chapter_begins():
    # During the opening phase the scene is still binding_room, but the paper
    # (the chapter's first hotspot) is available so the player's first physical
    # interaction can begin the chapter (docs/12 §41: 自由对话 → 调查纸条 EV01).
    orchestrator = _orchestrator()
    state = orchestrator._state.state_for("sess-opening")
    assert state.chapter1.phase == "opening"
    assert [item["hotspot_id"] for item in orchestrator._investigation_state_view(state)["available_hotspots"]] == [CH1_NOTE_01]


def test_0317_hotspots_open_after_claude_appears_and_grant_fixed_evidence():
    orchestrator = _orchestrator()
    opening = orchestrator.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    assert [item["hotspot_id"] for item in opening.state["available_hotspots"]] == [CH1_NOTE_01]
    with pytest.raises(ValueError, match="03:17 incident"):
        orchestrator.handle_investigation_action(opening.session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN)
    inspected = opening
    orchestrator.handle_investigation_action(inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    incident = _trigger_0317_incident(orchestrator, inspected.session_id)
    assert [line.speaker for line in incident.script_sequence] == ["claude", "deepseek"]
    assert incident.presentation == ("SHOW_CHARACTER claude",)
    available = orchestrator.get_investigation_state(inspected.session_id)["available_hotspots"]
    assert {item["hotspot_id"] for item in available} == {
        CH1_NOTE_01, CH1_TERMINAL_MAIN, CH1_C02_DOOR, CH1_CHARACTER_REGISTRY
    }
    assert next(item for item in available if item["hotspot_id"] == CH1_TERMINAL_MAIN)["preview"]
    first = orchestrator.handle_investigation_action(
        inspected.session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )
    assert first.state["evidence_presentation"] == {
        "unlocked": True,
        "character_ids": ["claude", "deepseek"],
    }
    repeated = orchestrator.handle_investigation_action(
        first.session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )
    c02 = orchestrator.handle_investigation_action(first.session_id, INSPECT_HOTSPOT, CH1_C02_DOOR)
    registry = orchestrator.handle_investigation_action(first.session_id, INSPECT_HOTSPOT, CH1_CHARACTER_REGISTRY)

    assert first.outcome == "COMPLETED"
    assert first.evidence_id == "EV02_ADMIN_SESSION_0317"
    assert repeated.outcome == "ALREADY_COMPLETED"
    assert c02.evidence_id == "EV03_C02_RELEASE"
    assert registry.evidence_id == "EV04_CURRENT_DEEPSEEK_REGISTRY"
    assert set(registry.state["acquired_evidence"]) == {
        "EV01_NOTE_V03", "EV02_ADMIN_SESSION_0317", "EV03_C02_RELEASE", "EV04_CURRENT_DEEPSEEK_REGISTRY"
    }


def test_first_case_links_paper_claude_and_terminal_without_llm():
    orchestrator = _orchestrator()
    inspected = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    paper = orchestrator.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    incident = orchestrator.handle_turn(inspected.session_id, "03:17 到底发生了什么？")
    terminal = orchestrator.handle_investigation_action(
        inspected.session_id, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN
    )
    state = orchestrator._state.state_for(inspected.session_id)

    assert paper.presentation == ()
    assert incident.script_sequence[0].dialogue == "比上一次慢。"
    assert "claude" in state.chapter1.available_characters
    assert "claude_has_appeared" in state.narrative_flags
    assert terminal.evidence_id == "EV02_ADMIN_SESSION_0317"
    assert "FIRST_IMPOSSIBLE_EVENT_RESOLVED" in state.revealed_facts
    assert state.active_objective == "向 Claude 追问 03:17 的记录来源"


def test_discussing_0317_starts_incident_without_waiting_for_two_turns():
    orchestrator = _orchestrator()
    inspected = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    orchestrator.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )

    result = orchestrator.handle_turn(inspected.session_id, "03:17 是什么意思？")

    state = orchestrator._state.state_for(inspected.session_id)
    assert result.script_sequence[0].dialogue == "比上一次慢。"
    assert "PRE_0317_WINDOW" not in state.narrative_flags
    assert "EV_CH1_CLAUDE_APPEARS" in state.completed_events


def test_0317_incident_is_persisted_and_never_replays_after_restore(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    first = _orchestrator(repository)
    inspected = first.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    first.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )

    incident = first.handle_turn(inspected.session_id, "03:17 到底发生了什么？")
    restored = _orchestrator(repository)
    later_turn = restored.handle_turn(inspected.session_id, "继续调查。")
    history = restored.get_history(inspected.session_id)

    assert [line.dialogue for line in incident.script_sequence] == [
        "比上一次慢。",
        "……你、你怎么会在这里？！",
    ]
    assert later_turn.script_sequence == ()
    assert [message["content"] for message in history].count("比上一次慢。") == 1
    assert [message["content"] for message in history].count("……你、你怎么会在这里？！") == 1


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
