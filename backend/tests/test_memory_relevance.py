"""Lightweight semantic memory retrieval tests (docs/05 §38-41).

Relevance is a tokenizer-free character-bigram Jaccard overlap — no embeddings
or vector DB. Retrieval stays owner-scoped; a query only reorders within the
owning character's memories.
"""

from __future__ import annotations

from app.characters.base import CharacterResponse, CharacterRuntime, MemoryProposal
from app.game.memory import MemoryStore, relevance_score
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore


def test_relevance_score_overlap():
    score = relevance_score("墙上写着什么", "墙上写着一个数字")
    assert score > 0.0


def test_relevance_score_no_overlap():
    assert relevance_score("你好", "Player说自己很怕黑") == 0.0


def test_retrieve_with_query_surfaces_older_relevant_memory():
    store = MemoryStore()
    # older, but relevant to the query
    store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑"))
    # newer, but irrelevant
    store.propose("deepseek", MemoryProposal("scene_note", "窗外有鸟叫"))
    result = store.retrieve("deepseek", limit=1, query="我很怕黑")
    assert result[0].content == "Player说自己很怕黑"


def test_retrieve_without_query_keeps_recency_order():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("a", "m1"))
    store.propose("deepseek", MemoryProposal("b", "m2"))
    assert [m.content for m in store.retrieve("deepseek", limit=2)] == ["m2", "m1"]


def test_retrieve_with_query_falls_back_to_recency_when_no_overlap():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("a", "m1"))
    store.propose("deepseek", MemoryProposal("b", "m2"))
    # "你好" shares no bigrams → relevance is all 0 → recency order.
    assert [m.content for m in store.retrieve("deepseek", limit=2, query="你好")] == [
        "m2",
        "m1",
    ]


def test_retrieve_player_notes_with_query_surfaces_older_relevant_note():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("player_name", "Player叫小明"))
    for index in range(5):
        store.propose("deepseek", MemoryProposal("player_like", f"Player喜欢事物{index}"))

    # No query: the recency cap drops the oldest note.
    assert "Player叫小明" not in [
        m.content for m in store.retrieve_player_notes("deepseek", limit=5)
    ]

    # With query: the relevant older note is ranked back into the window.
    notes = store.retrieve_player_notes("deepseek", limit=5, query="小明是谁")
    assert "Player叫小明" in [m.content for m in notes]


# ---- orchestrator wiring: the player message is passed as the query ----


class _MemoryRuntime(CharacterRuntime):
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        self.requests = []
        self.proposals: list[MemoryProposal] = []

    def respond(self, request) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(
            character_id=self.character_id,
            dialogue="……",
            emotion="neutral",
            memory_proposals=list(self.proposals),
        )


def test_orchestrator_passes_query_and_recalls_memory():
    runtime = _MemoryRuntime("deepseek")
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": runtime})

    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    first = orchestrator.handle_turn(None, "我很怕黑。")
    runtime.proposals = []
    orchestrator.handle_turn(first.session_id, "我怕黑怎么办？")
    # The relevant memory is recalled into the character's context. A
    # player_* memory surfaces through the dedicated player-notes block
    # (issue #3 partitioning), never through the general memory window.
    assert "怕黑" in runtime.requests[1].player_notes
