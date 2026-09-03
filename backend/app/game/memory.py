"""Character-specific Important Memory (docs/05 §13-18, §33-38, §57-59).

Episodic Memory is owned by a character: `owner_character_id` scopes who may
read it (docs/05 §16-17 — a DeepSeek memory is not automatically available to
Claude). Character output only produces Memory Proposals (docs/04 §44); the
Write Gate decides what actually gets saved (docs/05 §33-36). The gate is a
hard permission boundary, not a prompt preference: it rejects proposals from
unknown owners and any proposal that stores knowledge the character was never
given (DeepSeek's visual blindness, docs/05 §23), so hallucinated or
out-of-band information cannot become long-term Memory or re-enter context
via recall. Retrieval is deterministic (docs/05 §38): owner filter, then
importance DESC / created_at DESC, LIMIT N — semantic retrieval is not
required before pgvector.

MVP simplification: all memories carry the same importance (docs/05 §56-57
only needs basic character-specific memory; importance ranking can come with
the full write policy later).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.characters.base import MemoryProposal
from app.game.scene import Scene

DEFAULT_IMPORTANCE = 5

# Characters that may own Episodic Memory in this MVP (docs/05 §16-17). Doubao
# remains scripted and therefore has no generative memory scope.
KNOWN_CHARACTERS = frozenset({"deepseek", "claude", "chatgpt"})


class MemoryRejected(Exception):
    """A Memory Proposal failed the Write Gate (docs/05 §34-35).

    Raised with a human-readable reason; the caller must not save the proposal
    and should record the reason for debug.
    """


def validate_memory_proposal(
    proposal: MemoryProposal,
    *,
    character_id: str,
    scene: Scene,
) -> None:
    """Memory Write Gate (docs/05 §34-35): decide SAVE / REJECT for a Proposal.

    Deterministic, backend-only checks — the model's own phrasing is never
    trusted as evidence of legitimacy:

    1. the owner must be a known character (correct owner_character_id);
    2. the character must be entitled to the information: DeepSeek cannot store
       the scene's visual ground truth (wall_code) she was never given
       (docs/05 §23, rule 7). This is the same boundary Character Validation
       enforces on her replies, extended to long-term Memory so knowledge that
       fails validation cannot re-enter her context via recall.

    Raises MemoryRejected on the first violation. Empty content and exact
    duplicates are handled by MemoryStore.propose (docs/05 §36), not here.
    """
    if character_id not in KNOWN_CHARACTERS:
        raise MemoryRejected(f"unknown memory owner: {character_id!r}")
    if character_id == "deepseek" and scene.wall_code:
        if scene.wall_code in proposal.content:
            raise MemoryRejected("deepseek cannot store visual scene ground truth")


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

    def retrieve_player_notes(
        self, owner_character_id: str, limit: int = 5
    ) -> list[EpisodicMemory]:
        """The player-model notes this character formed about the Player
        (docs/05 §31): memories whose type starts with "player_" — names,
        preferences, fears, attitudes. These are always relevant to "who am I
        talking to", so they are surfaced separately from the recency-ranked
        general memories (docs/05 §38). Still owner-scoped (docs/05 §16-17)."""
        memories = [
            memory
            for memory in self._memories.get(owner_character_id, [])
            if memory.memory_type.startswith("player_")
        ]
        ordered = sorted(memories, key=lambda m: -m.created_at)
        return ordered[:limit]

    def retrieve_context(
        self,
        owner_character_id: str,
        limit: int = 5,
        player_note_limit: int = 5,
    ) -> tuple[list[EpisodicMemory], list[EpisodicMemory]]:
        """Select a bounded general-memory window and a separate bounded
        player-note window (docs/05 §31, §37-38).

        The two groups are disjoint, so no memory is injected twice. Player
        notes are retrieved independently of the general importance/recency
        ranking, so an older note about the Player is not dropped just because
        more recent scene memories outrank it (issue #3).
        """
        player_notes = self.retrieve_player_notes(
            owner_character_id, limit=player_note_limit
        )
        player_ids = {memory.memory_id for memory in player_notes}
        ordered = sorted(
            self._memories.get(owner_character_id, []),
            key=lambda memory: (-memory.importance, -memory.created_at),
        )
        general = [
            memory for memory in ordered if memory.memory_id not in player_ids
        ][:limit]
        return general, player_notes

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


class MemoryService:
    """Owns the per-session MemoryStores (docs/05 §17, §57).

    The Game Orchestrator no longer holds the per-session MemoryStore map. Each
    session's store is fully isolated, created on first use, and seeded back
    from a persisted snapshot on Session Restore (docs/02 §21).
    """

    def __init__(self) -> None:
        self._stores: dict[str, MemoryStore] = {}

    def store_for(self, session_id: str) -> MemoryStore:
        """The session's store, created on first use."""
        store = self._stores.get(session_id)
        if store is None:
            store = MemoryStore()
            self._stores[session_id] = store
        return store

    def get(self, session_id: str) -> MemoryStore | None:
        """Non-mutating lookup (snapshot building needs it)."""
        return self._stores.get(session_id)

    def restore(
        self, session_id: str, memories: dict[str, list[EpisodicMemory]]
    ) -> None:
        """Seed a persisted store (TV-14 Session Restore)."""
        self._stores[session_id] = MemoryStore.from_snapshot(memories)


def format_memories(memories: list[EpisodicMemory]) -> str:
    """Render the selected memories as the character's memory_context
    (docs/04 §12, docs/05 §37): the historical info it may use this turn."""
    return "\n".join(f"- {memory.content}" for memory in memories)
