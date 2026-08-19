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
from datetime import datetime, timezone

from app.game.orchestrator import GameOrchestrator
from app.persistence.repository import _mood_to_dict, _session_to_dict
from app.save.checkpoint import (
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
SCHEMA_VERSION = 1

CHAPTER_ID = "ch1"

# docs/13 §19.3 / §26.3: an unsupported snapshot schema is a distinct, loud
# failure — the player must not get "best-effort restored and keep playing".
logger = logging.getLogger(__name__)


class SaveSchemaError(Exception):
    """The save's snapshot schema_version is not supported (docs/13 §16.2)."""


class SaveLoadError(Exception):
    """The snapshot failed post-restore integrity validation (docs/13 §19.3)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            "emotion": {cid: _mood_to_dict(m) for cid, m in moods.items()},
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
        """Overwrite the single AUTO slot (docs/13 §21). The captured
        checkpoints are the ones the state reaches that the session has not
        already auto-saved (Task 8 side effect, docs/13 §21.2)."""
        # docs/13 §21.3: mark the reached checkpoints BEFORE the capture, so the
        # AUTO snapshot itself carries the just-captured flags. Never
        # save-then-update: a snapshot taken before marking would let a restored
        # session re-capture the same checkpoint (§21.2 once-per-session).
        self._mark_checkpoints(orchestrator, session_id)
        return self._save_slot(
            orchestrator, player_id, session_id, AUTO, None, title=None
        )

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
            chapter_id=CHAPTER_ID,
            phase=snapshot.get("narrative", {}).get("chapter1", {}).get("phase"),
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

    def _mark_checkpoints(
        self, orchestrator: GameOrchestrator, session_id: str
    ) -> None:
        """Persist the captured checkpoints into the session snapshot so they
        are never re-captured on a later commit (docs/13 §21.2)."""
        state = orchestrator._load_known_state(session_id)
        if not pending_checkpoints(state, opened=self._session_opened(orchestrator, session_id)):
            return
        mark_captured(state, opened=self._session_opened(orchestrator, session_id))
        # The state mutation must be re-persisted (as narrative flags); the
        # pending set only differs from reached when a checkpoint was already
        # captured.
        orchestrator._repository.save(orchestrator._snapshot(session_id))
        logger.info(
            "auto save captured checkpoints %s (session %s)",
            sorted(reached_checkpoints(state, opened=True)),
            session_id,
        )

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

    def load_save(
        self, orchestrator: GameOrchestrator, player_id: str, save_id: str
    ) -> dict:
        """Load creates a NEW Active Session from the snapshot (docs/13 §19.1).
        Returns the new session_id + initial GameViewState (docs/13 §20.3)."""
        save = self._repository.get_by_id(save_id)
        if save is None or save.player_id != player_id:
            raise KeyError(f"unknown save: {save_id}")
        if save.schema_version != SCHEMA_VERSION:
            raise SaveSchemaError(
                f"save schema_version {save.schema_version} is not supported "
                f"(current {SCHEMA_VERSION})"
            )
        new_session_id = orchestrator.import_snapshot(save.snapshot)
        return {
            "session_id": new_session_id,
            **orchestrator.gameview_state(new_session_id),
        }

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_manual(self, player_id: str, slot_index: int) -> bool:
        if not 1 <= slot_index <= MANUAL_SLOTS:
            raise ValueError(f"manual slot must be 1..{MANUAL_SLOTS}")
        return self._repository.delete_slot(player_id, MANUAL, slot_index)
