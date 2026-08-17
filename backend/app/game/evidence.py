"""Backend-authoritative evidence and claim records (docs/02, docs/06)."""

from __future__ import annotations

from dataclasses import dataclass, field


EV_NOTE_V03 = "EV_NOTE_V03"
EV_ADMIN_LOG_0317 = "EV_ADMIN_LOG_0317"
EV_DEEPSEEK_OLD_ACTION = "EV_DEEPSEEK_OLD_ACTION"
EV_CURRENT_SUBJECT = "EV_CURRENT_SUBJECT"


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
    EV_ADMIN_LOG_0317: EvidenceDefinition(
        evidence_id=EV_ADMIN_LOG_0317,
        title="03:17 管理员日志",
        summary="03:17 建立过管理员会话，记录中的 Actor 已损坏。",
        facts=("ADMIN_SESSION_CREATED_AT_0317", "ADMIN_ACTOR_CORRUPTED"),
        source_hotspot="CH1_TERMINAL_MAIN",
    ),
    EV_DEEPSEEK_OLD_ACTION: EvidenceDefinition(
        evidence_id=EV_DEEPSEEK_OLD_ACTION,
        title="旧 Instance 行为记录",
        summary="记录显示：旧 Instance 的 DeepSeek 曾释放 Claude 房门。",
        facts=("OLD_DEEPSEEK_RELEASED_CLAUDE_DOOR",),
        source_hotspot="CH1_CLAUDE_AREA",
    ),
    EV_CURRENT_SUBJECT: EvidenceDefinition(
        evidence_id=EV_CURRENT_SUBJECT,
        title="当前对象标识",
        summary="系统身份栏显示：CURRENT SUBJECT = PLAYER_V04。",
        facts=("CURRENT_SUBJECT_IS_PLAYER_V04",),
        source_hotspot="SYSTEM_IDENTITY_PANEL",
    ),
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
    "ADMIN_ACTOR_CORRUPTED": GroundTruthDefinition("ADMIN_ACTOR_CORRUPTED", "true"),
    "OLD_DEEPSEEK_RELEASED_CLAUDE_DOOR": GroundTruthDefinition(
        "OLD_DEEPSEEK_RELEASED_CLAUDE_DOOR", "true"
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
