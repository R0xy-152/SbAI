"""TV-13 Important Memory tests (docs/06 §19, docs/05 §13-18, §33-38, §57-59).

Information that has left the Recent window must still be reusable through
Character-specific Important Memory. Character output only produces Memory
Proposals; the Write Gate (dedup) decides what is saved, and retrieval is
deterministic and owner-scoped — a DeepSeek memory is never available to
Claude without a legitimate source.
"""

from __future__ import annotations

import pytest

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime, MemoryProposal
from app.game.memory import MemoryStore, format_memories
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.providers.base import ProviderError


class _MemoryRuntime(CharacterRuntime):
    """Answers fixed JSON and records requests; attach proposals per turn."""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        self.requests: list[CharacterRequest] = []
        self.proposals: list[MemoryProposal] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(
            character_id=self.character_id,
            dialogue="……",
            emotion="neutral",
            memory_proposals=list(self.proposals),
        )


def _orchestrator(runtimes: dict[str, CharacterRuntime]) -> tuple[GameOrchestrator, str]:
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    return GameOrchestrator(store, runtimes), session_id


# ---- MemoryStore: Write Gate + deterministic retrieval (docs/05 §33-38) ----


def test_propose_saves_and_retrieve_returns():
    store = MemoryStore()
    memory = store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑"))
    assert memory is not None
    assert memory.owner_character_id == "deepseek"
    assert store.retrieve("deepseek") == [memory]


def test_write_gate_dedups_duplicate_content():
    # docs/05 §36: repeating the same info must not create duplicates.
    store = MemoryStore()
    assert store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑")) is not None
    assert store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑")) is None
    assert len(store.retrieve("deepseek")) == 1


def test_owner_scope_isolates_characters():
    # docs/05 §16-17: a DeepSeek memory is not automatically Claude's.
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑"))
    assert len(store.retrieve("deepseek")) == 1
    assert store.retrieve("claude") == []


def test_retrieve_orders_by_recency_and_limits():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("a", "m1"))
    store.propose("deepseek", MemoryProposal("b", "m2"))
    store.propose("deepseek", MemoryProposal("c", "m3"))
    assert [m.content for m in store.retrieve("deepseek", limit=2)] == ["m3", "m2"]


def test_empty_proposal_is_ignored():
    store = MemoryStore()
    assert store.propose("deepseek", MemoryProposal("player_fear", "   ")) is None
    assert store.retrieve("deepseek") == []


def test_format_memories_renders_one_line_per_memory():
    store = MemoryStore()
    memory = store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑"))
    assert format_memories([memory]) == "- Player说自己很怕黑"


# ---- Orchestrator wiring (docs/05 §37, §57-59) ----


def test_orchestrator_writes_then_recalls_memory():
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "我很怕黑。")
    assert len(orchestrator._memory.store_for(session_id).retrieve("deepseek")) == 1

    runtime.proposals = []
    orchestrator.handle_turn(session_id, "随便聊聊。")
    assert "Player说自己很怕黑" in runtime.requests[1].player_notes


def test_memory_survives_recent_window():
    # docs/06 §19: the info must be reusable after it leaves the Recent
    # window (20 messages = 10 rounds, docs/05 §8).
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "我很怕黑。")
    runtime.proposals = []
    for i in range(11):  # 22 more messages → the original is out of the window
        orchestrator.handle_turn(session_id, f"闲聊{i}。")

    orchestrator.handle_turn(session_id, "如果这里很黑怎么办？")
    last = runtime.requests[-1]
    # The memory content is the character's paraphrase ("说自己很怕黑"), so
    # assert on the meaning, not the literal player quote.
    assert "怕黑" in last.player_notes
    # The original statement is no longer in the recent conversation...
    assert not any("我很怕黑" in message.get("content", "") for message in last.recent_conversation)
    # ...yet the character still legally has it through Important Memory.


def test_memory_does_not_leak_to_claude():
    # docs/06 §19 second requirement: Claude must not gain DeepSeek's private
    # memory without a legitimate source.
    deepseek = _MemoryRuntime("deepseek")
    claude = _MemoryRuntime("claude")
    orchestrator, session_id = _orchestrator({"deepseek": deepseek, "claude": claude})

    deepseek.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator.handle_turn(session_id, "我很怕黑。", character_id="deepseek")
    deepseek.proposals = []

    orchestrator.handle_turn(session_id, "你听说过我的事吗？", character_id="claude")
    assert claude.requests[0].memory_context == ""
    # DeepSeek still has it in her own scope.
    assert len(orchestrator._memory.store_for(session_id).retrieve("deepseek")) == 1


def test_failed_output_does_not_write_memory():
    # docs/05 §34: a Proposal only survives if the character's output succeeds.
    class _FailingRuntime(_MemoryRuntime):
        def respond(self, request: CharacterRequest) -> CharacterResponse:
            self.requests.append(request)
            raise ProviderError("boom")

    runtime = _FailingRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session_id, "我很怕黑。")
    assert orchestrator._memory.store_for(session_id).retrieve("deepseek") == []
