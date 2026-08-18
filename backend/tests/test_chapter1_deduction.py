"""Claim / contradiction / inference tests (docs/04)."""

from app.game.deduction import (
    CL_CLAUDE_01,
    CL_CLAUDE_02,
    CT01_CLAUDE_SOURCE_GAP,
    INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR,
    INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE,
    submit_deduction,
)
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository, PersistedSession


def test_contradiction_requires_the_exact_recorded_claim_combination():
    state = NarrativeState()
    message = "你说没看到 DeepSeek 本人，那你为什么说是她开的？"
    assert submit_deduction(state, message)["outcome"] == "BLOCKED"

    state.chapter1.claim_store[CL_CLAUDE_01] = {}
    state.chapter1.claim_store[CL_CLAUDE_02] = {}
    result = submit_deduction(state, message)

    assert result == {"outcome": "ACCEPTED", "kind": "contradiction", "id": CT01_CLAUDE_SOURCE_GAP}
    assert "UNLOCK_CLAUDE_PRIVATE_INTERVIEW" in state.chapter1.scene_facts


def test_inference_cannot_be_brute_forced_before_evidence_gate():
    state = NarrativeState()
    message = "DEEPSEEK#03 和 #04 不是同一个 Instance。"
    assert submit_deduction(state, message)["outcome"] == "BLOCKED"

    state.chapter1.acquired_evidence.update({"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"})
    assert submit_deduction(state, message) == {
        "outcome": "ACCEPTED",
        "kind": "inference",
        "id": INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR,
    }
    assert "EV06_SESSION_REPLAY_MARKER" in state.chapter1.acquired_evidence
    assert "EV10_GPT_FIRST_SUMMARY" in state.chapter1.acquired_evidence
    assert "chatgpt" in state.chapter1.available_characters
    assert "chatgpt_has_appeared" in state.narrative_flags
    assert "CURRENT_DEEPSEEK_CLEARED" in state.chapter1.scene_facts


def test_deduction_result_survives_session_restore(tmp_path):
    state = NarrativeState()
    state.chapter1.acquired_evidence.update({"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"})
    submit_deduction(state, "DEEPSEEK#03 和 #04 不是同一个 Instance。")
    repository = JsonSessionRepository(tmp_path / "sessions")
    repository.save(PersistedSession(session_id="deduction", narrative_state=state))

    restored = repository.load("deduction")
    assert restored is not None
    assert restored.narrative_state.chapter1.accepted_inferences == {INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR}


def test_v03_v04_reveal_requires_all_three_authored_evidence_records():
    state = NarrativeState()
    message = "V03 是上一个我；当前 Player 是 V04。"

    assert submit_deduction(state, message)["outcome"] == "BLOCKED"
    state.chapter1.acquired_evidence.update({
        "EV01_NOTE_V03",
        "EV06_SESSION_REPLAY_MARKER",
        "EV09_CURRENT_PLAYER_SUBJECT",
    })

    assert submit_deduction(state, message) == {
        "outcome": "ACCEPTED",
        "kind": "inference",
        "id": INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE,
    }
