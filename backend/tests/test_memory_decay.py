"""Memory decay + reinforcement tests (docs/05 §66).

A memory's importance decays each turn since its last reinforcement, floored so
it fades but is never fully lost. Recall (retrieve + reinforce) resets the
decay. All deterministic; no vector DB.
"""

from __future__ import annotations

import json

from app.characters.base import MemoryProposal
from app.game.memory import (
    IMPORTANCE_FLOOR,
    EpisodicMemory,
    MemoryStore,
    effective_importance,
)
from app.persistence.repository import JsonSessionRepository, PersistedSession


def test_effective_importance_decays_with_age():
    memory = EpisodicMemory(
        memory_id="m", owner_character_id="deepseek", source="s", content="c",
        memory_type="t", importance=5, created_at=0, last_reinforced_at=0,
    )
    assert effective_importance(memory, 0) == 5.0
    assert effective_importance(memory, 5) < 5.0


def test_effective_importance_floors():
    memory = EpisodicMemory(
        memory_id="m", owner_character_id="deepseek", source="s", content="c",
        memory_type="t", importance=5, created_at=0, last_reinforced_at=0,
    )
    assert effective_importance(memory, 1000) == IMPORTANCE_FLOOR


def test_reinforce_resets_decay_and_counts():
    store = MemoryStore()
    memory = store.propose("deepseek", MemoryProposal("a", "m1"))
    store.reinforce("deepseek", memory.memory_id, 10)
    updated = store.retrieve("deepseek")[0]
    assert updated.reinforcements == 1
    assert updated.last_reinforced_at == 10
    assert effective_importance(updated, 10) == 5.0


def test_retrieve_with_now_ranks_fresher_first():
    store = MemoryStore()
    m1 = store.propose("deepseek", MemoryProposal("a", "m1"))  # created_at=1
    store.propose("deepseek", MemoryProposal("b", "m2"))  # created_at=2
    # Reinforce the OLDER memory at a later turn; the newer one stays stale.
    store.reinforce("deepseek", m1.memory_id, 20)
    result = store.retrieve("deepseek", limit=1, now=21)
    assert result[0].content == "m1"


def test_retrieve_without_now_keeps_base_importance_order():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("a", "m1"))
    store.propose("deepseek", MemoryProposal("b", "m2"))
    assert [m.content for m in store.retrieve("deepseek", limit=2)] == ["m2", "m1"]


def test_reinforce_missing_memory_returns_none():
    store = MemoryStore()
    assert store.reinforce("deepseek", "nope", 1) is None


# ---- persistence ----


def test_memory_decay_fields_persist_round_trip(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    memory = EpisodicMemory(
        memory_id="mem-1", owner_character_id="deepseek",
        source="player_statement", content="Player说自己很怕黑",
        memory_type="player_fear", importance=5, created_at=1,
        last_reinforced_at=3, reinforcements=2,
    )
    repo.save(PersistedSession(session_id="s1", memories={"deepseek": [memory]}))
    loaded = repo.load("s1")
    m = loaded.memories["deepseek"][0]
    assert m.last_reinforced_at == 3
    assert m.reinforcements == 2


def test_legacy_memory_snapshot_loads_with_defaults(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    repo.save(PersistedSession(session_id="legacy"))
    path = tmp_path / "legacy.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["memories"] = {
        "deepseek": [
            {
                "memory_id": "mem-1", "owner_character_id": "deepseek",
                "source": "ps", "content": "x", "memory_type": "t",
                "importance": 5, "created_at": 4,
            }
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = repo.load("legacy")
    m = loaded.memories["deepseek"][0]
    assert m.last_reinforced_at == 4  # defaults to created_at
    assert m.reinforcements == 0
