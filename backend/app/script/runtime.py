"""Script Runtime — plays fixed deterministic content under Narrative authority
(docs/12 §32-33).

The runtime walks a sequence of Script Events and *proposes* what should happen:
presentation actions for the Frontend, fixed dialogue lines, and Script Intents
(unlock / phase_transition). It never mutates NarrativeState itself — the
orchestrator routes each intent through the Narrative Runtime, which validates
before any Game State changes (docs/12 §25.2, §33).

Execution semantics:
- ``advance`` is a read-only plan: it walks from the per-session cursor to the
  first boundary (player_input / false narrative_gate / end / ai_dialogue).
- ``commit`` is the only cursor mutation; the orchestrator calls it only after
  routing intents succeeded, so a routing failure leaves the cursor untouched
  and the turn can be retried cleanly.
- A false ``narrative_gate`` keeps the cursor on the gate step: protected events
  never advance (docs/12 §24), and the script quietly retries later.
- ``character_show`` re-checks Character Availability (docs/12 §17, §40.3): a
  script can never conjure a character the Narrative Runtime has not unlocked —
  unless an ``unlock`` intent earlier in the same window proposed exactly that
  (routed before the show reaches the Frontend).

One active script per session; a completed script is never begun again
(once + idempotent, docs/12 §40.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.presentation.actions import PresentationAction
from app.script.chapter1_content import ScriptSequenceLine
from app.script.conditions import evaluate_condition
from app.script.registry import ScriptRegistry
from app.script.schema import (
    AiDialogueStep,
    BackgroundStep,
    CharacterHideStep,
    CharacterShowStep,
    CharacterUpdateStep,
    NarrativeGateStep,
    PhaseTransitionStep,
    PlayerInputStep,
    PresentationStep,
    ScriptDialogueStep,
    ScriptError,
    ScriptSequence,
    UnlockStep,
)

# presentation-step action → structured PresentationAction type (docs/12 §23).
_PRESENTATION_MAP = {
    "screen_glitch": "SCREEN_GLITCH",
    "screen_shake": "SCREEN_SHAKE",
    "dialogue_focus": "DIALOGUE_FOCUS",
    "input_lock": "INPUT_LOCK",
    "input_unlock": "INPUT_UNLOCK",
}


@dataclass(frozen=True)
class ScriptIntent:
    kind: str  # "unlock" | "phase_transition"
    target: str
    script_id: str
    step_index: int


@dataclass
class ScriptPlan:
    """The read-only result of an advance: what to present, what to route."""

    script_id: str | None
    status: str  # "idle" | "complete" | "paused_player_input" | "paused_gate"
    lines: tuple[ScriptSequenceLine, ...] = ()
    actions: tuple[PresentationAction, ...] = ()
    intents: tuple[ScriptIntent, ...] = ()
    legacy_presentation: tuple[str, ...] = ()
    next_step_index: int = 0


@dataclass
class ScriptCursorState:
    script_id: str
    step_index: int = 0
    status: str = "running"  # running | paused_player_input | paused_gate | complete


class ScriptRuntime:
    """Per-session cursor executor over a ScriptRegistry."""

    def __init__(
        self,
        registry: ScriptRegistry,
        conditions: Callable[[str, object, str], bool] = evaluate_condition,
    ) -> None:
        self._registry = registry
        self._conditions = conditions
        self._cursors: dict[str, ScriptCursorState] = {}

    # ---- session cursor lifecycle ------------------------------------------

    def maybe_start(self, session_id: str, state, player_message: str = "") -> None:
        """Begin the first eligible, not-yet-run script (docs/12 §29 trigger).

        Read-only except for recording the new active cursor. If a script is
        already active (paused mid-way), nothing new begins.
        """
        if self.is_active(session_id):
            return
        for condition_id, script_id in self._registry.triggers():
            if not self._conditions(condition_id, state, player_message):
                continue
            if self.is_completed(session_id, script_id):
                continue
            self._cursors[session_id] = ScriptCursorState(script_id=script_id)
            return

    def is_active(self, session_id: str) -> bool:
        cursor = self._cursors.get(session_id)
        return cursor is not None and cursor.status in (
            "running",
            "paused_player_input",
            "paused_gate",
        )

    def active_script(self, session_id: str) -> str | None:
        cursor = self._cursors.get(session_id)
        if cursor is None or not self.is_active(session_id):
            return None
        return cursor.script_id

    def is_completed(self, session_id: str, script_id: str) -> bool:
        cursor = self._cursors.get(session_id)
        return cursor is not None and cursor.script_id == script_id and cursor.status == "complete"

    # ---- planning ----------------------------------------------------------

    def advance(
        self,
        session_id: str,
        state,
        *,
        player_message: str = "",
        available: Callable[[str], bool],
        on_ai: Callable[[str, str | None], ScriptSequenceLine | None] | None = None,
    ) -> ScriptPlan:
        """Plan the next window of steps without mutating the cursor.

        ``available(character_id)`` is the orchestrator's authoritative
        availability predicate (system and the default character always pass).
        ``on_ai`` resolves an ``ai_dialogue`` step into a line; without it an
        ``ai_dialogue`` step fails closed.
        """
        cursor = self._cursors.get(session_id)
        if cursor is None or cursor.script_id is None:
            return ScriptPlan(script_id=None, status="idle")
        if cursor.status == "complete":
            return ScriptPlan(script_id=cursor.script_id, status="complete")

        script: ScriptSequence = self._registry.get(cursor.script_id)
        steps = script.steps
        lines: list[ScriptSequenceLine] = []
        actions: list[PresentationAction] = []
        intents: list[ScriptIntent] = []
        legacy: list[str] = []
        pending_unlocks: set[str] = set()
        index = cursor.step_index

        while index < len(steps):
            step = steps[index]
            if isinstance(step, NarrativeGateStep):
                if not self._conditions(step.condition, state, player_message):
                    return self._plan(
                        cursor.script_id, "paused_gate", index,
                        lines, actions, intents, legacy,
                    )
            elif isinstance(step, PlayerInputStep):
                index += 1
                if index >= len(steps):
                    return self._plan(
                        cursor.script_id, "complete", index,
                        lines, actions, intents, legacy,
                    )
                return self._plan(
                    cursor.script_id, "paused_player_input", index,
                    lines, actions, intents, legacy,
                )
            elif isinstance(step, ScriptDialogueStep):
                node = self._registry.dialogue(step.node)
                lines.append(
                    ScriptSequenceLine(
                        node.character,
                        node.text,
                        emotion=node.emotion,
                        animation=node.animation,
                    )
                )
            elif isinstance(step, PresentationStep):
                action_type = _PRESENTATION_MAP[step.action]
                actions.append(
                    PresentationAction(type=action_type, intensity=step.intensity)
                )
            elif isinstance(step, BackgroundStep):
                action_type = (
                    "BACKGROUND_FADE" if step.transition == "fade" else "BACKGROUND_SET"
                )
                actions.append(
                    PresentationAction(
                        type=action_type, background=step.background, transition=step.transition
                    )
                )
            elif isinstance(step, CharacterShowStep):
                # docs/12 §17: character_show cannot conjure an unavailable
                # character — unless the same window proposed its unlock.
                if not (available(step.character) or step.character in pending_unlocks):
                    raise ScriptError(
                        cursor.script_id,
                        index,
                        f"character {step.character!r} is not available",
                    )
                actions.append(
                    PresentationAction(
                        type="CHARACTER_SHOW",
                        character_id=step.character,
                        emotion=step.emotion,
                        slot=step.slot,
                        animation=step.animation,
                    )
                )
                legacy.extend(("SHOW_CHARACTER", step.character))
            elif isinstance(step, CharacterHideStep):
                actions.append(
                    PresentationAction(
                        type="CHARACTER_HIDE",
                        character_id=step.character,
                        animation=step.animation,
                    )
                )
                legacy.extend(("HIDE_CHARACTER", step.character))
            elif isinstance(step, CharacterUpdateStep):
                # docs/12 §19: presentation-only updates (emotion/slot/scale/
                # offset/animation) — never knowledge/memory/phase.
                if step.emotion is not None or step.slot is not None or step.scale is not None \
                        or step.offset_x is not None or step.offset_y is not None:
                    actions.append(
                        PresentationAction(
                            type="CHARACTER_EMOTION",
                            character_id=step.character,
                            emotion=step.emotion,
                            slot=step.slot,
                            scale=step.scale,
                            offset_x=step.offset_x,
                            offset_y=step.offset_y,
                        )
                    )
                    if step.emotion is not None:
                        legacy.extend(("SET_EMOTION", step.character, step.emotion))
                if step.animation is not None:
                    actions.append(
                        PresentationAction(
                            type="CHARACTER_ANIMATION",
                            character_id=step.character,
                            animation=step.animation,
                        )
                    )
            elif isinstance(step, AiDialogueStep):
                if on_ai is None:
                    raise ScriptError(
                        cursor.script_id,
                        index,
                        "ai_dialogue requires an on_ai callback",
                    )
                line = on_ai(step.character, step.directive)
                if line is not None:
                    lines.append(line)
            elif isinstance(step, UnlockStep):
                intents.append(ScriptIntent("unlock", step.target, cursor.script_id, index))
                pending_unlocks.add(step.target)
            elif isinstance(step, PhaseTransitionStep):
                intents.append(ScriptIntent("phase_transition", step.to, cursor.script_id, index))
            index += 1

        return self._plan(
            cursor.script_id, "complete", index,
            lines, actions, intents, legacy,
        )

    @staticmethod
    def _plan(
        script_id: str,
        status: str,
        next_step_index: int,
        lines: list[ScriptSequenceLine],
        actions: list[PresentationAction],
        intents: list[ScriptIntent],
        legacy: list[str],
    ) -> ScriptPlan:
        return ScriptPlan(
            script_id=script_id,
            status=status,
            lines=tuple(lines),
            actions=tuple(actions),
            intents=tuple(intents),
            legacy_presentation=tuple(legacy),
            next_step_index=next_step_index,
        )

    def commit(self, session_id: str, plan: ScriptPlan) -> None:
        """Advance the cursor to the planned position (only cursor mutation)."""
        cursor = self._cursors.get(session_id)
        if cursor is None or cursor.script_id != plan.script_id:
            return
        cursor.step_index = plan.next_step_index
        cursor.status = plan.status

    # ---- persistence -------------------------------------------------------

    def snapshot(self, session_id: str) -> dict | None:
        cursor = self._cursors.get(session_id)
        if cursor is None or cursor.script_id is None:
            return None
        return {
            "script_id": cursor.script_id,
            "step_index": cursor.step_index,
            "status": cursor.status,
        }

    def restore(self, session_id: str, data: dict | None) -> None:
        if data is None:
            self._cursors.pop(session_id, None)
            return
        self._cursors[session_id] = ScriptCursorState(
            script_id=data["script_id"],
            step_index=data["step_index"],
            status=data["status"],
        )
