"""Deterministic Claim / Contradiction / Inference rules (docs/04)."""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.state import NarrativeState

CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK = "CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK"
CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK = "CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK"
C_CLAUDE_SOURCE_01 = "C_CLAUDE_SOURCE_01"
INF_OLD_INSTANCE_RECORD = "OLD_INSTANCE_RECORD"


@dataclass(frozen=True)
class ClaimDefinition:
    claim_id: str
    character_id: str
    fact_refs: tuple[str, ...]


CLAIM_REGISTRY = {
    CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK: ClaimDefinition(
        CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK, "claude", ("CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK",)
    ),
    CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK: ClaimDefinition(
        CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK, "claude", ("CLAUDE_SAW_DEEPSEEK_ID_BEFORE_DOOR_OPEN",)
    ),
}

CONTRADICTION_REGISTRY = {
    C_CLAUDE_SOURCE_01: (
        CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK,
        CLAUDE_ATTRIBUTED_DOOR_TO_DEEPSEEK,
    ),
}
INFERENCE_EVIDENCE_GATES = {
    INF_OLD_INSTANCE_RECORD: frozenset({"EV_ADMIN_LOG_0317", "EV_DEEPSEEK_OLD_ACTION"}),
}


def map_player_deduction(message: str) -> tuple[str, str] | None:
    """Small deterministic equivalent-phrase mapper; never judges truth."""
    normalized = message.lower().replace(" ", "")
    if "没看到" in normalized and ("为什么说" in normalized or "为什么是她" in normalized):
        return ("contradiction", C_CLAUDE_SOURCE_01)
    if "不是现在的deepseek" in normalized or "旧instance" in normalized:
        return ("inference", INF_OLD_INSTANCE_RECORD)
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
        if identifier not in chapter.resolved_contradictions:
            chapter.resolved_contradictions.add(identifier)
            chapter.scene_facts.add("UNLOCK_SOURCE_QUESTION")
        return {"outcome": "ACCEPTED", "kind": kind, "id": identifier}
    required_evidence = INFERENCE_EVIDENCE_GATES[identifier]
    if not required_evidence.issubset(chapter.acquired_evidence):
        return {"outcome": "BLOCKED", "kind": kind, "id": identifier}
    chapter.accepted_inferences.add(identifier)
    return {"outcome": "ACCEPTED", "kind": kind, "id": identifier}
