"""SaveSnapshotService tests (docs/13 Task 6 acceptance + §26.3).

The core contract: save → mutate the current session → load → the NEW Active
Session equals the saved snapshot, for every captured dimension (§17):
Narrative phase / flags / availability, per-character Memory (no cross-role
leak), Messages + visibility, Evidence / Claim / Contradiction / Inference,
Private Interview progress, Scene / Presence / Emotion, and the script cursor.
"""

from __future__ import annotations

import pytest

from app.characters.base import CharacterMood, CharacterResponse, MemoryProposal
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.game.investigation import CH1_NOTE_01, INSPECT_HOTSPOT, PAPER_RUBBING_COMPLETE
from app.game.deduction import (
    CL_CLAUDE_01,
    CL_CLAUDE_02,
    CT01_CLAUDE_SOURCE_GAP,
    submit_deduction,
)
from app.game.private_interview import submit_challenge
from app.persistence.repository import JsonSessionRepository
from app.save.repository import JsonSaveRepository, MANUAL
from app.save.service import SCHEMA_VERSION, SaveSchemaError, SaveSnapshotService
from app.script.fixture import build_script_nodes
from app.script.service import ScriptService


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


def _orchestrator(repository=None, save_service=None, script=None) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": _MemoryRuntime("deepseek"),
            "claude": _Runtime("claude"),
            "chatgpt": _Runtime("chatgpt"),
            "doubao": _Runtime("doubao"),
        },
        repository=repository,
        save_service=save_service,
        script=script,
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
    # P1-6 修复后：AUTO 只在新 checkpoint 时更新——先完成一个回合（Opening
    # Complete checkpoint）再写 AUTO。
    orchestrator.handle_turn(session_id, "你好", player_id="p1")
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


# ── docs/13 Task 8: Auto Save 是 Narrative commit 后的 side effect ─────────

def _task8_orchestrator(tmp_path, service):
    return _orchestrator(
        repository=JsonSessionRepository(tmp_path / "sess"),
        save_service=service,
        # wired opening line so open_turn actually speaks (docs/13 Task 8)
        script=ScriptService(build_script_nodes()),
    )


def test_opening_complete_auto_saves_once(tmp_path):
    """Opening Complete: the opening turn commits + persists, then the AUTO
    slot appears (§21.3 ordering). A second opening (idempotent) does not
    re-capture (§21.2)."""
    service, repo = _service(tmp_path)
    orchestrator = _task8_orchestrator(tmp_path, service)
    result = orchestrator.open_turn(None, player_id="p1")
    session_id = result.session_id
    auto = service.list_saves("p1")["auto"]
    assert auto is not None, "opening complete must auto-save"
    assert auto["phase"] in ("opening", "investigation")
    assert auto["source_session_id"] == session_id
    first_updated = auto["updated_at"]

    # already-opened session → empty turn → no re-capture
    orchestrator.open_turn(session_id, player_id="p1")
    auto2 = service.list_saves("p1")["auto"]
    assert auto2["updated_at"] == first_updated
    # the captured checkpoint is recorded as a narrative flag
    state = orchestrator._state.state_for(session_id)
    assert "AS_CH1_OPENING_COMPLETE" in state.narrative_flags


def test_plain_turn_does_not_auto_save(tmp_path):
    """docs/13 §21.1: an ordinary AI turn never triggers a NEW checkpoint —
    once opening is captured, further plain turns leave the AUTO slot alone."""
    service, _ = _service(tmp_path)
    orchestrator = _task8_orchestrator(tmp_path, service)
    # open the session (scripted opening line → AUTO captures opening complete)
    opened = orchestrator.open_turn(None, player_id="p1")
    session_id = opened.session_id
    auto = service.list_saves("p1")["auto"]
    assert auto is not None
    first_updated = auto["updated_at"]

    # several ordinary turns → no new checkpoint → AUTO unchanged
    for msg in ("你好", "然后呢？", "再说说"):
        orchestrator.handle_turn(session_id, msg, player_id="p1")
    auto2 = service.list_saves("p1")["auto"]
    assert auto2["updated_at"] == first_updated


def test_claude_appeared_auto_saves_after_0317_turn(tmp_path):
    """Claude Appeared: the turn that commits the incident persists, then the
    AUTO slot records claude's availability (no half-Evidence)."""
    service, _ = _service(tmp_path)
    orchestrator = _task8_orchestrator(tmp_path, service)
    inspected = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    )
    session_id = inspected.session_id
    orchestrator.handle_investigation_action(
        session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    # the first player-bound turn captures the (already-reached) opening
    # checkpoint — player_id binds via handle_turn, not the investigation API.
    orchestrator.handle_turn(session_id, "你好", player_id="p1")
    auto = service.list_saves("p1")["auto"]
    assert auto is not None and auto["source_session_id"] == session_id
    assert auto["phase"] == "investigation"
    first_updated = auto["updated_at"]

    # the 03:17 turn commits claude availability → AUTO overwrites (§21.2)
    orchestrator.handle_turn(session_id, "03:17 是什么意思？", player_id="p1")
    state = orchestrator._state.state_for(session_id)
    assert "claude" in state.chapter1.available_characters
    auto2 = service.list_saves("p1")["auto"]
    assert auto2["source_session_id"] == session_id
    assert auto2["updated_at"] > first_updated
    assert "AS_CH1_CLAUDE_APPEARED" in state.narrative_flags


def test_no_player_id_means_no_auto_save(tmp_path):
    """docs/13 §15: player_id is frontend-owned; without a binding the side
    effect is skipped (never fails the turn)."""
    service, _ = _service(tmp_path)
    orchestrator = _task8_orchestrator(tmp_path, service)
    result = orchestrator.handle_turn(None, "你好", player_id=None)
    orchestrator.handle_turn(result.session_id, "03:17", player_id=None)
    assert service.list_saves("p1")["auto"] is None


def test_inf01_and_inf03_auto_save_after_deduction(tmp_path):
    """docs/13 Task 8 acceptance #3/#4: INF01 then INF03 (Recovery Entry) each
    overwrite the AUTO slot; the loaded checkpoint is a legal state
    (recovery_required) with the INF01 evidence — no streaming mid-state /
    half-Evidence / cross-role leak."""
    from app.game.deduction import (
        CL_CLAUDE_01,
        CL_CLAUDE_02,
        CT01_CLAUDE_SOURCE_GAP,
        CT04_GPT_SUMMARY_OMISSION,
    )

    service, _ = _service(tmp_path)
    session_repo = JsonSessionRepository(tmp_path / "sess")
    orchestrator = _task8_orchestrator(tmp_path, service)
    session_id = orchestrator.open_turn(None, player_id="p1").session_id
    # drive the deterministic chain by mutating the AUTHORITATIVE persisted
    # snapshot (the repository is the source _load_known_state restores from;
    # in prod the claims/evidence land via LLM + investigation + interviews).
    persisted = session_repo.load(session_id)
    state = persisted.narrative_state
    state.chapter1.claim_store[CL_CLAUDE_01] = {}
    state.chapter1.claim_store[CL_CLAUDE_02] = {}
    # EV04 + EV05 → INF01 gate
    state.chapter1.acquired_evidence.update(
        {"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"}
    )
    # CT01 → unlock claude private interview → challenge → EV05 stays
    assert submit_deduction(state, "你说没看到 DeepSeek 本人，那你为什么说是她开的？")["outcome"] == "ACCEPTED"
    submit_challenge(state, "claude", [CL_CLAUDE_01, CL_CLAUDE_02], [])
    session_repo.save(persisted)

    inf01 = orchestrator.submit_deduction(
        session_id, "DEEPSEEK#03 和 #04 不是同一个 Instance。", player_id="p1"
    )
    assert inf01["outcome"] == "ACCEPTED"
    after_inf01 = service.list_saves("p1")["auto"]
    assert after_inf01 is not None
    assert "AS_CH1_INF01_CONFIRMED" in orchestrator._state.state_for(session_id).narrative_flags

    # INF03: needs EV06 (INF01 granted) + EV09 (chatgpt private interview)
    persisted = session_repo.load(session_id)
    state = persisted.narrative_state
    # CT04 gate: EV11 + EV06 both in acquired_evidence
    state.chapter1.acquired_evidence.update(
        {"EV11_GPT_SECOND_SUMMARY", "EV01_NOTE_V03"}
    )
    assert submit_deduction(state, "GPT 的摘要遗漏了 Recovered Session 和 V03。")["outcome"] == "ACCEPTED"
    submit_challenge(state, "chatgpt", [], ["EV06_SESSION_REPLAY_MARKER"])
    session_repo.save(persisted)
    inf03 = orchestrator.submit_deduction(
        session_id, "V03 是上一个我；当前 Player 是 V04。", player_id="p1"
    )
    assert inf03["outcome"] == "ACCEPTED"
    after_inf03 = service.list_saves("p1")["auto"]
    assert after_inf03["updated_at"] > after_inf01["updated_at"]
    assert "AS_CH1_INF03_CONFIRMED" in orchestrator._state.state_for(session_id).narrative_flags

    # Continue → restore to the recovery checkpoint (legal state)
    loaded = service.load_save(orchestrator, "p1", after_inf03["id"])
    new_id = loaded["session_id"]
    chapter = orchestrator._state.state_for(new_id).chapter1
    assert chapter.phase == "recovery_required"
    # INF01 evidence came with the checkpoint; no streaming mid-state
    assert "EV06_SESSION_REPLAY_MARKER" in chapter.acquired_evidence
    # no cross-role memory leak: memories only for the characters who actually
    # spoke (the deduction runtime never proposes; the opening spoke deepseek)
    memories = orchestrator._memory.store_for(new_id).snapshot()
    assert set(memories.keys()) <= {"deepseek"}


# ── §26.3: investigation gates after load ─────────────────────────────────

# ── T2review P1-5 / P1-6：AUTO checkpoint 门禁与写失败回滚 ─────────────────


def test_auto_save_rejects_without_pending_checkpoint(tmp_path):
    """普通状态（无新 checkpoint）写 AUTO 被拒，不覆盖唯一合法 checkpoint。"""
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, _ = _service(tmp_path)
    session_id = _acquire_note(orchestrator)
    with pytest.raises(ValueError, match="no new checkpoint"):
        service.save_auto(orchestrator, "p1", session_id)
    assert service.list_saves("p1")["auto"] is None


def test_auto_save_write_failure_keeps_checkpoint_pending(tmp_path, monkeypatch):
    """写失败：checkpoint 标记回滚、保持 pending，后续重试成功（P1-5）。"""
    orchestrator = _orchestrator(repository=JsonSessionRepository(tmp_path / "sess"))
    service, repo = _service(tmp_path)
    session_id = _acquire_note(orchestrator)
    orchestrator.handle_turn(session_id, "你好", player_id="p1")

    def _boom(_save):
        raise OSError("disk full")

    monkeypatch.setattr(repo, "upsert", _boom)
    with pytest.raises(OSError):
        service.save_auto(orchestrator, "p1", session_id)
    state = orchestrator._state.state_for(session_id)
    assert "AS_CH1_OPENING_COMPLETE" not in state.narrative_flags  # 标记已回滚

    monkeypatch.undo()
    save = service.save_auto(orchestrator, "p1", session_id)
    assert save.slot_type == "AUTO"
    assert "AS_CH1_OPENING_COMPLETE" in orchestrator._state.state_for(
        session_id
    ).narrative_flags


def test_investigation_gates_behave_identically_after_load(tmp_path):
    """docs/13 §26.3: 推进到 EV01 → 03:17 确定性 Gate（轮数兜底 counter=2，
    消息不含 03:17 字样，D6）→ EV04/EV05 → INF01 ACCEPTED 后存档；Load 的新
    Active Session 中所有闸门保持关闭：推理重复提交 ALREADY_ACCEPTED（副作用
    不重放）、03:17 轮数计数恢复、纸条 hotspot 仍 completed（重复检查
    ALREADY_COMPLETED）、在场角色仍含 deepseek+claude。"""
    from app.game.deduction import INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR

    session_repo = JsonSessionRepository(tmp_path / "sess")
    orchestrator = _orchestrator(repository=session_repo)
    service, _ = _service(tmp_path)

    # 1. 纸条（EV01）→ PRE_0317_WINDOW（首个物理交互开场，deepseek 入场）
    session_id = _acquire_note(orchestrator)
    # 2. 两个普通回合 → counter=2 → 03:17 确定性 Gate 自动发生（B 分支）
    orchestrator.handle_turn(session_id, "你好")
    orchestrator.handle_turn(session_id, "然后呢？")
    state = orchestrator._state.state_for(session_id)
    assert state.chapter1.pre_0317_player_turns == 2
    assert "claude" in state.chapter1.available_characters
    assert "EV_CH1_CLAUDE_APPEARS" in state.completed_events

    # 3. EV04 + EV05 → CT01 → Claude 私审 → INF01 ACCEPTED
    persisted = session_repo.load(session_id)
    pstate = persisted.narrative_state
    pstate.chapter1.claim_store[CL_CLAUDE_01] = {}
    pstate.chapter1.claim_store[CL_CLAUDE_02] = {}
    pstate.chapter1.acquired_evidence.update(
        {"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"}
    )
    assert submit_deduction(
        pstate, "你说没看到 DeepSeek 本人，那你为什么说是她开的？"
    )["outcome"] == "ACCEPTED"
    submit_challenge(pstate, "claude", [CL_CLAUDE_01, CL_CLAUDE_02], [])
    session_repo.save(persisted)

    inf01 = orchestrator.submit_deduction(
        session_id, "DEEPSEEK#03 和 #04 不是同一个 Instance。", player_id="p1"
    )
    assert inf01["outcome"] == "ACCEPTED"
    assert (
        INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR
        in orchestrator._state.state_for(session_id).chapter1.accepted_inferences
    )

    # 4. save → load 新 Active Session（docs/13 §19.1）
    saved = service.save_manual(orchestrator, "p1", session_id, 1)
    loaded = service.load_save(orchestrator, "p1", saved.id)
    new_id = loaded["session_id"]
    assert new_id != session_id
    # docs/13 §20.3 契约：history = {session_id, messages}，最后一条角色台词
    # 是 03:17 序列的 DS 行（供前端恢复展示）
    assert isinstance(loaded["history"], dict)
    assert loaded["history"]["session_id"] == new_id
    last_character = next(
        (m for m in reversed(loaded["history"]["messages"]) if m.get("role") == "character"),
        None,
    )
    assert last_character is not None
    assert last_character["character_id"] == "deepseek"
    assert last_character["content"] == "……你、你怎么会在这里？！"
    chapter = orchestrator._state.state_for(new_id).chapter1

    # 5. 所有闸门与存档时一致，不重开
    assert INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR in chapter.accepted_inferences
    again = orchestrator.submit_deduction(
        new_id, "DEEPSEEK#03 和 #04 不是同一个 Instance。", player_id="p1"
    )
    assert again["outcome"] == "ALREADY_ACCEPTED"
    assert orchestrator._state.state_for(new_id).chapter1.pre_0317_player_turns == 2
    assert chapter.hotspot_states[CH1_NOTE_01] == "completed"
    repeated = orchestrator.handle_investigation_action(
        new_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    assert repeated.outcome == "ALREADY_COMPLETED"
    available = orchestrator._state.state_for(new_id).chapter1.available_characters
    assert {"deepseek", "claude"} <= available
