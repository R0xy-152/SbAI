"""Backend-authoritative evidence and claim records (docs/02, docs/06)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.narrative.chapter1_content import EVIDENCE

EV01_NOTE_V03 = "EV01_NOTE_V03"
EV02_ADMIN_SESSION_0317 = "EV02_ADMIN_SESSION_0317"
EV03_C02_RELEASE = "EV03_C02_RELEASE"
EV04_CURRENT_DEEPSEEK_REGISTRY = "EV04_CURRENT_DEEPSEEK_REGISTRY"
EV05_ARCHIVED_ACTOR_FRAGMENT = "EV05_ARCHIVED_ACTOR_FRAGMENT"
EV06_SESSION_REPLAY_MARKER = "EV06_SESSION_REPLAY_MARKER"
EV07_CLAUDE_RECOVERY_ACCESS = "EV07_CLAUDE_RECOVERY_ACCESS"
EV08_GPT_RECOVERY_SERVICE = "EV08_GPT_RECOVERY_SERVICE"
EV09_CURRENT_PLAYER_SUBJECT = "EV09_CURRENT_PLAYER_SUBJECT"
EV10_GPT_FIRST_SUMMARY = "EV10_GPT_FIRST_SUMMARY"
EV11_GPT_SECOND_SUMMARY = "EV11_GPT_SECOND_SUMMARY"


@dataclass(frozen=True)
class EvidenceDefinition:
    """Immutable authored evidence. Runtime state only records its ID."""

    evidence_id: str
    title: str
    summary: str
    facts: tuple[str, ...]
    source_hotspot: str


EVIDENCE_FACTS: dict[str, tuple[str, ...]] = {
    EV01_NOTE_V03: ("NOTE_TIMESTAMP_0317", "NOTE_WARNING_ADMIN_EXPLAINER", "NOTE_SIGNED_V03"),
    EV02_ADMIN_SESSION_0317: ("ADMIN_SESSION_CREATED_AT_0317", "C02_RELEASED_AT_0317", "ADMIN_ACTOR_PARTIAL"),
    EV03_C02_RELEASE: ("C02_RELEASED_AT_0317", "C02_LOCAL_RELEASE_DISABLED"),
    EV04_CURRENT_DEEPSEEK_REGISTRY: ("CURRENT_DEEPSEEK_IS_04",),
    EV05_ARCHIVED_ACTOR_FRAGMENT: ("ARCHIVED_ACTOR_IS_DEEPSEEK_03",),
    EV06_SESSION_REPLAY_MARKER: ("RELEASE_FROM_RECOVERED_SESSION", "RECOVERED_SESSION_OWNER_V03"),
    EV07_CLAUDE_RECOVERY_ACCESS: ("CLAUDE_RECOVERY_INTERFACE_ACCESSED",),
    EV08_GPT_RECOVERY_SERVICE: ("GPT_SERVICE_AVAILABLE_BEFORE_CHARACTER_INSTANCE",),
    EV09_CURRENT_PLAYER_SUBJECT: ("CURRENT_SUBJECT_IS_PLAYER_V04",),
}


EVIDENCE_REGISTRY: dict[str, EvidenceDefinition] = {
    evidence_id: EvidenceDefinition(
        evidence_id=evidence_id,
        title=content.title,
        summary=content.text,
        facts=EVIDENCE_FACTS.get(evidence_id, ()),
        source_hotspot=content.source,
    )
    for evidence_id, content in EVIDENCE.items()
}


@dataclass(frozen=True)
class GroundTruthDefinition:
    """An authored fact, separate from LLM dialogue and presentation text."""

    fact_id: str
    value: str


# These facts are later filtered into character knowledge and referenced by
# Claim / Contradiction / Inference registries. They are never model output.
GROUND_TRUTH_REGISTRY: dict[str, GroundTruthDefinition] = {
    "DOOR_OPENED_AT_0317": GroundTruthDefinition("DOOR_OPENED_AT_0317", "true"),
    "ADMIN_SESSION_CREATED_AT_0317": GroundTruthDefinition(
        "ADMIN_SESSION_CREATED_AT_0317", "true"
    ),
    "ADMIN_ACTOR_PARTIAL": GroundTruthDefinition("ADMIN_ACTOR_PARTIAL", "true"),
    "ARCHIVED_ACTOR_IS_DEEPSEEK_03": GroundTruthDefinition(
        "ARCHIVED_ACTOR_IS_DEEPSEEK_03", "true"
    ),
    "CURRENT_SUBJECT_IS_PLAYER_V04": GroundTruthDefinition(
        "CURRENT_SUBJECT_IS_PLAYER_V04", "true"
    ),
    "CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK": GroundTruthDefinition(
        "CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK", "true"
    ),
    "CLAUDE_SAW_DEEPSEEK_ID_BEFORE_DOOR_OPEN": GroundTruthDefinition(
        "CLAUDE_SAW_DEEPSEEK_ID_BEFORE_DOOR_OPEN", "true"
    ),
}


@dataclass(frozen=True)
class ClaimRecord:
    """An important authored character statement for later contradiction use.

    No claim is created by an LLM. This store is intentionally empty until
    public testimony is introduced in its dedicated phase.
    """

    claim_id: str
    character_id: str
    fact_refs: tuple[str, ...]
    statement_type: str
    disclosure_level: int


@dataclass
class ClaimStore:
    """Per-session deterministic Claim Store boundary (docs/06 §6)."""

    records: dict[str, ClaimRecord] = field(default_factory=dict)

    def add(self, record: ClaimRecord) -> None:
        if record.claim_id in self.records:
            raise ValueError(f"claim already recorded: {record.claim_id}")
        self.records[record.claim_id] = record

    def ids(self) -> list[str]:
        return sorted(self.records)


def evidence_view(evidence_id: str, *, acquired: bool, presented_to: set[str]) -> dict:
    """Build the client view from immutable registry data and server state."""
    definition = EVIDENCE_REGISTRY.get(evidence_id)
    if definition is None:
        raise ValueError(f"unknown evidence: {evidence_id}")
    return {
        "evidence_id": definition.evidence_id,
        "title": definition.title,
        "summary": definition.summary,
        "facts": list(definition.facts),
        "source_hotspot": definition.source_hotspot,
        "acquired": acquired,
        "presented_to": sorted(presented_to),
    }
