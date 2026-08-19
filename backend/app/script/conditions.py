"""Narrative Gate conditions (docs/12 §24).

A gate does not compute anything itself — it asks the Narrative Runtime whether a
condition currently holds, by evaluating a pure predicate over the authoritative
NarrativeState. Predicates never mutate state; only the orchestrator owns
narrative mutation. An unknown condition id fails closed (docs/12 §37).
"""

from __future__ import annotations

from typing import Callable

from app.narrative.state import NarrativeState
from app.script.schema import ScriptLoadError

Condition = Callable[[NarrativeState, str], bool]

_0317_TOKENS = ("03:17", "0317", "三点十七")


def _discusses_0317(message: str) -> bool:
    normalized = message.lower().replace(" ", "")
    return any(token in normalized for token in _0317_TOKENS)


def _incident_0317_ready(state: NarrativeState, message: str) -> bool:
    """03:17 is eligible after EV01 inside the window, before Claude appears.

    The A/B safe progression trigger (docs/12 §29): the player either asks about
    03:17 or completes a couple of ordinary interactions — they can never soft-
    lock by not asking the exact question.
    """
    chapter = state.chapter1
    if (
        "PRE_0317_WINDOW" not in state.narrative_flags
        or "EV01_NOTE_V03" not in chapter.acquired_evidence
        or "claude" in chapter.available_characters
        or "EV_CH1_CLAUDE_APPEARS" in state.completed_events
    ):
        return False
    return _discusses_0317(message) or chapter.pre_0317_player_turns >= 2


def _gpt_arrival_ready(state: NarrativeState, message: str) -> bool:
    """GPT's arrival presentation plays only after the deduction runtime granted
    him (INF01 → chatgpt_has_appeared, docs/10 §INF01)."""
    return (
        "chatgpt_has_appeared" in state.narrative_flags
        and "chatgpt" in state.chapter1.available_characters
    )


def _doubao_arrival_ready(state: NarrativeState, message: str) -> bool:
    """Doubao arrives after GPT's first turn lands (mirrors the legacy
    ``_advance_after_character_turn`` timing)."""
    return (
        "chatgpt_first_turn_done" in state.narrative_flags
        and "doubao" not in state.chapter1.available_characters
    )


def _inf03_accepted(state: NarrativeState, message: str) -> bool:
    """Final reveal plays only after INF03 committed recovery_required."""
    return state.chapter1.phase == "recovery_required"


def _ct01_confirmed(state: NarrativeState, message: str) -> bool:
    """Claude's private-interview unlock condition (docs/12 §24 example)."""
    return "CT01_CLAUDE_SOURCE_GAP" in state.chapter1.resolved_contradictions


def _inf01_complete(state: NarrativeState, message: str) -> bool:
    """INF01 accepted with GPT on stage (deduction already granted him)."""
    return (
        "INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR" in state.chapter1.accepted_inferences
        and "chatgpt" in state.chapter1.available_characters
    )


CONDITION_REGISTRY: dict[str, Condition] = {
    "INCIDENT_0317_READY": _incident_0317_ready,
    "GPT_ARRIVAL_READY": _gpt_arrival_ready,
    "DOUBAO_ARRIVAL_READY": _doubao_arrival_ready,
    "INF03_ACCEPTED": _inf03_accepted,
    "CT01_CONFIRMED": _ct01_confirmed,
    "INF01_COMPLETE": _inf01_complete,
}


def evaluate_condition(condition_id: str, state: NarrativeState, player_message: str = "") -> bool:
    """Evaluate a condition id against the authoritative state; unknown → fail."""
    fn = CONDITION_REGISTRY.get(condition_id)
    if fn is None:
        raise ScriptLoadError("<runtime>", -1, f"unknown condition {condition_id!r}")
    return fn(state, player_message)
