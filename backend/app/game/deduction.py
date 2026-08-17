"""Deterministic Chapter One contradiction and inference rules (docs/10)."""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.chapter1_content import INFERENCE_GATES
from app.narrative.state import NarrativeState

CL_CLAUDE_01 = "CL_CLAUDE_01"
CL_CLAUDE_02 = "CL_CLAUDE_02"
CT01_CLAUDE_SOURCE_GAP = "CT01_CLAUDE_SOURCE_GAP"
CT04_GPT_SUMMARY_OMISSION = "CT04_GPT_SUMMARY_OMISSION"
INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR = "INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR"
INF02_0317_FROM_OLD_SESSION = "INF02_0317_FROM_OLD_SESSION"
INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE = "INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE"
INF04_GPT_NOT_NEUTRAL = "INF04_GPT_NOT_NEUTRAL"


@dataclass(frozen=True)
class ClaimDefinition:
    claim_id: str
    character_id: str
    fact_refs: tuple[str, ...]


CLAIM_REGISTRY = {
    CL_CLAUDE_01: ClaimDefinition(CL_CLAUDE_01, "claude", ("CLAUDE_ATTRIBUTES_C02_RELEASE_TO_DEEPSEEK",)),
    CL_CLAUDE_02: ClaimDefinition(CL_CLAUDE_02, "claude", ("CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK",)),
}

CONTRADICTION_REGISTRY = {
    CT01_CLAUDE_SOURCE_GAP: (CL_CLAUDE_01, CL_CLAUDE_02),
}


def map_player_deduction(message: str) -> tuple[str, str] | None:
    """Map bounded equivalent expressions; the backend alone judges correctness."""
    normalized = message.lower().replace(" ", "")
    if "没看到" in normalized and ("为什么说" in normalized or "为什么是她" in normalized):
        return ("contradiction", CT01_CLAUDE_SOURCE_GAP)
    if ("#03" in normalized and "#04" in normalized) or "不是日志里的" in normalized:
        return ("inference", INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR)
    if "recoveredsession" in normalized or "旧session" in normalized or "旧会话" in normalized:
        return ("inference", INF02_0317_FROM_OLD_SESSION)
    if ("v03" in normalized and "v04" in normalized) or "上一个我" in normalized:
        return ("inference", INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE)
    if "gpt" in normalized and ("不" in normalized and "中立" in normalized or "选择性" in normalized):
        return ("inference", INF04_GPT_NOT_NEUTRAL)
    return None


def submit_deduction(state: NarrativeState, message: str) -> dict:
    mapped = map_player_deduction(message)
    if mapped is None:
        return {"outcome": "NO_MATCH"}
    kind, identifier = mapped
    chapter = state.chapter1
    if kind == "contradiction":
        required = CONTRADICTION_REGISTRY[identifier]
        if not all(claim_id in chapter.claim_store for claim_id in required):
            return {"outcome": "BLOCKED", "kind": kind, "id": identifier}
        chapter.resolved_contradictions.add(identifier)
        chapter.scene_facts.add("UNLOCK_CLAUDE_PRIVATE_INTERVIEW")
        return {"outcome": "ACCEPTED", "kind": kind, "id": identifier}

    if identifier == INF04_GPT_NOT_NEUTRAL:
        ready = (
            CT04_GPT_SUMMARY_OMISSION in chapter.resolved_contradictions
            and "chatgpt" in chapter.private_interview_completed
        )
    else:
        ready = INFERENCE_GATES[identifier].issubset(chapter.acquired_evidence)
    if not ready:
        return {"outcome": "BLOCKED", "kind": kind, "id": identifier}
    chapter.accepted_inferences.add(identifier)
    return {"outcome": "ACCEPTED", "kind": kind, "id": identifier}
