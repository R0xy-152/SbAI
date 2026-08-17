"""Backend-authoritative evidence and claim records (docs/02, docs/06)."""

from __future__ import annotations

from dataclasses import dataclass, field


EV_NOTE_V03 = "EV_NOTE_V03"


@dataclass(frozen=True)
class EvidenceDefinition:
    """Immutable authored evidence. Runtime state only records its ID."""

    evidence_id: str
    title: str
    summary: str
    facts: tuple[str, ...]
    source_hotspot: str


EVIDENCE_REGISTRY: dict[str, EvidenceDefinition] = {
    EV_NOTE_V03: EvidenceDefinition(
        evidence_id=EV_NOTE_V03,
        title="V03 留下的纸条",
        summary="纸条压痕显示：03:17，不要把管理员权限交给“最会替你解释的人”。署名 V03。",
        facts=(
            "NOTE_TIMESTAMP_0317",
            "NOTE_WARNING_ADMIN_EXPLAINER",
            "NOTE_SIGNED_V03",
        ),
        source_hotspot="CH1_NOTE_01",
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
