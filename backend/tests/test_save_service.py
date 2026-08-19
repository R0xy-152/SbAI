"""SaveSnapshotService tests (docs/13 Task 6 acceptance + §26.3).

The core contract: save → mutate the current session → load → the NEW Active
Session equals the saved snapshot, for every captured dimension (§17):
Narrative phase / flags / availability, per-character Memory (no cross-role
leak), Messages + visibility, Evidence / Claim / Contradiction / Inference,
Private Interview progress, Scene / Presence / Emotion, and the script cursor.
"""

from __future__ import annotations

from app.characters.base import CharacterMood, CharacterResponse, MemoryProposal
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.game.investigation import CH1_NOTE_01, INSPECT_HOTSPOT, PAPER_RUBBING_COMPLETE
from app.game.deduction import CL_CLAUDE_01, CL_CLAUDE_02, CT01_CLAUDE_SOURCE_GAP
from app.game.private_interview import submit_challenge
from app.persistence.repository import JsonSessionRepository
from app.save.repository import JsonSaveRepository, MANUAL
from app.save.service import SCHEMA_VERSION, SaveSchemaError, SaveSnapshotService


def _proposal(content: str) -> MemoryProposal:
    return MemoryProposal("player_fear", content)


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(
            character_id=self.character_id,
            dialogue=f"{self.character_id} 回应。",
            next_mood=CharacterMood(positive=0.5, excitement=0.2),
        )

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


class _MemoryRuntime(_Runtime):
    """Proposes a DeepSeek memory every turn so memory lands in the store."""

    def respond(self, request):
        return CharacterResponse(
            character_id=self.character_id,
            dialogue=f"{self.character_id} 回应。",
            memory_proposals=[_proposal("玩家说自己有点紧张")],
        )


def _orchestrator(repository=None) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": _MemoryRuntime("deepseek"),
            "claude": _Runtime("claude"),
            "chatgpt": _Runtime("chatgpt"),
            "doubao": _Runtime("doubao"),
        },
        repository=repository,
    )


def _acquire_note(orchestrator) -> str:
    """First physical action: opens the chapter and acquires EV01."""
    inspected = orchestrator.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    orchestrator.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    return inspected.session_id


def _drive_claude_appeared(orchestrator) -> str:
    """A session with Claude on stage (docs/13 Task 6 #2/#5): acquire EV01,
    then discuss 03:17 to trigger the deterministic incident."""
    session_id = _acquire_note(orchestrator)
    orchestrator.handle_turn(session_id, "03:17 是什么意思？")
    return session_id


def _service(tmp_path) -> tuple[SaveSnapshotService, JsonSessionRepository]:
    repo = JsonSaveRepository(tmp_path / "saves")
    return SaveSnapshotService(repo), repo


def _compare_states(a: dict, b: dict) -> None:
    """The two persisted snapshots must be equal on every captured dimension."""
    assert a == b, "loaded snapshot != saved snapshot"


# ── 1. DeepSeek / Claude Memory 不串 ──────────────────────────────────────

def test_memory_scopes_do_not_cross_after_load(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, repo = _service(tmp_path)
    session_id = _orchestrator_helper_run(orchestrator)

    orchestrator.handle_turn(session_id, "你好呀")
    saved = service.save_manual(orchestrator, "p1", session_id, 1)

    # mutate: fresh deepseek memory + a new turn after save
    orchestrator.handle_turn(session_id, "再聊一句")

    loaded = service.load_save(orchestrator, "p1", saved.id)
    assert loaded["session_id"] != session_id  # docs/13 §19.1: NEW Active Session
    new_id = loaded["session_id"]
    memories = orchestrator._memory.store_for(new_id).snapshot()
    assert set(memories.keys()) == {"deepseek"}
    assert all(m.owner_character_id == "deepseek" for m in memories["deepseek"])
    # the mutate-after-save memory must not be in the loaded session
    assert all("再聊一句" not in m.content for m in memories["deepseek"])


# ── 2. Evidence 恢复 ──────────────────────────────────────────────────────

def test_evidence_restores_after_load(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _acquire_note(orchestrator)
    assert "EV01_NOTE_V03" in orchestrator._state.state_for(session_id).chapter1.acquired_evidence

    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    loaded = service.load_save(orchestrator, "p1", saved.id)
    new_id = loaded["session_id"]
    chapter = orchestrator._state.state_for(new_id).chapter1
    assert "EV01_NOTE_V03" in chapter.acquired_evidence
    assert chapter.hotspot_states == orchestrator._state.state_for(session_id).chapter1.hotspot_states


# ── 3. Claim 恢复 ─────────────────────────────────────────────────────────

def test_claim_store_restores_after_load(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _acquire_note(orchestrator)
    state = orchestrator._state.state_for(session_id)
    state.chapter1.claim_store["CL_CLAUDE_01"] = {
        "character_id": "claude", "fact_refs": ["F1"], "statement_type": "public",
    }
    state.chapter1.resolved_contradictions.add(CT01_CLAUDE_SOURCE_GAP)

    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    loaded = service.load_save(orchestrator, "p1", saved.id)
    chapter = orchestrator._state.state_for(loaded["session_id"]).chapter1
    assert chapter.claim_store == state.chapter1.claim_store
    assert chapter.resolved_contradictions == {CT01_CLAUDE_SOURCE_GAP}


# ── 4. Narrative phase 恢复 ───────────────────────────────────────────────

def test_narrative_phase_and_flags_restore_after_load(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _acquire_note(orchestrator)  # first action advances phase → investigation
    state = orchestrator._state.state_for(session_id)
    assert state.chapter1.phase == "investigation"
    state.narrative_flags.add("pre_0317_window")

    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    loaded = service.load_save(orchestrator, "p1", saved.id)
    chapter = orchestrator._state.state_for(loaded["session_id"]).chapter1
    assert chapter.phase == "investigation"
    assert "pre_0317_window" in orchestrator._state.state_for(loaded["session_id"]).narrative_flags


# ── 5. Character availability 恢复 ────────────────────────────────────────

def test_character_availability_restores_after_load(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _drive_claude_appeared(orchestrator)
    assert "claude" in orchestrator._state.state_for(session_id).chapter1.available_characters

    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    loaded = service.load_save(orchestrator, "p1", saved.id)
    chapter = orchestrator._state.state_for(loaded["session_id"]).chapter1
    assert "claude" in chapter.available_characters
    assert "EV_CH1_CLAUDE_APPEARS" in orchestrator._state.state_for(loaded["session_id"]).completed_events


# ── 6. Private Interview progress 恢复 ────────────────────────────────────

def test_private_interview_progress_restores_after_load(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _acquire_note(orchestrator)
    state = orchestrator._state.state_for(session_id)
    state.chapter1.resolved_contradictions.add(CT01_CLAUDE_SOURCE_GAP)
    submit_challenge(state, "claude", [CL_CLAUDE_01, CL_CLAUDE_02], [])
    assert "claude" in state.chapter1.private_interview_completed

    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    loaded = service.load_save(orchestrator, "p1", saved.id)
    chapter = orchestrator._state.state_for(loaded["session_id"]).chapter1
    assert "claude" in chapter.private_interview_rights
    assert "claude" in chapter.private_interview_completed
    assert "EV05_ARCHIVED_ACTOR_FRAGMENT" in chapter.acquired_evidence


# ── 7. Load 创建新 Active Session ─────────────────────────────────────────

def test_load_creates_new_active_session_and_persists(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _drive_claude_appeared(orchestrator)
    saved = service.save_manual(orchestrator, "p1", session_id, 1)

    loaded = service.load_save(orchestrator, "p1", saved.id)
    new_id = loaded["session_id"]
    assert new_id != session_id
    # the new session is itself persisted → survives a fresh process
    fresh = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    history = fresh.get_history(new_id)
    assert history and history[0]["content"]
    # the restored session is usable: a turn works and advances it
    result = fresh.handle_turn(new_id, "继续。")
    assert result.session_id == new_id


# ── 8. schema_version 不支持时明确失败 ───────────────────────────────────

def test_unsupported_schema_version_fails_loudly(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, repo = _service(tmp_path)
    session_id = _orchestrator_helper_run(orchestrator)
    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    # corrupt the saved schema_version into the future
    record = repo.get_by_id(saved.id)
    record.schema_version = SCHEMA_VERSION + 999
    repo.upsert(record)

    try:
        service.load_save(orchestrator, "p1", saved.id)
        assert False, "must raise SaveSchemaError"
    except SaveSchemaError:
        pass


# ── §26.3: slot lifecycle ─────────────────────────────────────────────────

def test_manual_save_overwrite_and_auto_slot(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, repo = _service(tmp_path)
    session_id = _acquire_note(orchestrator)

    m1 = service.save_manual(orchestrator, "p1", session_id, 1, title="第一次")
    auto = service.save_auto(orchestrator, "p1", session_id)
    listing = service.list_saves("p1")
    assert listing["manual"][0] is not None and listing["manual"][0]["id"] == m1.id
    assert listing["auto"] is not None and listing["auto"]["id"] == auto.id

    # overwrite slot 1 — identity (id) is kept, updated_at moves (§16.1)
    orchestrator.handle_turn(session_id, "再聊。")
    m2 = service.save_manual(orchestrator, "p1", session_id, 1, title="第二次")
    assert m2.id == m1.id
    assert m2.title == "第二次"
    assert m2.updated_at >= m1.updated_at
    listing = service.list_saves("p1")
    assert [s for s in listing["manual"] if s is not None] == [m2.info()]

    # delete slot 1
    assert service.delete_manual("p1", 1) is True
    assert service.list_saves("p1")["manual"][0] is None


def test_list_is_player_scoped(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _acquire_note(orchestrator)
    service.save_manual(orchestrator, "p1", session_id, 1)
    service.save_manual(orchestrator, "p2", session_id, 2)
    listing = service.list_saves("p1")
    assert listing["manual"][0] is not None and listing["manual"][1] is None
    assert listing["manual"][2] is None


def test_load_unknown_save_id_fails(tmp_path):
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    try:
        service.load_save(orchestrator, "p1", "does-not-exist")
        assert False, "must raise KeyError"
    except KeyError:
        pass


def test_capture_contains_required_dimensions(tmp_path):
    """docs/13 §17: the snapshot carries every required section."""
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _drive_claude_appeared(orchestrator)
    orchestrator.handle_turn(session_id, "你说说看")
    snapshot = service.capture(orchestrator, session_id)
    assert snapshot["schema_version"] == SCHEMA_VERSION
    assert set(snapshot) >= {
        "schema_version", "narrative", "messages", "memories",
        "consumed_script_nodes", "script_cursor", "character_states", "presentation",
    }
    # per-character memory scope (docs/13 §17.4)
    assert "memories" in snapshot
    # presentation stable state (docs/13 §17.7)
    assert set(snapshot["presentation"]) == {
        "scene", "present_characters", "emotion", "last_dialogue",
    }
    assert "deepseek" in snapshot["presentation"]["present_characters"]


def _orchestrator_helper_run(orchestrator: GameOrchestrator) -> str:
    """A plain session with at least one completed turn (used where only a
    minimal save is needed)."""
    result = orchestrator.handle_turn(None, "你好")
    return result.session_id


# ── 核心契约: save → mutate → load → restored state == save snapshot ─────

def test_roundtrip_restored_state_equals_save_snapshot(tmp_path):
    """docs/13 Task 6 acceptance, strongest form: capture the full snapshot,
    mutate the live session, load, and require the NEW session's snapshot to
    equal the saved one on every dimension (§17)."""
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _drive_claude_appeared(orchestrator)
    state = orchestrator._state.state_for(session_id)
    state.chapter1.claim_store["CL_CLAUDE_01"] = {
        "character_id": "claude", "fact_refs": ["F1"], "statement_type": "public",
    }
    state.chapter1.resolved_contradictions.add(CT01_CLAUDE_SOURCE_GAP)
    submit_challenge(state, "claude", [CL_CLAUDE_01, CL_CLAUDE_02], [])
    orchestrator.handle_turn(session_id, "然后呢？")  # deepseek memory + mood land

    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    snapshot_a = repo_snapshot = saved.snapshot

    # mutate the live session after the save
    orchestrator.handle_turn(session_id, "我说的是别的事情。")
    orchestrator.handle_investigation_action(session_id, INSPECT_HOTSPOT, CH1_NOTE_01)

    loaded = service.load_save(orchestrator, "p1", saved.id)
    new_id = loaded["session_id"]
    snapshot_b = service.capture(orchestrator, new_id)

    for key in snapshot_a:
        if key == "session_id":
            continue
        assert snapshot_b.get(key) == snapshot_a[key], f"dimension {key!r} diverged"
