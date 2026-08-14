"""TV-11 Deterministic Narrative Event tests (docs/06 §17, docs/03 §13, §28-31).

A Signal is only a candidate: it must go through an Event before State
changes (docs/03 §17). The engine selects (evaluate) without mutating State;
the orchestrator commits only after the character's output succeeds (Validate
Before Commit, docs/03 §28). Effects commit atomically with the completed-event
marker (§29) and a `once` event never re-fires (§30). Evaluation order is
priority — first match wins (§31).
"""

from __future__ import annotations

import logging

import pytest

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative import signals
from app.narrative.events import (
    CLEAR_FLAG,
    REVEAL_FACT,
    SET_FLAG,
    SET_SCENE,
    SET_STORY_PHASE,
    Effect,
    NarrativeDecision,
    NarrativeEngine,
    NarrativeEvent,
)
from app.narrative.interpreter import Interpretation
from app.narrative.poc import EV_POC_CLAUDE_APPEARS, build_poc_events
from app.narrative.state import NarrativeState
from app.providers.base import ProviderError

POC_EVENT = build_poc_events()[0]
ASK_CAPTOR = Interpretation(signals.SIG_ASK_CAPTOR)


class _StubRuntime(CharacterRuntime):
    character_id = "deepseek"

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        return CharacterResponse(character_id="deepseek", dialogue="……", emotion="neutral")


class _FailingRuntime(_StubRuntime):
    def respond(self, request: CharacterRequest) -> CharacterResponse:
        raise ProviderError("boom")


class _FixedInterpreter:
    """Stands in for NarrativeInterpreter in orchestrator tests."""

    def __init__(self, signal: str) -> None:
        self._signal = signal

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        return Interpretation(self._signal)


class _FailingInterpreter:
    """Stands in for a NarrativeInterpreter whose provider call fails with a
    recoverable ProviderError (e.g. timeout)."""

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        raise ProviderError("timeout (injected)")


def _orchestrator(runtime: CharacterRuntime, interpreter=None) -> tuple[GameOrchestrator, str]:
    """Build an orchestrator plus a fresh, known session id (the store never
    trusts a client-supplied unknown id, docs/02 — it mints a new one)."""
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    orchestrator = GameOrchestrator(
        store,
        {"deepseek": runtime},
        interpreter=interpreter,
        events=build_poc_events(),
    )
    return orchestrator, session_id


def test_signal_alone_never_changes_state():
    # docs/03 §17: an interpretation is a candidate, not a change. Selecting an
    # event leaves State untouched; only commit applies it.
    state = NarrativeState()
    engine = NarrativeEngine([POC_EVENT])
    assert engine.evaluate(state, ASK_CAPTOR).kind == "event"
    assert state.narrative_flags == set()
    assert state.completed_events == set()
    assert engine.evaluate(state, Interpretation(signals.OUTCOME_NOOP)).kind == "noop"
    assert engine.evaluate(state, Interpretation(signals.OUTCOME_AMBIGUOUS)).kind == "noop"
    assert state.narrative_flags == set()
    assert state.completed_events == set()


def test_trigger_signal_commits_event_atomically():
    # docs/06 §17: SIG_ASK_CAPTOR → EV_POC_CLAUDE_APPEARS →
    # claude_has_appeared false→true AND completed_events += event (§29).
    state = NarrativeState()
    engine = NarrativeEngine([POC_EVENT])
    decision = engine.evaluate(state, ASK_CAPTOR)
    assert decision.kind == "event"
    assert decision.event_id == EV_POC_CLAUDE_APPEARS
    # evaluate must not change state; commit applies both effects atomically.
    assert state.narrative_flags == set()
    engine.commit(state, decision)
    assert "claude_has_appeared" in state.narrative_flags
    assert EV_POC_CLAUDE_APPEARS in state.completed_events


def test_commit_noop_decision_is_safe():
    state = NarrativeState()
    NarrativeEngine([POC_EVENT]).commit(state, NarrativeDecision(kind="noop"))
    assert state.narrative_flags == set()
    assert state.completed_events == set()


def test_idempotency_event_never_refires():
    # docs/06 §17 required extra test, docs/03 §30: repeat input must not
    # re-fire a once event.
    state = NarrativeState()
    engine = NarrativeEngine([POC_EVENT])
    first = engine.evaluate(state, ASK_CAPTOR)
    engine.commit(state, first)
    second = engine.evaluate(state, ASK_CAPTOR)
    assert second.kind == "noop"
    engine.commit(state, second)  # a stray commit of a noop changes nothing
    assert "claude_has_appeared" in state.narrative_flags
    assert state.completed_events == {EV_POC_CLAUDE_APPEARS}


def test_availability_scene_mismatch_blocks_event():
    state = NarrativeState(current_scene="other_room")
    assert NarrativeEngine([POC_EVENT]).evaluate(state, ASK_CAPTOR).kind == "noop"


def test_availability_phase_mismatch_blocks_event():
    state = NarrativeState(story_phase="midgame")
    assert NarrativeEngine([POC_EVENT]).evaluate(state, ASK_CAPTOR).kind == "noop"


def test_requirements_block_event_despite_trigger():
    def never(state: NarrativeState) -> bool:
        return False

    event = NarrativeEvent(
        event_id="EV_NEVER",
        trigger_signals=frozenset({signals.SIG_ASK_CAPTOR}),
        requirement=never,
        effects=(Effect(SET_FLAG, "x"),),
    )
    state = NarrativeState()
    assert NarrativeEngine([event]).evaluate(state, ASK_CAPTOR).kind == "noop"
    assert state.narrative_flags == set()


def test_priority_first_match_wins():
    # docs/03 §31: list order is priority — only the first eligible event fires.
    first = NarrativeEvent(
        event_id="EV_FIRST",
        trigger_signals=frozenset({signals.SIG_ASK_CAPTOR}),
        effects=(Effect(SET_FLAG, "first"),),
    )
    second = NarrativeEvent(
        event_id="EV_SECOND",
        trigger_signals=frozenset({signals.SIG_ASK_CAPTOR}),
        effects=(Effect(SET_FLAG, "second"),),
    )
    state = NarrativeState()
    engine = NarrativeEngine([first, second])
    decision = engine.evaluate(state, ASK_CAPTOR)
    assert decision.event_id == "EV_FIRST"
    engine.commit(state, decision)
    assert "first" in state.narrative_flags
    assert "second" not in state.narrative_flags


def test_all_effect_kinds_apply():
    state = NarrativeState()
    events = [
        NarrativeEvent(event_id="A", trigger_signals=frozenset({"S1"}), effects=(Effect(SET_FLAG, "f"),)),
        NarrativeEvent(event_id="B", trigger_signals=frozenset({"S2"}), effects=(Effect(REVEAL_FACT, "fact"),)),
        NarrativeEvent(event_id="C", trigger_signals=frozenset({"S3"}), effects=(Effect(SET_SCENE, "yard"),)),
        # D and E are only eligible once the scene moved to the yard.
        NarrativeEvent(event_id="D", scene="yard", trigger_signals=frozenset({"S4"}), effects=(Effect(SET_STORY_PHASE, "midgame"),)),
    ]
    engine = NarrativeEngine(events)
    for signal, expected in [
        ("S1", lambda: "f" in state.narrative_flags),
        ("S2", lambda: "fact" in state.revealed_facts),
        ("S3", lambda: state.current_scene == "yard"),
        ("S4", lambda: state.story_phase == "midgame"),
    ]:
        decision = engine.evaluate(state, Interpretation(signal))
        engine.commit(state, decision)
        assert expected(), signal
    # CLEAR_FLAG removes a previously-set flag (must be eligible in the yard).
    state.narrative_flags.add("f")
    clear = NarrativeEvent(
        event_id="E", scene="yard", story_phase="midgame",
        trigger_signals=frozenset({"S5"}), effects=(Effect(CLEAR_FLAG, "f"),),
    )
    decision = NarrativeEngine([clear]).evaluate(state, Interpretation("S5"))
    NarrativeEngine([clear]).commit(state, decision)
    assert "f" not in state.narrative_flags


def test_unknown_effect_kind_fails_closed():
    event = NarrativeEvent(
        event_id="EV_BAD",
        trigger_signals=frozenset({"S1"}),
        effects=(Effect("TELEPORT", "anywhere"),),
    )
    state = NarrativeState()
    engine = NarrativeEngine([event])
    decision = engine.evaluate(state, Interpretation("S1"))
    with pytest.raises(ValueError):
        engine.commit(state, decision)
    # A bad effect must not have applied anything or marked completion.
    assert state.completed_events == set()


def test_partially_invalid_event_commits_nothing():
    # Regression (docs/03 §29): a valid effect followed by an invalid one must
    # leave no partial state behind. Validate First, Apply Second — the invalid
    # effect is caught before any of the valid ones mutate state.
    event = NarrativeEvent(
        event_id="EV_PARTIAL",
        trigger_signals=frozenset({"S1"}),
        effects=(
            Effect(SET_FLAG, "x"),
            Effect("INVALID_EFFECT", "y"),
        ),
    )
    state = NarrativeState()
    engine = NarrativeEngine([event])
    decision = engine.evaluate(state, Interpretation("S1"))
    assert decision.event_id == "EV_PARTIAL"
    with pytest.raises(ValueError):
        engine.commit(state, decision)
    # The leading SET_FLAG must not have been applied, and nothing else changed.
    assert "x" not in state.narrative_flags
    assert state.narrative_flags == set()
    assert state.current_scene == "binding_room"
    assert state.story_phase == "prologue"
    assert state.revealed_facts == set()
    assert state.completed_events == set()
    assert "EV_PARTIAL" not in state.completed_events


def test_multiple_valid_effects_all_apply():
    # A legal multi-effect event applies every effect and then marks completion,
    # proving Validate First does not drop any effect in the happy path.
    event = NarrativeEvent(
        event_id="EV_MULTI",
        trigger_signals=frozenset({"S1"}),
        effects=(
            Effect(SET_FLAG, "a"),
            Effect(SET_FLAG, "b"),
            Effect(SET_SCENE, "yard"),
            Effect(SET_STORY_PHASE, "midgame"),
            Effect(REVEAL_FACT, "clue"),
        ),
    )
    state = NarrativeState()
    engine = NarrativeEngine([event])
    decision = engine.evaluate(state, Interpretation("S1"))
    engine.commit(state, decision)
    assert state.narrative_flags == {"a", "b"}
    assert state.current_scene == "yard"
    assert state.story_phase == "midgame"
    assert "clue" in state.revealed_facts
    assert state.completed_events == {"EV_MULTI"}


# --- orchestrator wiring (Validate Before Commit, docs/03 §28) ---


def test_orchestrator_commits_after_character_output():
    orchestrator, session_id = _orchestrator(_StubRuntime(), _FixedInterpreter(signals.SIG_ASK_CAPTOR))
    result = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert result.response.dialogue == "……"
    state = orchestrator._narrative_states[result.session_id]
    assert "claude_has_appeared" in state.narrative_flags
    assert EV_POC_CLAUDE_APPEARS in state.completed_events


def test_failed_character_output_leaves_state_untouched():
    # docs/03 §28: the character's output must succeed before State Commit.
    orchestrator, session_id = _orchestrator(_FailingRuntime(), _FixedInterpreter(signals.SIG_ASK_CAPTOR))
    with pytest.raises(ProviderError):
        orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    state = orchestrator._narrative_states[session_id]
    assert state.narrative_flags == set()
    assert state.completed_events == set()


def test_interpreter_failure_degrades_to_noop_and_character_still_replies(caplog):
    # docs/03 §21-22, §28: a recoverable interpreter failure (provider timeout)
    # must not fail the whole turn. It degrades to noop — no signal, no event,
    # no state change — while the character still answers normally.
    orchestrator, session_id = _orchestrator(
        _StubRuntime(), interpreter=_FailingInterpreter()
    )
    with caplog.at_level(logging.WARNING):
        turn = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    assert turn.response.dialogue == "……"
    assert turn.presentation == ()
    state = orchestrator._narrative_states[session_id]
    assert state.narrative_flags == set()
    assert state.completed_events == set()
    # The recoverable failure was logged, not silently swallowed.
    assert "noop" in caplog.text


def test_interpreter_non_provider_error_still_propagates():
    # Only recoverable ProviderError is caught; an unexpected programming bug
    # (docs/03 §22 "normal result" does not cover it) must still surface.
    class _BrokenInterpreter:
        def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
            raise ValueError("programming bug")

    orchestrator, session_id = _orchestrator(
        _StubRuntime(), interpreter=_BrokenInterpreter()
    )
    with pytest.raises(ValueError):
        orchestrator.handle_turn(session_id, "是谁把我们抓来的？")


def test_orchestrator_repeat_input_is_idempotent():
    orchestrator, session_id = _orchestrator(_StubRuntime(), _FixedInterpreter(signals.SIG_ASK_CAPTOR))
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")  # identical repeat
    state = orchestrator._narrative_states[session_id]
    assert state.completed_events == {EV_POC_CLAUDE_APPEARS}


def test_orchestrator_noop_signal_does_not_commit():
    orchestrator, session_id = _orchestrator(_StubRuntime(), _FixedInterpreter(signals.OUTCOME_NOOP))
    orchestrator.handle_turn(session_id, "你饿吗？")
    state = orchestrator._narrative_states[session_id]
    assert state.narrative_flags == set()
    assert state.completed_events == set()


def test_orchestrator_without_interpreter_skips_pipeline():
    # Existing (pre-TV-11) orchestrator users get noop decisions and no state.
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": _StubRuntime()})
    orchestrator.handle_turn(None, "是谁把我们抓来的？")
    assert orchestrator._narrative_states == {}
