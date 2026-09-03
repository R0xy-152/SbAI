"""SaveSnapshotService (docs/13 §14.2, §17-19, Task 6).

Backend-authoritative Save Capture: the snapshot is produced from the
orchestrator's canonical state (Narrative / Script cursor / Game State /
per-character Memory / Message history + visibility / Evidence / Claim /
Contradiction / Inference / Private Interview progress / Scene / Presence /
Emotion), never from Frontend claims (docs/13 §14.1-14.2). Load follows
docs/13 §19.1: a Save becomes a NEW Active Session restored from the snapshot
— the old session is never edited in place.

One logical-time-point consistency (docs/13 §18): the capture is a single
orchestrator._snapshot() read, so Narrative and Memory can never be from
different moments. Storage is all-or-nothing at the repository layer (a single
transaction / atomic file write).
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone

from app.game.orchestrator import GameOrchestrator
from app.persistence.repository import _mood_to_dict, _session_to_dict
from app.save.checkpoint import (
    CHECKPOINT_IDS,
    mark_captured,
    pending_checkpoints,
    reached_checkpoints,
)
from app.save.repository import (
    AUTO,
    MANUAL,
    MANUAL_SLOTS,
    GameSave,
    SaveRepository,
    new_save_id,
)

# docs/13 §16.2: the snapshot schema version, saved from the first version.
# A structural change to the snapshot must bump this and add a Migration;
# silently changing JSON structure is forbidden.
SCHEMA_VERSION = 2
OLDEST_SUPPORTED_SCHEMA_VERSION = 1

CHAPTER_ID = "ch1"

# T2review P1-4：Load 前的快照不变量白名单。
KNOWN_PHASES = {
    "opening",
    "investigation",
    "recovery_required",
    "recovery",
    "security_review",
    "bad_end",
    "to_be_continued",
}
KNOWN_SCENES = {
    "binding_room",
    "ROOM_A",
    "RECOVERY_REQUIRED",
    "RECOVERY_CORE",
    "SECURITY_REVIEW",
    "BOUNDARY_BREACH",
    "BAD_END_CHAT",
}
KNOWN_CHARACTERS = {"deepseek", "claude", "chatgpt", "doubao"}

# docs/13 §19.3 / §26.3: an unsupported snapshot schema is a distinct, loud
# failure — the player must not get "best-effort restored and keep playing".
logger = logging.getLogger(__name__)


class SaveSchemaError(Exception):
    """The save's snapshot schema_version is not supported (docs/13 §16.2)."""


class SaveLoadError(Exception):
    """The snapshot failed post-restore integrity validation (docs/13 §19.3)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _migrate_snapshot(snapshot: dict, schema_version: int) -> dict:
    """Return a current-version copy of a supported save snapshot.

    v1 stored ``character_states[character_id]`` as a flat mood object. v2
    stores the complete CharacterState while remaining tolerant of the short-
    lived nested-v1 shape written by the feature branch before this migration.
    """
    if not OLDEST_SUPPORTED_SCHEMA_VERSION <= schema_version <= SCHEMA_VERSION:
        raise SaveSchemaError(
            f"save schema_version {schema_version} is not supported "
            f"(supported {OLDEST_SUPPORTED_SCHEMA_VERSION}..{SCHEMA_VERSION})"
        )

    migrated = deepcopy(snapshot)
    if schema_version == 1:
        states = migrated.get("character_states") or {}
        migrated_states: dict[str, dict] = {}
        for character_id, value in states.items():
            if isinstance(value, dict) and "mood" in value:
                migrated_states[character_id] = {
                    "mood": value.get("mood"),
                    "last_reasoning": value.get("last_reasoning", ""),
                    "relationship_stage": value.get("relationship_stage", ""),
                }
            else:
                migrated_states[character_id] = {
                    "mood": value,
                    "last_reasoning": "",
                    "relationship_stage": "",
                }
        migrated["character_states"] = migrated_states
        migrated["schema_version"] = 2
    return migrated


class SaveSnapshotService:
    """Coordinates Capture / Save / List / Load against one SaveRepository."""

    def __init__(self, repository: SaveRepository) -> None:
        self._repository = repository

    # ── Capture ────────────────────────────────────────────────────────────

    def capture(self, orchestrator: GameOrchestrator, session_id: str) -> dict:
        """The deterministic full snapshot of one session (docs/13 §17).

        A single authoritative read, so Narrative and Memory are from the same
        logical moment (docs/13 §18). The Frontend never supplies any of this.
        """
        persisted = orchestrator._snapshot(session_id)
        data = _session_to_dict(persisted)
        data["schema_version"] = SCHEMA_VERSION
        # docs/13 §17.7: the presentation stable state, derived — never
        # transient animation frames.
        data["presentation"] = self._presentation_slice(orchestrator, session_id)
        return data

    @staticmethod
    def _presentation_slice(orchestrator: GameOrchestrator, session_id: str) -> dict:
        state = orchestrator._load_known_state(session_id)
        chapter = state.chapter1
        moods = orchestrator._character_state.snapshot(session_id)
        history = orchestrator.get_history(session_id)
        last_dialogue = next(
            (m for m in reversed(history) if m.get("role") == "character"), None
        )
        return {
            "scene": state.current_scene,
            "present_characters": sorted(
                set(chapter.available_characters) | {"deepseek"}
            ),
            "emotion": {
                cid: _mood_to_dict(m.mood)
                for cid, m in moods.items()
                if m.mood is not None
            },
            "last_dialogue": last_dialogue,
        }

    # ── Save ──────────────────────────────────────────────────────────────

    def save_manual(
        self,
        orchestrator: GameOrchestrator,
        player_id: str,
        session_id: str,
        slot_index: int,
        title: str | None = None,
    ) -> GameSave:
        if not 1 <= slot_index <= MANUAL_SLOTS:
            raise ValueError(f"manual slot must be 1..{MANUAL_SLOTS}")
        return self._save_slot(
            orchestrator, player_id, session_id, MANUAL, slot_index, title=title
        )

    def save_auto(
        self, orchestrator: GameOrchestrator, player_id: str, session_id: str
    ) -> GameSave:
        """Overwrite the single AUTO slot (docs/13 §21)。

        T2review P1-5 / P1-6 修复：
        - 仅当存在新 checkpoint 时允许写 AUTO——普通回合不得覆盖唯一
          合法 checkpoint（Continue 的确定性保证）；
        - checkpoint 标记在内存中先置（AUTO 快照携带刚捕获的标志，
          docs/13 §21.3 不变），但只在 AUTO 写入成功后持久化；写入失败回滚
          内存标志，checkpoint 保持 pending，后续回合可重试（不再被吞掉）。"""
        state = orchestrator._load_known_state(session_id)
        opened = self._session_opened(orchestrator, session_id)
        if not pending_checkpoints(state, opened=opened):
            raise ValueError(
                "no new checkpoint: the AUTO slot only updates on checkpoints"
            )
        # docs/13 §21.3：先标记并把标志持久化进会话快照，AUTO 捕获的快照才能
        # 携带刚捕获的标志（capture 内部会经 _load_known_state 重新加载）。
        mark_captured(state, opened=opened)
        orchestrator._repository.save(orchestrator._snapshot(session_id))
        try:
            save = self._save_slot(
                orchestrator, player_id, session_id, AUTO, None, title=None
            )
        except Exception:
            # T2review P1-5：写入失败回滚标志并再次持久化——checkpoint 保持
            # pending，后续回合可重试（不再被永久吞掉）。
            live = orchestrator._load_known_state(session_id)
            live.narrative_flags.difference_update(CHECKPOINT_IDS)
            orchestrator._repository.save(orchestrator._snapshot(session_id))
            raise
        logger.info(
            "auto save captured checkpoints %s (session %s)",
            sorted(reached_checkpoints(state, opened=True)),
            session_id,
        )
        return save

    def _save_slot(
        self,
        orchestrator: GameOrchestrator,
        player_id: str,
        session_id: str,
        slot_type: str,
        slot_index: int | None,
        title: str | None,
    ) -> GameSave:
        existing = self._repository.get_slot(player_id, slot_type, slot_index)
        now = _now()
        snapshot = self.capture(orchestrator, session_id)
        story_cursor = snapshot.get("story_cursor") or {}
        is_prologue = story_cursor.get("story_id") == "prologue"
        save = GameSave(
            # Overwriting a slot keeps its id and created_at (stable identity
            # across overwrites, docs/13 §16.1); updated_at always moves.
            id=existing.id if existing is not None else new_save_id(),
            player_id=player_id,
            slot_type=slot_type,
            slot_index=slot_index,
            title=title if title is not None else (existing.title if existing else None),
            source_session_id=session_id,
            schema_version=SCHEMA_VERSION,
            snapshot=snapshot,
            chapter_id="prologue" if is_prologue else CHAPTER_ID,
            phase=(
                story_cursor.get("phase")
                if is_prologue
                else snapshot.get("narrative", {}).get("chapter1", {}).get("phase")
            ),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        self._repository.upsert(save)
        return save

    def _session_opened(self, orchestrator: GameOrchestrator, session_id: str) -> bool:
        """Whether the session has actually spoken its opening line (a message
        was recorded). The opening is a scripted beat that lands before any
        narrative flag change, so completion is derived from history."""
        return bool(orchestrator.get_history(session_id))

    # ── Trigger helper (docs/13 §21.3 / Task 8) ────────────────────────────

    def auto_save_pending(
        self, orchestrator: GameOrchestrator, player_id: str, session_id: str
    ) -> GameSave | None:
        """The Task 8 side effect: capture the AUTO slot when the session has
        pending checkpoints, and only then. Called after the narrative commit
        and after the session is persisted. Returns the new save, or None when
        no checkpoint newly reached."""
        state = orchestrator._load_known_state(session_id)
        if not pending_checkpoints(
            state, opened=self._session_opened(orchestrator, session_id)
        ):
            return None
        return self.save_auto(orchestrator, player_id, session_id)

    def auto_save_story(
        self, orchestrator: GameOrchestrator, player_id: str, session_id: str
    ) -> GameSave:
        """快速上线故事模式自动存档：场景边界 / 选项提交即 checkpoint。

        与 auto_save_pending 不同：故事模式没有 Narrative checkpoint 机，
        「场景边界」就是唯一权威检查点（story_runtime.py 在 advance 时标记
        scene_changed，选项提交恒为检查点），因此这里无条件覆写 AUTO slot。
        普通回合绝不调用本方法（docs/13 §21.1 约束只适用于旧玩法）。"""
        return self._save_slot(
            orchestrator, player_id, session_id, AUTO, None, title=None
        )

    # ── List ──────────────────────────────────────────────────────────────

    def list_saves(self, player_id: str) -> dict:
        """docs/13 §20.1: {auto, manual:[6]} — empty slots renderable by the
        Frontend, auto at most one."""
        saves = self._repository.list_by_player(player_id)
        auto = next(
            (s for s in saves if s.slot_type == AUTO and s.slot_index is None), None
        )
        by_index = {
            s.slot_index: s for s in saves if s.slot_type == MANUAL and s.slot_index
        }
        return {
            "auto": auto.info() if auto is not None else None,
            "manual": [
                by_index[i].info() if i in by_index else None
                for i in range(1, MANUAL_SLOTS + 1)
            ],
        }

    # ── Load ──────────────────────────────────────────────────────────────

    def _validate_snapshot_invariants(self, snapshot: dict) -> None:
        """T2review P1-4：Load 前在不可变快照上校验不变量——篡改角色可用性 /
        phase / scene / 消息形状的快照一律拒绝，不允许「先写入后验证」。"""
        narrative = snapshot.get("narrative")
        if not isinstance(narrative, dict):
            raise SaveLoadError("snapshot narrative is missing")
        chapter1 = narrative.get("chapter1")
        if not isinstance(chapter1, dict):
            raise SaveLoadError("snapshot chapter1 is missing")
        phase = chapter1.get("phase")
        if phase not in KNOWN_PHASES:
            raise SaveLoadError(f"unknown chapter phase: {phase!r}")
        scene = narrative.get("current_scene")
        if scene not in KNOWN_SCENES:
            raise SaveLoadError(f"unknown scene: {scene!r}")
        available = set(chapter1.get("available_characters") or [])
        if not available.issubset(KNOWN_CHARACTERS):
            raise SaveLoadError("available_characters contains unknown ids")
        messages = snapshot.get("messages")
        if not isinstance(messages, list):
            raise SaveLoadError("messages is not a list")
        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in {"player", "character"}
            ):
                raise SaveLoadError("invalid message record")

    def load_save(
        self, orchestrator: GameOrchestrator, player_id: str, save_id: str
    ) -> dict:
        """Load creates a NEW Active Session from the snapshot (docs/13 §19.1).
        Returns the new session_id + initial GameViewState (docs/13 §20.3)."""
        save = self._repository.get_by_id(save_id)
        if save is None or save.player_id != player_id:
            raise KeyError(f"unknown save: {save_id}")
        snapshot = _migrate_snapshot(save.snapshot, save.schema_version)
        self._validate_snapshot_invariants(snapshot)
        new_session_id = orchestrator.import_snapshot(snapshot)
        # 故事进度摘要：前端据此路由（故事存档 → /story；已完结/旧玩法存档
        # → /game），不改变 GameViewState 契约（docs/17 结局后自由聊天）。
        progress = orchestrator.story_progress(new_session_id)
        return {
            "session_id": new_session_id,
            **progress,
            **orchestrator.gameview_state(new_session_id),
        }

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_manual(self, player_id: str, slot_index: int) -> bool:
        if not 1 <= slot_index <= MANUAL_SLOTS:
            raise ValueError(f"manual slot must be 1..{MANUAL_SLOTS}")
        return self._repository.delete_slot(player_id, MANUAL, slot_index)
