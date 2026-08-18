"""Deterministic Evidence Manipulation Framework (docs/05)."""

from __future__ import annotations

from app.game.deduction import CL_CLAUDE_01, CL_CLAUDE_02, CT01_CLAUDE_SOURCE_GAP
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
        # The player identifies a held evidence item GPT omitted from one of
        # her persisted evidence selections; omission is not fabrication.
        success = (
            len(evidence_ids) == 1
            and evidence_ids[0] in chapter.acquired_evidence
            and any(
                selection["character_id"] == "chatgpt"
                and evidence_ids[0] not in selection["evidence_ids"]
                for selection in chapter.evidence_selections
            )
        )
    elif character_id == "doubao" and statement_index is not None:
        if 0 <= statement_index < len(chapter.doubao_statements):
            statement = chapter.doubao_statements[statement_index]
            success = (
                claim_ids == statement["observed_fact_refs"]
                and bool(statement["interpretation"])
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
    return {"outcome": "UNLOCKED", "character_id": character_id}
