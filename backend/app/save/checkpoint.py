"""Auto Save checkpoint evaluation (docs/13 §21.2, Task 8).

The Auto Save is a *deterministic* checkpoint machine, never "save every
turn": docs/13 §21.1 forbids per-AI-turn autos (mid-stream output, uncommitted
Narrative Event, incomplete Memory writes, needless DB snapshots). Instead a
small set of stable checkpoints is evaluated after a narrative commit, and the
single AUTO slot is overwritten when a checkpoint *transitions* to reached
(docs/13 §21.2 — a re-committed checkpoint must not re-trigger).

The function is pure over NarrativeState (no SaveRepository import), so the
orchestrator can call it as a side effect right after a commit and after the
session is persisted (docs/13 §21.3: commit → checkpoint reached → capture).
"""

from __future__ import annotations

from app.narrative.state import NarrativeState

# docs/13 §21.2: the first-batch stable checkpoints (full list later).
OPENING_COMPLETE = "AS_CH1_OPENING_COMPLETE"
CLAUDE_APPEARED = "AS_CH1_CLAUDE_APPEARED"
INF01_CONFIRMED = "AS_CH1_INF01_CONFIRMED"
INF03_CONFIRMED = "AS_CH1_INF03_CONFIRMED"
RECOVERY_ENTRY = "AS_CH1_RECOVERY_ENTRY"

# All checkpoints reachable by this build. docs/13 §21.2: the first batch is
# Opening Complete / Claude Appeared / INF01 Confirmed / INF03 Confirmed, with
# Recovery Entry satisfied together with INF03 (recovery_required phase).
CHECKPOINT_IDS = (
    OPENING_COMPLETE,
    CLAUDE_APPEARED,
    INF01_CONFIRMED,
    INF03_CONFIRMED,
    RECOVERY_ENTRY,
)


def reached_checkpoints(state: NarrativeState, *, opened: bool = False) -> set[str]:
    """The checkpoints the state currently satisfies (docs/13 §21.2).

    ``opened``: whether the session has actually spoken its opening line (the
    opening is a scripted beat that records the line before any narrative
    flag/phase change, so completion is derived from the session, not the
    state)."""
    reached: set[str] = set()
    if opened:
        reached.add(OPENING_COMPLETE)
    if "claude" in state.chapter1.available_characters:
        reached.add(CLAUDE_APPEARED)
    if "INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR" in state.chapter1.accepted_inferences:
        reached.add(INF01_CONFIRMED)
    if state.chapter1.phase == "recovery_required":
        reached.add(INF03_CONFIRMED)
        reached.add(RECOVERY_ENTRY)
    return reached


def pending_checkpoints(state: NarrativeState, *, opened: bool = False) -> set[str]:
    """Checkpoints the state reaches but the session has not yet auto-saved.

    A captured checkpoint is recorded as a narrative flag (AS_CH1_*), so the
    capture survives persistence and a later commit on the same session never
    re-triggers (docs/13 §21.2)."""
    return reached_checkpoints(state, opened=opened) - set(
        flag for flag in state.narrative_flags if flag in CHECKPOINT_IDS
    )


def mark_captured(state: NarrativeState, *, opened: bool = False) -> None:
    """Record the currently-reached checkpoints as captured (narrative flags)."""
    state.narrative_flags.update(reached_checkpoints(state, opened=opened))
