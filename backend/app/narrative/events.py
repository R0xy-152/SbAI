"""Deterministic Narrative Event engine (docs/03 §13, §28-31).

A Signal alone never changes State (docs/03 §17): it must go through an
Event, which checks Availability, Trigger and Requirements, then commits its
Narrative Effects atomically (docs/03 §29) and only after the character's
output has succeeded (Validate Before Commit, docs/03 §28). Main-story
events are `once`: repeating the same input never re-fires them (Idempotency,
docs/03 §30). Events are evaluated in list order = priority (docs/03 §31).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.narrative.interpreter import Interpretation
from app.narrative.state import NarrativeState

# Allowed Narrative Effect kinds (docs/03 §13.5).
SET_FLAG = "SET_FLAG"
CLEAR_FLAG = "CLEAR_FLAG"
REVEAL_FACT = "REVEAL_FACT"
SET_SCENE = "SET_SCENE"
SET_STORY_PHASE = "SET_STORY_PHASE"

# The complete set of kinds commit() will accept. Anything outside this set
# fails the whole event before any state is touched (docs/03 §29 atomicity).
ALLOWED_EFFECT_KINDS = frozenset(
    {SET_FLAG, CLEAR_FLAG, REVEAL_FACT, SET_SCENE, SET_STORY_PHASE}
)

ONCE = "once"
REPEATABLE = "repeatable"


@dataclass(frozen=True)
class Effect:
    """One deterministic mutation of Narrative State (docs/03 §13.5)."""

    kind: str
    target: str


@dataclass(frozen=True)
class NarrativeEvent:
    """The smallest deterministic plot-advancement unit (docs/03 §12-13)."""

    event_id: str
    trigger_signals: frozenset[str]
    scene: str = "binding_room"
    story_phase: str = "prologue"
    requirement: Callable[[NarrativeState], bool] = lambda state: True
    effects: tuple[Effect, ...] = ()
    presentation: tuple[str, ...] = ()
    # Narrative Directive (docs/03 §24): authored alongside the event and
    # handed to the current character when this event is selected. It states
    # this turn's narrative goal / allowed scope / forbidden reveals — never
    # exact lines, never a Game State mutation.
    directive: str = ""
    repeat_policy: str = ONCE


@dataclass(frozen=True)
class NarrativeDecision:
    """The outcome of evaluating the current message against eligible events.

    `kind` is "noop" (nothing story-relevant — a normal result, docs/03 §22)
    or "event" (an event selected and ready to commit after the character's
    output succeeds, docs/03 §28).
    """

    kind: str = "noop"
    event_id: str | None = None
    presentation: tuple[str, ...] = ()
    # The selected event's Narrative Directive (docs/03 §24), empty for noop.
    directive: str = ""


class NarrativeEngine:
    def __init__(self, events: list[NarrativeEvent]) -> None:
        self._events = list(events)
        self._by_id = {event.event_id: event for event in self._events}

    def evaluate(self, state: NarrativeState, interpretation: Interpretation) -> NarrativeDecision:
        """Select the highest-priority eligible event for this signal, if any.

        Pure selection: no state is changed here. Idempotency (docs/03 §30),
        availability, trigger and requirements are all checked.
        """
        for event in self._events:  # list order = priority (docs/03 §31)
            if event.repeat_policy == ONCE and event.event_id in state.completed_events:
                continue
            if state.current_scene != event.scene:
                continue
            if state.story_phase != event.story_phase:
                continue
            if interpretation.signal not in event.trigger_signals:
                continue
            if not event.requirement(state):
                continue
            return NarrativeDecision(
                kind="event",
                event_id=event.event_id,
                presentation=event.presentation,
                directive=event.directive,
            )
        return NarrativeDecision(kind="noop")

    def commit(self, state: NarrativeState, decision: NarrativeDecision) -> None:
        """Apply the committed event's effects atomically (docs/03 §29).

        Call only after the character's output succeeded (docs/03 §28).

        Validate First, Apply Second: every effect kind is checked before any
        state is mutated, so an invalid effect anywhere in the event leaves the
        whole state unchanged (including completed_events).
        """
        if decision.kind != "event" or decision.event_id is None:
            return
        event = self._by_id[decision.event_id]
        self._validate_effects(event)
        for effect in event.effects:
            self._apply(state, effect)
        state.completed_events.add(event.event_id)

    @staticmethod
    def _validate_effects(event: NarrativeEvent) -> None:
        for effect in event.effects:
            if effect.kind not in ALLOWED_EFFECT_KINDS:
                raise ValueError(f"unknown effect kind: {effect.kind}")

    @staticmethod
    def _apply(state: NarrativeState, effect: Effect) -> None:
        if effect.kind == SET_FLAG:
            state.narrative_flags.add(effect.target)
        elif effect.kind == CLEAR_FLAG:
            state.narrative_flags.discard(effect.target)
        elif effect.kind == REVEAL_FACT:
            state.revealed_facts.add(effect.target)
        elif effect.kind == SET_SCENE:
            state.current_scene = effect.target
        elif effect.kind == SET_STORY_PHASE:
            state.story_phase = effect.target
        else:
            raise ValueError(f"unknown effect kind: {effect.kind}")
