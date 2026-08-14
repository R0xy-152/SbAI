"""TV-14 Session Restore tests (docs/06 §20, docs/02 §21-23).

After a refresh (a fresh orchestrator over the same repository — all
in-memory state gone), a known session_id must bring back: the message
history, the current Scene, the current Character, the Narrative flags, the
completed events (which must not re-fire), and each character's Important
Memory scope — then the game continues normally.

The repository is the TV-14 validation fixture: a durable JSON file store
behind the SessionRepository interface (docs/02 §22); PostgreSQL is the
target backend. Fixture ≠ Production (docs/06 §10).
"""

from __future__ import annotations

import json

import pytest

from app.characters.base import (
    CharacterRequest,
    CharacterResponse,
    CharacterRuntime,
    MemoryProposal,
)
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative import signals
from app.narrative.interpreter import Interpretation
from app.narrative.poc import build_poc_events
from app.persistence.repository import (
    JsonSessionRepository,
    PersistedSession,
)
from app.providers.base import ProviderError


class _Runtime(CharacterRuntime):
    """Fixed replies; records every request; optionally proposes memories."""

    def __init__(self, character_id: str, proposals: list[MemoryProposal] | None = None):
        self.character_id = character_id
        self.requests: list[CharacterRequest] = []
        self.proposals = proposals or []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(
            character_id=self.character_id,
            dialogue="……",
            emotion="neutral",
            memory_proposals=list(self.proposals),
        )


class _FailingRuntime(CharacterRuntime):
    character_id = "deepseek"

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        raise ProviderError("boom")


class _FlakyRuntime(CharacterRuntime):
    """Succeeds until `fail_on_turn`, then raises (docs/04 §55 recoverable)."""

    def __init__(self, character_id: str, fail_on_turn: int = 2) -> None:
        self.character_id = character_id
        self.fail_on_turn = fail_on_turn
        self.count = 0

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.count += 1
        if self.count == self.fail_on_turn:
            raise ProviderError("boom")
        return CharacterResponse(character_id=self.character_id, dialogue="ok")


class _ScriptedInterpreter:
    """Returns scripted Interpretation verdicts, consumed per call (then noop)."""

    def __init__(self, script: list[str]) -> None:
        self._script = list(script)

    def interpret(self, state, message: str) -> Interpretation:
        signal = self._script.pop(0) if self._script else signals.OUTCOME_NOOP
        return Interpretation(signal=signal)


def _orchestrator(repo, runtimes, script=()):
    return GameOrchestrator(
        SessionStore(),
        runtimes,
        interpreter=_ScriptedInterpreter(list(script)),
        events=build_poc_events(),
        repository=repo,
    )


def _fresh_repo(tmp_path):
    return JsonSessionRepository(tmp_path / "sessions")


# ---- docs/06 §20: the full refresh PASS contract ----

def test_refresh_restores_everything_and_continues(tmp_path):
    repo = _fresh_repo(tmp_path)
    deepseek_a = _Runtime("deepseek", proposals=[MemoryProposal("player_fear", "Player说自己很怕黑")])
    claude_a = _Runtime("claude")
    orchestrator_a = _orchestrator(
        repo, {"deepseek": deepseek_a, "claude": claude_a},
        script=[signals.OUTCOME_NOOP, signals.SIG_ASK_CAPTOR, signals.OUTCOME_NOOP],
    )

    # Pre-refresh state: multi-turn messages, a memory, a fired event (flag +
    # completed_events), the default scene/character.
    session = orchestrator_a.handle_turn(None, "我很怕黑。")       # noop + memory written
    session = orchestrator_a.handle_turn(session.session_id, "是谁把我们抓来的？")  # fires the event
    orchestrator_a.handle_turn(session.session_id, "接下来怎么办？")  # a third round
    session_id = session.session_id

    # The refresh: a brand-new orchestrator shares only the repository.
    deepseek_b = _Runtime("deepseek")
    claude_b = _Runtime("claude")
    orchestrator_b = _orchestrator(
        repo, {"deepseek": deepseek_b, "claude": claude_b},
        script=[signals.OUTCOME_NOOP],
    )

    # Restore happens when the known session_id returns.
    turn = orchestrator_b.handle_turn(session_id, "Claude现在在哪里？")
    assert turn.session_id == session_id  # same session, not a fresh uuid

    # History still exists: the restored session carries all prior messages,
    # so the character hears the old thread again.
    restored_session = orchestrator_b._sessions.get(session_id)
    assert restored_session is not None
    assert len(restored_session.messages) >= 6  # 3 turns × (player + character)
    assert any("我很怕黑" in m["content"] for m in restored_session.messages)

    # Current Scene correct (the single authoritative source, docs/03 §5.1).
    assert orchestrator_b._narrative_states[session_id].current_scene == "binding_room"

    # Narrative Flag correct + Completed Event correct (docs/06 §20).
    state = orchestrator_b._narrative_states[session_id]
    assert "claude_has_appeared" in state.narrative_flags
    assert "EV_POC_CLAUDE_APPEARS" in state.completed_events

    # Event does not repeat: re-triggering SIG_ASK_CAPTOR evaluates to noop
    # and grows nothing (idempotency, docs/03 §30).
    before_flags = set(state.narrative_flags)
    orchestrator_b.handle_turn(session_id, "到底是谁抓的我们？")
    state_after = orchestrator_b._narrative_states[session_id]
    assert state_after.completed_events == {"EV_POC_CLAUDE_APPEARS"}
    assert state_after.narrative_flags == before_flags

    # DeepSeek / Claude Memory Scope stays correct (docs/06 §20): DeepSeek
    # still has her memory.
    memory_context_deepseek = deepseek_b.requests[0].memory_context
    assert "怕黑" in memory_context_deepseek

    # Current Character restored: a message without character_id goes to
    # DeepSeek (the restored last speaker), not to Claude.
    turn = orchestrator_b.handle_turn(session_id, "你还好吗？")
    assert turn.response.character_id == "deepseek"

    # Claude's scope stays isolated: addressed directly, she must not gain
    # DeepSeek's private memory.
    orchestrator_b.handle_turn(session_id, "你知道我害怕什么吗？", character_id="claude")
    assert "怕黑" not in claude_b.requests[0].memory_context

    # Can continue sending new messages: message_count grows from the history.
    assert turn.message_count >= 4


def test_refresh_uses_restored_current_character(tmp_path):
    repo = _fresh_repo(tmp_path)
    deepseek = _Runtime("deepseek")
    claude = _Runtime("claude")
    orchestrator_a = _orchestrator(repo, {"deepseek": deepseek, "claude": claude})

    session = orchestrator_a.handle_turn(None, "你好", character_id="claude")
    session_id = session.session_id

    deepseek_b = _Runtime("deepseek")
    claude_b = _Runtime("claude")
    orchestrator_b = _orchestrator(repo, {"deepseek": deepseek_b, "claude": claude_b})

    # No character_id → the restored current character (claude) is used.
    turn = orchestrator_b.handle_turn(session_id, "继续聊")
    assert turn.response.character_id == "claude"
    assert claude_b.requests
    assert not deepseek_b.requests


# ---- repository semantics ----

def test_unknown_session_id_still_mints_fresh(tmp_path):
    repo = _fresh_repo(tmp_path)
    runtime = _Runtime("deepseek")
    orchestrator = _orchestrator(repo, {"deepseek": runtime})
    session = orchestrator.handle_turn("stale-client-id", "你好")
    assert session.session_id != "stale-client-id"  # never trusts unknown ids


def test_without_repository_nothing_persists(tmp_path):
    runtime = _Runtime("deepseek")
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": runtime})
    orchestrator.handle_turn(None, "你好")
    assert not list(tmp_path.iterdir())


def test_snapshot_file_contains_full_history(tmp_path):
    repo = _fresh_repo(tmp_path)
    runtime = _Runtime("deepseek")
    orchestrator = _orchestrator(repo, {"deepseek": runtime})
    session = orchestrator.handle_turn(None, "第一句")
    orchestrator.handle_turn(session.session_id, "第二句")
    data = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert len(data["messages"]) == 4
    assert data["messages"][0]["content"] == "第一句"
    assert data["narrative"]["current_scene"] == "binding_room"
    assert data["current_character"] == "deepseek"


def test_failed_turn_is_not_persisted(tmp_path):
    # First turn succeeds (snapshot exists), second turn fails → the failed
    # player message must not reach the snapshot (validate-before-commit also
    # applies to persistence).
    repo = _fresh_repo(tmp_path)
    runtime = _FlakyRuntime("deepseek", fail_on_turn=2)
    orchestrator = _orchestrator(repo, {"deepseek": runtime})
    session = orchestrator.handle_turn(None, "成功的一轮")
    before = (tmp_path / "sessions" / f"{session.session_id}.json").read_bytes()
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session.session_id, "这会失败")
    after = (tmp_path / "sessions" / f"{session.session_id}.json").read_bytes()
    assert after == before

    # A brand-new orchestrator restores only the successful turn.
    runtime_b = _Runtime("deepseek")
    orchestrator_b = _orchestrator(repo, {"deepseek": runtime_b})
    turn = orchestrator_b.handle_turn(session.session_id, "恢复后继续")
    restored = orchestrator_b._sessions.get(session.session_id)
    assert all("这会失败" not in m["content"] for m in restored.messages)


def test_corrupt_snapshot_falls_back_to_fresh_session(tmp_path):
    repo = _fresh_repo(tmp_path)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions" / "broken.json").write_text("{not json", encoding="utf-8")
    assert repo.load("broken") is None
    runtime = _Runtime("deepseek")
    orchestrator = _orchestrator(repo, {"deepseek": runtime})
    session = orchestrator.handle_turn("broken", "你好")
    assert session.session_id != "broken"  # recovers like any unknown id


def test_repository_round_trip_serialization(tmp_path):
    from app.game.memory import EpisodicMemory
    from app.narrative.state import NarrativeState

    persisted = PersistedSession(
        session_id="s-1",
        messages=[{"role": "player", "content": "你好"}],
        current_character="claude",
        narrative_state=NarrativeState(
            current_scene="yard",
            story_phase="midgame",
            narrative_flags={"flag_a", "flag_b"},
            revealed_facts={"fact_1"},
            completed_events={"EV_X"},
            active_objective="leave",
        ),
        memories={
            "deepseek": [
                EpisodicMemory("mem-1", "deepseek", "player_statement", "怕黑", "fear", 5, 1)
            ]
        },
    )
    repo = _fresh_repo(tmp_path)
    repo.save(persisted)

    loaded = repo.load("s-1")
    assert loaded is not None
    assert loaded.session_id == "s-1"
    assert loaded.messages == persisted.messages
    assert loaded.current_character == "claude"
    assert loaded.narrative_state == persisted.narrative_state
    assert loaded.narrative_state.current_scene == "yard"
    assert loaded.memories["deepseek"][0] == persisted.memories["deepseek"][0]


def test_restored_memory_store_keeps_ordering_and_ids(tmp_path):
    repo = _fresh_repo(tmp_path)
    runtime = _Runtime("deepseek", proposals=[MemoryProposal("fear", "怕黑")])
    orchestrator_a = _orchestrator(repo, {"deepseek": runtime})
    session = orchestrator_a.handle_turn(None, "我很怕黑。")
    session_id = session.session_id

    runtime_b = _Runtime("deepseek")
    orchestrator_b = _orchestrator(repo, {"deepseek": runtime_b})
    orchestrator_b.handle_turn(session_id, "恢复")  # restores the store

    # New memories continue the id counter instead of colliding.
    store = orchestrator_b._memory_stores[session_id]
    assert [m.memory_id for m in store.retrieve("deepseek")] == ["mem-1"]
    new = store.propose("deepseek", MemoryProposal("likes", "Player喜欢甜食"))
    assert new is not None
    assert new.memory_id == "mem-2"
