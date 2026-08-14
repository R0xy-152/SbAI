"""Character-specific Important Memory (docs/05 §13-18, §33-38, §57-59).

Episodic Memory is owned by a character: `owner_character_id` scopes who may
read it (docs/05 §16-17 — a DeepSeek memory is not automatically available to
Claude). Character output only produces Memory Proposals (docs/04 §44); the
Write Gate decides what actually gets saved (docs/05 §33-36, simple content
dedup for the MVP). Retrieval is deterministic (docs/05 §38): owner filter,
then importance DESC / created_at DESC, LIMIT N — semantic retrieval is not
required before pgvector.

MVP simplification: all memories carry the same importance (docs/05 §56-57
only needs basic character-specific memory; importance ranking can come with
the full write policy later).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.characters.base import MemoryProposal

DEFAULT_IMPORTANCE = 5


@dataclass(frozen=True)
class EpisodicMemory:
    """One long-term memory a character is entitled to recall (docs/05 §15)."""

    memory_id: str
    owner_character_id: str
    source: str
    content: str
    memory_type: str
    importance: int
    created_at: int


class MemoryStore:
    """Per-session, per-character important memories (docs/05 §17, §57)."""

    def __init__(self) -> None:
        self._memories: dict[str, list[EpisodicMemory]] = {}
        self._counter = 0

    def propose(
        self,
        owner_character_id: str,
        proposal: MemoryProposal,
        source: str = "player_statement",
    ) -> EpisodicMemory | None:
        """Write Gate (docs/05 §34-36): a Proposal is not a Memory until it
        passes here. Returns the saved memory, or None if ignored (duplicate)."""
        content = proposal.content.strip()
        if not content:
            return None
        existing = self._memories.get(owner_character_id, [])
        if any(memory.content == content for memory in existing):
            return None  # simple dedup (docs/05 §36)
        self._counter += 1
        memory = EpisodicMemory(
            memory_id=f"mem-{self._counter}",
            owner_character_id=owner_character_id,
            source=source,
            content=content,
            memory_type=proposal.type,
            importance=DEFAULT_IMPORTANCE,
            created_at=self._counter,
        )
        self._memories.setdefault(owner_character_id, []).append(memory)
        return memory

    def retrieve(
        self, owner_character_id: str, limit: int = 5
    ) -> list[EpisodicMemory]:
        """Deterministic retrieval (docs/05 §38): only the owning character's
        memories, ordered importance DESC then created_at DESC, LIMIT N."""
        memories = self._memories.get(owner_character_id, [])
        ordered = sorted(memories, key=lambda m: (-m.importance, -m.created_at))
        return ordered[:limit]

    def snapshot(self) -> dict[str, list[EpisodicMemory]]:
        """The full store content, for persistence (TV-14)."""
        return {owner: list(memories) for owner, memories in self._memories.items()}

    @classmethod
    def from_snapshot(
        cls, memories: dict[str, list[EpisodicMemory]]
    ) -> MemoryStore:
        """Rebuild a store from a persisted snapshot (TV-14 Session Restore).

        The id counter is rebuilt from the latest created_at so restored
        memories keep monotonic ids and ordering.
        """
        store = cls()
        store._memories = {owner: list(mems) for owner, mems in memories.items()}
        store._counter = max(
            (memory.created_at for mems in store._memories.values() for memory in mems),
            default=0,
        )
        return store


def format_memories(memories: list[EpisodicMemory]) -> str:
    """Render the selected memories as the character's memory_context
    (docs/04 §12, docs/05 §37): the historical info it may use this turn."""
    return "\n".join(f"- {memory.content}" for memory in memories)
