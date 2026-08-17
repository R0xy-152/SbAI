"""Private interview challenge tests (docs/05)."""

from app.game.deduction import CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK
from app.game.private_interview import submit_challenge
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository, PersistedSession


def test_claude_knowledge_gap_requires_exact_claim_and_evidence_but_can_retry():
    state = NarrativeState()
    state.chapter1.claim_store[CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK] = {}
    state.chapter1.acquired_evidence.add("EV_ADMIN_LOG_0317")

    wrong = submit_challenge(state, "claude", [], ["EV_ADMIN_LOG_0317"])
    correct = submit_challenge(
        state,
        "claude",
        [CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK],
        ["EV_ADMIN_LOG_0317"],
    )

    assert wrong["outcome"] == "RETRY"
    assert correct == {"outcome": "UNLOCKED", "character_id": "claude"}
    assert "claude" in state.chapter1.private_interview_rights
    assert "claude" in state.chapter1.private_interview_completed


def test_gpt_omission_and_doubao_split_are_backend_checked():
    state = NarrativeState()
    state.chapter1.acquired_evidence.update({"EV_NOTE_V03", "EV_ADMIN_LOG_0317"})
    state.chapter1.evidence_selections.append(
        {"character_id": "chatgpt", "evidence_ids": ["EV_ADMIN_LOG_0317"]}
    )
    state.chapter1.doubao_statements.append(
        {"observed_fact_refs": ["ADMIN_ACTOR_CORRUPTED"], "interpretation": "有人动了手脚。"}
    )

    assert submit_challenge(state, "chatgpt", [], ["EV_NOTE_V03"])["outcome"] == "UNLOCKED"
    assert submit_challenge(
        state, "doubao", ["ADMIN_ACTOR_CORRUPTED"], [], statement_index=0
    )["outcome"] == "UNLOCKED"


def test_private_interview_rights_persist(tmp_path):
    state = NarrativeState()
    state.chapter1.private_interview_rights.add("claude")
    state.chapter1.private_interview_completed.add("claude")
    repository = JsonSessionRepository(tmp_path / "sessions")
    repository.save(PersistedSession(session_id="private", narrative_state=state))
    restored = repository.load("private")
    assert restored is not None
    assert restored.narrative_state.chapter1.private_interview_completed == {"claude"}
