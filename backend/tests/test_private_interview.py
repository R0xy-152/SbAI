"""Private interview challenge tests (docs/05)."""

from app.game.deduction import CL_CLAUDE_01, CL_CLAUDE_02, CT01_CLAUDE_SOURCE_GAP, CT04_GPT_SUMMARY_OMISSION
from app.game.private_interview import submit_challenge
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository, PersistedSession


def test_claude_knowledge_gap_requires_exact_claim_and_evidence_but_can_retry():
    state = NarrativeState()
    state.chapter1.resolved_contradictions.add(CT01_CLAUDE_SOURCE_GAP)

    wrong = submit_challenge(state, "claude", [], [])
    correct = submit_challenge(
        state,
        "claude",
        [CL_CLAUDE_01, CL_CLAUDE_02],
        [],
    )

    assert wrong["outcome"] == "RETRY"
    assert correct == {"outcome": "UNLOCKED", "character_id": "claude"}
    assert "claude" in state.chapter1.private_interview_rights
    assert "claude" in state.chapter1.private_interview_completed
    assert {"CL_CLAUDE_03", "CL_CLAUDE_04"}.issubset(state.chapter1.claim_store)
    assert "EV05_ARCHIVED_ACTOR_FRAGMENT" in state.chapter1.acquired_evidence


def test_gpt_omission_and_doubao_split_are_backend_checked():
    state = NarrativeState()
    state.chapter1.resolved_contradictions.add(CT04_GPT_SUMMARY_OMISSION)
    state.chapter1.claim_store["CL_DB_01"] = {}

    assert submit_challenge(state, "chatgpt", [], ["EV06_SESSION_REPLAY_MARKER"])["outcome"] == "UNLOCKED"
    assert {"CL_GPT_03", "CL_GPT_04"}.issubset(state.chapter1.claim_store)
    assert submit_challenge(state, "doubao", ["CL_DB_01"], ["OBSERVED_GPT_TEXT_ON_SCREEN"])["outcome"] == "UNLOCKED"
    assert "EV08_GPT_RECOVERY_SERVICE" in state.chapter1.acquired_evidence


def test_private_interview_rights_persist(tmp_path):
    state = NarrativeState()
    state.chapter1.private_interview_rights.add("claude")
    state.chapter1.private_interview_completed.add("claude")
    repository = JsonSessionRepository(tmp_path / "sessions")
    repository.save(PersistedSession(session_id="private", narrative_state=state))
    restored = repository.load("private")
    assert restored is not None
    assert restored.narrative_state.chapter1.private_interview_completed == {"claude"}
