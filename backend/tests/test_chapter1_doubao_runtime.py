"""Doubao observation/interpretation runtime tests (docs/06 §5)."""

from __future__ import annotations

import json

import pytest

from app.characters.base import CharacterRequest, CharacterResponse
from app.characters.doubao import DoubaoRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore
from app.game.validation import ResponseRejected, validate_response
from app.persistence.repository import JsonSessionRepository
from app.providers.base import LLMProvider


class _Provider(LLMProvider):
    def complete(self, *, system, user, max_tokens=256, response_format=None, thinking=None):
        return json.dumps(
            {
                "character_id": "doubao",
                "dialogue": "我看到日志里写着 Actor 已损坏；我猜这表示有人故意做了手脚。",
                "emotion": "serious",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
                "observed_fact_refs": ["ADMIN_ACTOR_CORRUPTED"],
                "interpretation": "有人故意做了手脚。",
            },
            ensure_ascii=False,
        )


def test_doubao_keeps_observation_and_interpretation_separate():
    response = DoubaoRuntime(_Provider()).respond(
        CharacterRequest(
            character_id="doubao",
            player_message="你怎么看这条日志？",
            presented_evidence=[
                {
                    "evidence_id": "EV_ADMIN_LOG_0317",
                    "summary": "管理员日志记录 Actor 损坏。",
                    "facts": ["ADMIN_SESSION_CREATED_AT_0317", "ADMIN_ACTOR_CORRUPTED"],
                }
            ],
        )
    )

    assert response.observed_fact_refs == ["ADMIN_ACTOR_CORRUPTED"]
    assert response.interpretation == "有人故意做了手脚。"


def test_doubao_cannot_turn_an_unseen_fact_into_an_observation():
    response = CharacterResponse(
        character_id="doubao",
        dialogue="我看到了。",
        observed_fact_refs=["CURRENT_SUBJECT_IS_PLAYER_V04"],
        interpretation="这一定很重要。",
    )
    with pytest.raises(ResponseRejected, match="not authorized to observe fact"):
        validate_response(
            response,
            character_id="doubao",
            scene=Scene(scene_id="ROOM_A", wall_code=""),
            allowed_observed_fact_ids=frozenset({"ADMIN_ACTOR_CORRUPTED"}),
        )


def test_doubao_statement_is_persisted_as_two_distinct_fields(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    orchestrator = GameOrchestrator(
        SessionStore(), {"doubao": DoubaoRuntime(_Provider())}, repository=repository
    )
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.chapter1.acquired_evidence.add("EV_ADMIN_LOG_0317")
    state.chapter1.presented_evidence["EV_ADMIN_LOG_0317"] = {"doubao"}

    orchestrator.handle_turn(session_id, "你怎么看？", character_id="doubao")

    restored = repository.load(session_id)
    assert restored is not None
    assert restored.narrative_state.chapter1.doubao_statements == [
        {
            "observed_fact_refs": ["ADMIN_ACTOR_CORRUPTED"],
            "interpretation": "有人故意做了手脚。",
        }
    ]
