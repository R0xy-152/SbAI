"""Relationship stage + player model tests (docs/05 §31, §45).

Two "thinking AI" levers: the committed relationship stage (model-proposed,
validated, fed back next turn) and the player-model notes (derived only from a
character's own player_* memories, never another character's private
knowledge). Both make a character's attitude toward the Player visible and
continuous across turns.
"""

from __future__ import annotations

import json

from app.characters.base import (
    CharacterRequest,
    CharacterResponse,
    CharacterRuntime,
    CharacterState,
    MemoryProposal,
    parse_character_response,
)
from app.characters.deepseek import DeepSeekRuntime
from app.game.memory import MemoryStore
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository, PersistedSession
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider


def _structured_json(dialogue: str = "好的。", **extra) -> str:
    data = {
        "character_id": "deepseek",
        "dialogue": dialogue,
        "emotion": "neutral",
        "animation_proposal": "none",
        "memory_proposals": [],
        "action_proposals": [],
        "fact_refs": [],
    }
    data.update(extra)
    return json.dumps(data, ensure_ascii=False)


# ---- relationship: parse (tolerant) ----


def test_relationship_parsed():
    response = parse_character_response(
        _structured_json(relationship="trusting"), "deepseek"
    )
    assert response.next_relationship_stage == "trusting"


def test_relationship_invalid_is_none():
    response = parse_character_response(
        _structured_json(relationship="best_friends_forever"), "deepseek"
    )
    assert response.next_relationship_stage is None


def test_relationship_absent_is_none():
    response = parse_character_response(_structured_json(), "deepseek")
    assert response.next_relationship_stage is None


# ---- relationship: prompt injection ----


def test_relationship_injected_into_prompt():
    runtime = DeepSeekRuntime(MockProvider())
    user = runtime._build_user_message(
        CharacterRequest(
            character_id="deepseek",
            player_message="你好",
            relationship_stage="trusting",
        )
    )
    assert "关系阶段" in user
    assert "trusting" in user


# ---- relationship: commit + continuity ----


class _RelationshipProvider(LLMProvider):
    def __init__(self, relationship: str | None = None) -> None:
        self._relationship = relationship
        self.users: list[str] = []

    def complete(self, **kwargs) -> str:
        self.users.append(kwargs["user"])
        extra = {}
        if self._relationship is not None:
            extra["relationship"] = self._relationship
        return _structured_json(**extra)


def _orchestrator(provider) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(provider)}
    )


def test_relationship_commits_and_reaches_next_turn():
    provider = _RelationshipProvider(relationship="attached")
    orchestrator = _orchestrator(provider)
    first = orchestrator.handle_turn(None, "你好")
    # First turn has no committed relationship yet → no relationship line.
    assert "关系阶段" not in provider.users[0]
    orchestrator.handle_turn(first.session_id, "你好呀")
    assert "关系阶段" in provider.users[1]
    assert "attached" in provider.users[1]


# ---- relationship: persistence ----


def test_relationship_persists_round_trip(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    repo.save(
        PersistedSession(
            session_id="s1",
            character_states={"deepseek": CharacterState(relationship_stage="jealous")},
        )
    )
    loaded = repo.load("s1")
    assert loaded.character_states["deepseek"].relationship_stage == "jealous"


# ---- player model: retrieval (docs/05 §16-17, §31) ----


def test_player_notes_filter_player_types():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑"))
    store.propose("deepseek", MemoryProposal("scene_note", "墙上有个数字"))
    notes = store.retrieve_player_notes("deepseek")
    assert [n.content for n in notes] == ["Player说自己很怕黑"]


def test_player_notes_are_owner_scoped():
    store = MemoryStore()
    store.propose("deepseek", MemoryProposal("player_fear", "Player说自己很怕黑"))
    assert store.retrieve_player_notes("deepseek")
    assert store.retrieve_player_notes("claude") == []


def test_player_notes_injected_into_prompt():
    runtime = DeepSeekRuntime(MockProvider())
    user = runtime._build_user_message(
        CharacterRequest(
            character_id="deepseek",
            player_message="你好",
            player_notes="- Player说自己很怕黑",
        )
    )
    assert "你对 Player 的了解" in user
    assert "怕黑" in user


# ---- player model: orchestrator wiring + isolation ----


class _MemoryRuntime(CharacterRuntime):
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


def _memory_orchestrator(
    runtimes: dict[str, CharacterRuntime],
) -> tuple[GameOrchestrator, str]:
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    return GameOrchestrator(store, runtimes), session_id


def test_player_notes_reach_next_turn():
    runtime = _MemoryRuntime("deepseek")
    runtime.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator, session_id = _memory_orchestrator({"deepseek": runtime})

    orchestrator.handle_turn(session_id, "我很怕黑。")
    runtime.proposals = []
    orchestrator.handle_turn(session_id, "再聊聊。")
    assert "怕黑" in runtime.requests[1].player_notes


def test_player_notes_do_not_leak_to_claude():
    deepseek = _MemoryRuntime("deepseek")
    claude = _MemoryRuntime("claude")
    orchestrator, session_id = _memory_orchestrator(
        {"deepseek": deepseek, "claude": claude}
    )

    deepseek.proposals = [MemoryProposal("player_fear", "Player说自己很怕黑")]
    orchestrator.handle_turn(session_id, "我很怕黑。", character_id="deepseek")
    deepseek.proposals = []

    orchestrator.handle_turn(session_id, "你了解我吗？", character_id="claude")
    assert claude.requests[0].player_notes == ""

    # DeepSeek still has it in her own scope and it reaches her next turn.
    orchestrator.handle_turn(session_id, "你还记得我怕黑吗？", character_id="deepseek")
    assert "怕黑" in deepseek.requests[1].player_notes
