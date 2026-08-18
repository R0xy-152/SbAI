"""Deterministic Evidence Manipulation Framework (docs/05)."""

from __future__ import annotations

from app.game.deduction import CL_CLAUDE_01, CL_CLAUDE_02, CL_DB_01, CL_DB_02, CL_DB_03, CT01_CLAUDE_SOURCE_GAP, CT04_GPT_SUMMARY_OMISSION
from app.narrative.chapter1_content import CLAIMS
from app.narrative.state import NarrativeState


def submit_challenge(
    state: NarrativeState,
    character_id: str,
    claim_ids: list[str],
    evidence_ids: list[str],
    statement_index: int | None = None,
) -> dict:
    """Check one short character-specific evidence manipulation challenge."""
    chapter = state.chapter1
    if character_id == "deepseek":
        return {"outcome": "ALREADY_UNLOCKED", "character_id": character_id}
    success = False
    if character_id == "claude":
        success = (
            claim_ids == [CL_CLAUDE_01, CL_CLAUDE_02]
            and CT01_CLAUDE_SOURCE_GAP in chapter.resolved_contradictions
        )
    elif character_id == "chatgpt":
        success = (
            evidence_ids == ["EV06_SESSION_REPLAY_MARKER"]
            and CT04_GPT_SUMMARY_OMISSION in chapter.resolved_contradictions
        )
    elif character_id == "doubao":
        success = (
            claim_ids == [CL_DB_01]
            and evidence_ids == ["OBSERVED_GPT_TEXT_ON_SCREEN"]
            and CL_DB_01 in chapter.claim_store
        )
    else:
        raise ValueError("unknown private interview challenge character")

    if not success:
        return {"outcome": "RETRY", "character_id": character_id}
    chapter.private_interview_rights.add(character_id)
    chapter.private_interview_completed.add(character_id)
    if character_id == "claude":
        for claim_id in ("CL_CLAUDE_03", "CL_CLAUDE_04"):
            chapter.claim_store.setdefault(
                claim_id,
                {
                    "character_id": "claude",
                    "fact_refs": [],
                    "statement_type": "private",
                    "text": CLAIMS[claim_id],
                },
            )
        chapter.acquired_evidence.add("EV05_ARCHIVED_ACTOR_FRAGMENT")
    elif character_id == "doubao":
        for claim_id in (CL_DB_02, CL_DB_03):
            chapter.claim_store.setdefault(
                claim_id,
                {
                    "character_id": "doubao",
                    "fact_refs": [],
                    "statement_type": "private",
                    "text": CLAIMS[claim_id],
                },
            )
        chapter.acquired_evidence.add("EV08_GPT_RECOVERY_SERVICE")
        state.narrative_flags.add("claude_recovery_disclosure_open")
    elif character_id == "chatgpt":
        for claim_id in ("CL_GPT_03", "CL_GPT_04"):
            chapter.claim_store.setdefault(claim_id, {"character_id": "chatgpt", "fact_refs": [], "statement_type": "private", "text": CLAIMS[claim_id]})
    return {"outcome": "UNLOCKED", "character_id": character_id}
