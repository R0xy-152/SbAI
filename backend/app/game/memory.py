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

from dataclasses import dataclass, replace

from app.characters.base import MemoryProposal
from app.game.scene import Scene

DEFAULT_IMPORTANCE = 5
# docs/05 §66: importance decays each turn since the last reinforcement,
# floored so a memory fades but is never fully lost. Tune DECAY_FACTOR to
# make characters forget faster/slower.
DECAY_FACTOR = 0.9
IMPORTANCE_FLOOR = 1.0

# Characters that may own Episodic Memory in this MVP (docs/05 §16-17). Doubao
# remains scripted and therefore has no generative memory scope.
KNOWN_CHARACTERS = frozenset({"deepseek", "claude", "chatgpt"})


def _bigrams(text: str) -> set[str]:
    """Character bigrams, ignoring whitespace — a tokenizer-free unit that
    works for Chinese text without a word segmenter (docs/05 §40)."""
    chars = [ch for ch in text if not ch.isspace()]
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def relevance_score(query: str, text: str) -> float:
    """Jaccard overlap of character bigrams — a lightweight, deterministic
    relevance signal. No embeddings / vector DB (docs/05 §39, §41: semantic
    retrieval is not required before pgvector). 0.0 when nothing overlaps."""
    q = _bigrams(query)
    t = _bigrams(text)
    if not q or not t:
        return 0.0
    return len(q & t) / len(q | t)


def effective_importance(memory: EpisodicMemory, now: int) -> float:
    """Importance after decay since the last reinforcement (docs/05 §66).

    The base importance decays by DECAY_FACTOR for each turn since the memory
    was last reinforced, floored at IMPORTANCE_FLOOR — so a memory that is
    never recalled fades toward the floor but is never fully lost.
    """
    age = max(0, now - memory.last_reinforced_at)
    return max(IMPORTANCE_FLOOR, memory.importance * (DECAY_FACTOR ** age))


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
    # docs/05 §66: decay / reinforcement bookkeeping — when it was last
    # recalled and how many times. Recalling a memory bumps last_reinforced_at
    # (reinforce), which resets its decay.
    last_reinforced_at: int = 0
    reinforcements: int = 0


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
            last_reinforced_at=self._counter,
        )
        self._memories.setdefault(owner_character_id, []).append(memory)
        return memory

    def retrieve(
        self,
        owner_character_id: str,
        limit: int | None = 5,
        query: str | None = None,
        now: int | None = None,
    ) -> list[EpisodicMemory]:
        """Deterministic retrieval (docs/05 §38) plus optional lightweight
        relevance (docs/05 §40-41) and decay (docs/05 §66): only the owning
        character's memories. With no query and no now, order importance DESC
        then created_at DESC. With a query, surface the most relevant memories
        first. With now, rank by decayed (effective) importance so recalled
        memories stay fresh and never-recalled ones fade."""
        memories = self._memories.get(owner_character_id, [])
        if query:
            scored = [
                (memory, relevance_score(query, memory.content))
                for memory in memories
            ]
            if now is not None:
                scored.sort(
                    key=lambda pair: (
                        -pair[1],
                        -effective_importance(pair[0], now),
                        -pair[0].created_at,
                    )
                )
            else:
                scored.sort(
                    key=lambda pair: (-pair[1], -pair[0].importance, -pair[0].created_at)
                )
            return [memory for memory, _ in scored[:limit]]
        if now is not None:
            ordered = sorted(
                memories, key=lambda m: (-effective_importance(m, now), -m.created_at)
            )
        else:
            ordered = sorted(memories, key=lambda m: (-m.importance, -m.created_at))
        return ordered[:limit]

    def reinforce(
        self, owner_character_id: str, memory_id: str, turn: int
    ) -> EpisodicMemory | None:
        """Recall reinforces a memory (docs/05 §66): bump its last_reinforced_at
        (resetting decay) and increment the reinforcement count. Returns the
        updated memory, or None if it no longer exists."""
        memories = self._memories.get(owner_character_id, [])
        for index, memory in enumerate(memories):
            if memory.memory_id == memory_id:
                reinforced = replace(
                    memory,
                    last_reinforced_at=turn,
                    reinforcements=memory.reinforcements + 1,
                )
                memories[index] = reinforced
                return reinforced
        return None



    def retrieve_player_notes(
        self, owner_character_id: str, limit: int = 5, query: str | None = None
    ) -> list[EpisodicMemory]:
        """The player-model notes this character formed about the Player
        (docs/05 §31): memories whose type starts with "player_" — names,
        preferences, fears, attitudes. These are always relevant to "who am I
        talking to", so they are surfaced separately from the recency-ranked
        general memories (docs/05 §38). Still owner-scoped (docs/05 §16-17).

        With a query, notes are relevance-ranked (docs/05 §38 轻量相关性排序)
        so an older note the player is actively asking about is not dropped by
        the recency cap. This channel has no decay/reinforcement."""
        memories = [
            memory
            for memory in self._memories.get(owner_character_id, [])
            if memory.memory_type.startswith("player_")
        ]
        if query:
            scored = [(memory, relevance_score(query, memory.content)) for memory in memories]
            scored.sort(key=lambda pair: (-pair[1], -pair[0].created_at))
            return [memory for memory, _ in scored[:limit]]
        ordered = sorted(memories, key=lambda m: -m.created_at)
        return ordered[:limit]

    def retrieve_context(
        self,
        owner_character_id: str,
        limit: int = 5,
        player_note_limit: int = 5,
        query: str | None = None,
        now: int | None = None,
    ) -> tuple[list[EpisodicMemory], list[EpisodicMemory]]:
        """Select a bounded general-memory window and a separate bounded
        player-note window (docs/05 §31, §37-38).

        The two groups are disjoint, so no memory is injected twice. Player
        notes are retrieved independently of the general importance/recency
        ranking, so an older note about the Player is not dropped just because
        more recent scene memories outrank it (issue #3).

        Partition invariant (docs/05 §38, memory-recall experiment
        2026-09-03): the general window excludes EVERY player_* memory of the
        owner, not only the ones inside the current notes window — a note that
        fell outside the recency-capped window used to be treated as a general
        memory and leak in through query relevance.

        query is forwarded to both windows so the lightweight relevance
        ranking (docs/05 §38) applies to general memories and player notes
        alike; now is forwarded to retrieve() for decayed-importance ranking
        (docs/05 §66).
        """
        player_ids = {
            memory.memory_id
            for memory in self._memories.get(owner_character_id, [])
            if memory.memory_type.startswith("player_")
        }
        player_notes = self.retrieve_player_notes(
            owner_character_id, limit=player_note_limit, query=query
        )
        ranked = self.retrieve(owner_character_id, limit=None, query=query, now=now)
        general = [
            memory for memory in ranked if memory.memory_id not in player_ids
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
