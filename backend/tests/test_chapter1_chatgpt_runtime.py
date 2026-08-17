"""ChatGPT evidence-selection runtime tests (docs/06 §4)."""

from __future__ import annotations

import json

import pytest

from app.characters.base import CharacterRequest, CharacterResponse
from app.characters.chatgpt import ChatGPTRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore
from app.game.validation import ResponseRejected, validate_response
from app.persistence.repository import JsonSessionRepository
from app.providers.base import LLMProvider


class _Provider(LLMProvider):
    def __init__(self, evidence_refs: list[str]) -> None:
        self.evidence_refs = evidence_refs
        self.user = ""

    def complete(self, *, system, user, max_tokens=256, response_format=None, thinking=None):
        self.user = user
        return json.dumps(
            {
                "character_id": "chatgpt",
                "dialogue": "先从这项证据开始整理。",
                "emotion": "serious",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
                "evidence_refs": self.evidence_refs,
            },
            ensure_ascii=False,
        )


def test_chatgpt_prompt_and_response_make_evidence_order_traceable():
    provider = _Provider(["EV02_ADMIN_SESSION_0317", "EV01_NOTE_V03"])
    response = ChatGPTRuntime(provider).respond(
        CharacterRequest(
            character_id="chatgpt",
            player_message="整理一下线索。",
            presented_evidence=[
                {"evidence_id": "EV01_NOTE_V03", "summary": "纸条包含 03:17。"},
                {"evidence_id": "EV02_ADMIN_SESSION_0317", "summary": "管理员会话记录。"},
            ],
        )
    )

    assert response.evidence_refs == ["EV02_ADMIN_SESSION_0317", "EV01_NOTE_V03"]
    assert "EV01_NOTE_V03" in provider.user
    assert "EV02_ADMIN_SESSION_0317" in provider.user


def test_chatgpt_cannot_reference_evidence_that_was_not_presented():
    response = CharacterResponse(
        character_id="chatgpt",
        dialogue="我看过日志。",
        evidence_refs=["EV02_ADMIN_SESSION_0317"],
    )

    with pytest.raises(ResponseRejected, match="not authorized to reference evidence"):
        validate_response(
            response,
            character_id="chatgpt",
            scene=Scene(scene_id="ROOM_A", wall_code=""),
            allowed_evidence_ids=frozenset({"EV01_NOTE_V03"}),
        )


def test_approved_selection_is_persisted_for_later_audit(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"chatgpt": ChatGPTRuntime(_Provider(["EV01_NOTE_V03"]))},
        repository=repository,
    )
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.chapter1.acquired_evidence.add("EV01_NOTE_V03")
    state.chapter1.presented_evidence["EV01_NOTE_V03"] = {"chatgpt"}

    orchestrator.handle_turn(session_id, "整理线索。", character_id="chatgpt")

    restored = JsonSessionRepository(tmp_path / "sessions").load(session_id)
    assert restored is not None
    assert restored.narrative_state.chapter1.evidence_selections == [
        {"character_id": "chatgpt", "evidence_ids": ["EV01_NOTE_V03"]}
    ]
