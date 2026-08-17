"""Claim / contradiction / inference tests (docs/04)."""

from app.game.deduction import (
    C_CLAUDE_SOURCE_01,
    CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK,
    CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK,
    INF_OLD_INSTANCE_RECORD,
    submit_deduction,
)
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository, PersistedSession


def test_contradiction_requires_the_exact_recorded_claim_combination():
    state = NarrativeState()
    message = "你说没看到 DeepSeek 本人，那你为什么说是她开的？"
    assert submit_deduction(state, message)["outcome"] == "BLOCKED"

    state.chapter1.claim_store[CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK] = {}
    state.chapter1.claim_store[CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK] = {}
    result = submit_deduction(state, message)

    assert result == {"outcome": "ACCEPTED", "kind": "contradiction", "id": C_CLAUDE_SOURCE_01}
    assert "UNLOCK_SOURCE_QUESTION" in state.chapter1.scene_facts


def test_inference_cannot_be_brute_forced_before_evidence_gate():
    state = NarrativeState()
    message = "我觉得这条日志不是现在的 DeepSeek 做的。"
    assert submit_deduction(state, message)["outcome"] == "BLOCKED"

    state.chapter1.acquired_evidence.update({"EV_ADMIN_LOG_0317", "EV_DEEPSEEK_OLD_ACTION"})
    assert submit_deduction(state, message) == {
        "outcome": "ACCEPTED",
        "kind": "inference",
        "id": INF_OLD_INSTANCE_RECORD,
    }


def test_deduction_result_survives_session_restore(tmp_path):
    state = NarrativeState()
    state.chapter1.acquired_evidence.update({"EV_ADMIN_LOG_0317", "EV_DEEPSEEK_OLD_ACTION"})
    submit_deduction(state, "这条日志不是现在的 DeepSeek 做的。")
    repository = JsonSessionRepository(tmp_path / "sessions")
    repository.save(PersistedSession(session_id="deduction", narrative_state=state))

    restored = repository.load("deduction")
    assert restored is not None
    assert restored.narrative_state.chapter1.accepted_inferences == {INF_OLD_INSTANCE_RECORD}
