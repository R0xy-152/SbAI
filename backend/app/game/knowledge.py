"""Deterministic knowledge ledger (who-knows-what, via what, since when).

A "belief model" skeleton for the mystery: it records, per character, which
fact / evidence ids they have come to know, via which legal source, and at
which turn. Knowledge is NEVER auto-shared across characters — it enters only
through an explicit legal event (e.g. the player presenting evidence), which is
the propagation rule of docs/05 §51. This is deterministic, queryable state
(complementing, not replacing, per-character Episodic Memory).
"""

from __future__ import annotations

from dataclasses import dataclass

# Legal knowledge sources (docs/05 §28): how a character came to know a fact.
# presented_evidence is wired in this round; narrative reveals and player
# statements can be recorded through the same ledger later.
SOURCE_PRESENTED_EVIDENCE = "presented_evidence"
SOURCE_NARRATIVE_REVEAL = "narrative_reveal"
SOURCE_PLAYER_STATEMENT = "player_statement"


@dataclass(frozen=True)
class KnowledgeEntry:
    character_id: str
    fact_id: str
    source: str
    turn: int


class KnowledgeLedger:
    """Per-session knowledge: character_id -> fact_id -> [entries].

    Multiple entries per fact record the (possibly multiple) legal sources a
    character learned it from. A fact is "known" once any entry exists.
    """

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, list[KnowledgeEntry]]] = {}

    def record(
        self, character_id: str, fact_id: str, source: str, turn: int
    ) -> bool:
        """Record that a character now knows a fact. Returns False if this
        exact (source, turn) entry already exists (idempotent)."""
        per_fact = self._entries.setdefault(character_id, {}).setdefault(fact_id, [])
        if any(e.source == source and e.turn == turn for e in per_fact):
            return False
        per_fact.append(KnowledgeEntry(character_id, fact_id, source, turn))
        return True

    def knows(self, character_id: str, fact_id: str) -> bool:
        """Whether the character has any recorded knowledge of the fact."""
        return fact_id in self._entries.get(character_id, {})

    def known_facts(self, character_id: str) -> frozenset[str]:
        """All fact/evidence ids the character knows."""
        return frozenset(self._entries.get(character_id, {}))

    def entries(self, character_id: str, fact_id: str) -> list[KnowledgeEntry]:
        """The (source, turn) history for one fact, oldest first."""
        return list(self._entries.get(character_id, {}).get(fact_id, []))

    def snapshot(self) -> dict[str, dict[str, list[dict]]]:
        """Serializable form for persistence (docs/02 §21)."""
        return {
            cid: {
                fact_id: [{"source": e.source, "turn": e.turn} for e in entries]
                for fact_id, entries in facts.items()
            }
            for cid, facts in self._entries.items()
        }

    @classmethod
    def from_snapshot(cls, data: dict[str, dict[str, list[dict]]]) -> "KnowledgeLedger":
        ledger = cls()
        for cid, facts in data.items():
            for fact_id, entries in facts.items():
                for e in entries:
                    ledger.record(cid, fact_id, e["source"], e["turn"])
        return ledger


class KnowledgeService:
    """Owns the per-session KnowledgeLedgers (mirrors MemoryService)."""

    def __init__(self) -> None:
        self._ledgers: dict[str, KnowledgeLedger] = {}

    def ledger_for(self, session_id: str) -> KnowledgeLedger:
        ledger = self._ledgers.get(session_id)
        if ledger is None:
            ledger = KnowledgeLedger()
            self._ledgers[session_id] = ledger
        return ledger

    def get(self, session_id: str) -> KnowledgeLedger | None:
        return self._ledgers.get(session_id)

    def restore(self, session_id: str, data: dict) -> None:
        self._ledgers[session_id] = KnowledgeLedger.from_snapshot(data)
