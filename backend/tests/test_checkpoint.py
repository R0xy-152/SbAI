"""Auto Save checkpoint tests (docs/13 §21.2 / §21.3, Task 8).

The checkpoint machine is deterministic: a checkpoint is reached from
NarrativeState, auto-saved at most once per session, and only ever AFTER the
state commit + session persist (the side-effect ordering is covered by
test_save_service / the API tests). A plain opening or an ordinary chat turn
must never auto-save (§21.1: no per-turn autos).
"""

from __future__ import annotations

from app.game.deduction import submit_deduction
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative.state import NarrativeState
from app.save.checkpoint import (
    CLAUDE_APPEARED,
    INF01_CONFIRMED,
    INF03_CONFIRMED,
    OPENING_COMPLETE,
    RECOVERY_ENTRY,
    mark_captured,
    pending_checkpoints,
    reached_checkpoints,
)
from app.save.service import SaveSnapshotService
from app.save.repository import JsonSaveRepository


def test_fresh_state_reaches_no_checkpoints():
    reached = reached_checkpoints(NarrativeState())
    assert reached == set()


def test_opening_complete_reached_after_first_interaction():
    """OPENING_COMPLETE derives from the session actually speaking the opening
    line (§21.2) — a state alone (flags/phase) does not imply it."""
    state = NarrativeState()
    assert OPENING_COMPLETE not in reached_checkpoints(state)
    # once the opening line was spoken, the checkpoint is reached
    assert OPENING_COMPLETE in reached_checkpoints(state, opened=True)


def test_claude_appeared_reached_from_availability():
    state = NarrativeState()
    state.chapter1.available_characters.add("claude")
    assert CLAUDE_APPEARED in reached_checkpoints(state)


def test_inf01_and_inf03_reached_from_deduction():
    """INF01 lands via the deduction runtime; INF03 additionally drives
    recovery_required and satisfies RECOVERY_ENTRY too (§21.2)."""
    state = NarrativeState()
    chapter = state.chapter1
    # INF01 gate: EV04 + EV05 (docs/10 §INF01)
    chapter.acquired_evidence.update(
        {"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"}
    )
    assert submit_deduction(state, "#03 不是日志里的")["outcome"] == "ACCEPTED"
    assert INF01_CONFIRMED in reached_checkpoints(state)
    assert INF03_CONFIRMED not in reached_checkpoints(state)

    # INF03 gate: EV01 + EV06 + EV09 (docs/10 §INF03)
    chapter.acquired_evidence.update(
        {"EV01_NOTE_V03", "EV06_SESSION_REPLAY_MARKER", "EV09_CURRENT_PLAYER_SUBJECT"}
    )
    assert submit_deduction(state, "上一个我")["outcome"] == "ACCEPTED"
    assert state.chapter1.phase == "recovery_required"
    reached = reached_checkpoints(state)
    assert INF03_CONFIRMED in reached
    assert RECOVERY_ENTRY in reached


def test_duplicate_checkpoint_never_returns_pending():
    """Once a checkpoint is captured (narrative flag), it is no longer
    pending — a later commit on the same session must not re-capture (§21.2)."""
    state = NarrativeState()
    mark_captured(state, opened=True)
    assert OPENING_COMPLETE in state.narrative_flags
    assert pending_checkpoints(state, opened=True) == set()


def test_pending_only_contains_newly_reached():
    state = NarrativeState()
    state.chapter1.available_characters.add("claude")
    state.narrative_flags.add(CLAUDE_APPEARED)
    # a checkpoint already captured is not pending
    assert pending_checkpoints(state) == set()


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        from app.characters.base import CharacterResponse

        return CharacterResponse(
            character_id=self.character_id, dialogue=f"{self.character_id} 回应。"
        )

    def safe_fallback(self):
        from app.characters.base import CharacterResponse

        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


def _orchestrator(repository=None, save_service=None) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": _Runtime("deepseek"),
            "claude": _Runtime("claude"),
            "chatgpt": _Runtime("chatgpt"),
            "doubao": _Runtime("doubao"),
        },
        repository=repository,
        save_service=save_service,
    )
