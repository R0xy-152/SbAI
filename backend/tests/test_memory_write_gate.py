"""Memory Write Gate tests (docs/05 §33-36, §23-25, §57-67).

A Memory Proposal is not a Memory until the Write Gate accepts it. These tests
pin the gate as a permission boundary, not a prompt preference: DeepSeek cannot
store the scene's visual ground truth she was never given, a Player statement
is recorded as a report rather than Ground Truth, rejected knowledge cannot
re-enter her context via recall, scopes stay isolated, and duplicates stay
deduped.
"""

from __future__ import annotations

import logging

import pytest

from app.characters.base import (
    CharacterRequest,
    CharacterResponse,
    CharacterRuntime,
    MemoryProposal,
)
from app.game.memory import (
    MemoryRejected,
    format_memories,
    validate_memory_proposal,
)
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore

BINDING_ROOM = Scene(scene_id="binding_room")  # wall_code "0317"


class _MemoryRuntime(CharacterRuntime):
    """Answers fixed valid output and proposes the memories we attach per turn."""

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


# ---- Write Gate, unit level (docs/05 §34-35) -------------------------------


def test_legal_memory_proposal_passes():
    # A Player's self-disclosure is exactly what the gate should allow.
    validate_memory_proposal(
        MemoryProposal("player_fear", "Player说自己很怕黑"),
        character_id="deepseek",
        scene=BINDING_ROOM,
    )


def test_deepseek_visual_ground_truth_rejected():
    # The model asserts the wall code as a bare fact it was never given.
    with pytest.raises(MemoryRejected):
        validate_memory_proposal(
            MemoryProposal("visual", "墙上的真实密码是0317"),
            character_id="deepseek",
            scene=BINDING_ROOM,
        )


def test_claude_may_store_visual_fact():
    # Claude is not blind (docs/04 §35-39): the same fact is legal for her.
    validate_memory_proposal(
        MemoryProposal("visual", "墙上的密码是0317"),
        character_id="claude",
        scene=BINDING_ROOM,
    )


def test_unknown_owner_rejected():
    # A memory must be owned by a known character (docs/05 §16).
    with pytest.raises(MemoryRejected):
        validate_memory_proposal(
            MemoryProposal("player_fear", "Player说自己很怕黑"),
            character_id="chatgpt",
            scene=BINDING_ROOM,
        )


# ---- Orchestrator: the gate sits on the save path (docs/05 §34) ------------


def test_rejected_visual_memory_not_saved_or_recalled():
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("visual", "墙上的真实密码是0317")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "密码是什么？")
    store = orchestrator._memory_store(session_id)
    assert store.retrieve("deepseek") == []

    # Rebuilding the DeepSeek context after rejection never yields the code.
    runtime.proposals = []
    orchestrator.handle_turn(session_id, "再想想。")
    assert "0317" not in runtime.requests[-1].memory_context
    assert format_memories(store.retrieve("deepseek")) == ""


def test_legal_memory_saved_and_recalled():
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "我很怕黑。")
    assert len(orchestrator._memory_store(session_id).retrieve("deepseek")) == 1

    runtime.proposals = []
    orchestrator.handle_turn(session_id, "随便聊聊。")
    assert "怕黑" in runtime.requests[-1].memory_context


def test_player_statement_does_not_become_ground_truth():
    # A wrong-but-reported wall code (docs/05 §25) is storable as a Player
    # statement, but Memory must never feed Narrative State (docs/05 §3-4).
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_statement", "Player告诉我墙上写着9999")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "墙上写着9999。")
    memories = orchestrator._memory_store(session_id).retrieve("deepseek")
    assert [m.content for m in memories] == ["Player告诉我墙上写着9999"]
    assert memories[0].source == "player_statement"
    # No Narrative State was created — the memory never became Ground Truth.
    assert session_id not in orchestrator._narrative_states


def test_memory_scope_isolated_between_characters():
    # A DeepSeek memory is never retrievable as Claude's (docs/05 §17, §51).
    deepseek = _MemoryRuntime("deepseek")
    claude = _MemoryRuntime("claude")
    orchestrator, session_id = _orchestrator({"deepseek": deepseek, "claude": claude})

    deepseek.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator.handle_turn(session_id, "我很怕黑。", character_id="deepseek")

    store = orchestrator._memory_store(session_id)
    assert len(store.retrieve("deepseek")) == 1
    assert store.retrieve("claude") == []


def test_duplicate_memory_deduped_through_gate():
    # The same proposal on two turns yields one memory (docs/05 §36).
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "我很怕黑。")
    orchestrator.handle_turn(session_id, "我还是很怕黑。")
    assert len(orchestrator._memory_store(session_id).retrieve("deepseek")) == 1


def test_rejection_is_logged_for_debug(caplog):
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("visual", "墙上的真实密码是0317")]
    orchestrator, session_id = _orchestrator({"deepseek": runtime})

    with caplog.at_level(logging.WARNING):
        orchestrator.handle_turn(session_id, "密码是什么？")
    assert "memory proposal rejected" in caplog.text
    assert "visual scene ground truth" in caplog.text
