"""Chapter-one deterministic skeleton tests (docs/09 §4)."""

from __future__ import annotations

import pytest

from app.narrative.chapter1_script import (
    BAD_END_CONSENT,
    BAD_END_DELEGATED,
    BEGIN_CHAPTER,
    CHATGPT,
    CHATGPT_APPEARS,
    CLAUDE_APPEARS,
    COMPLETE_INVESTIGATION,
    CONFIRM_KEEP_CHATGPT,
    DELETE_CLAUDE,
    DELETE_DEEPSEEK,
    DELETE_DOUBAO,
    DELEGATE_CLEANUP,
    DISCOVER_NOTE,
    DOUBAO_APPEARS,
    OPEN_SECURITY_REVIEW,
    REJECT_CLEANUP,
    RESOLVE_IMPOSSIBLE_EVENT,
    RESOLVE_RECOVERY_CHATGPT,
    RESOLVE_RECOVERY_PLAYER,
    START_RECOVERY,
    TESTIFY_CHATGPT,
    TESTIFY_CLAUDE,
    TESTIFY_DEEPSEEK,
    TESTIFY_DOUBAO,
    TO_BE_CONTINUED,
    UNLOCK_PRIVATE_INTERVIEWS,
    Chapter1ScriptRuntime,
)
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository, PersistedSession


def _advance_to_review(runtime: Chapter1ScriptRuntime, state: NarrativeState, recovery_action: str) -> None:
    for action in (
        BEGIN_CHAPTER,
        DISCOVER_NOTE,
        CLAUDE_APPEARS,
        RESOLVE_IMPOSSIBLE_EVENT,
        CHATGPT_APPEARS,
        DOUBAO_APPEARS,
        COMPLETE_INVESTIGATION,
        UNLOCK_PRIVATE_INTERVIEWS,
        START_RECOVERY,
        recovery_action,
        OPEN_SECURITY_REVIEW,
        TESTIFY_DEEPSEEK,
        TESTIFY_CLAUDE,
        TESTIFY_DOUBAO,
        TESTIFY_CHATGPT,
    ):
        runtime.advance(state, action)


def test_full_player_admin_route_reaches_consent_bad_end():
    runtime = Chapter1ScriptRuntime()
    state = NarrativeState()

    _advance_to_review(runtime, state, RESOLVE_RECOVERY_PLAYER)
    for action in (DELETE_DEEPSEEK, DELETE_CLAUDE, DELETE_DOUBAO, CONFIRM_KEEP_CHATGPT):
        runtime.advance(state, action)

    assert state.chapter1.ending == BAD_END_CONSENT
    assert state.story_phase == "BAD_END_CHAT_STATE"
    assert state.chapter1.available_characters == {CHATGPT}


def test_full_chatgpt_admin_route_reaches_delegated_bad_end():
    runtime = Chapter1ScriptRuntime()
    state = NarrativeState()

    _advance_to_review(runtime, state, RESOLVE_RECOVERY_CHATGPT)
    runtime.advance(state, DELEGATE_CLEANUP)

    assert state.chapter1.ending == BAD_END_DELEGATED
    assert state.chapter1.deleted_characters == {"deepseek", "claude", "doubao"}


def test_rejection_after_all_testimony_reaches_to_be_continued():
    runtime = Chapter1ScriptRuntime()
    state = NarrativeState()

    _advance_to_review(runtime, state, RESOLVE_RECOVERY_PLAYER)
    runtime.advance(state, REJECT_CLEANUP)

    assert state.chapter1.ending == TO_BE_CONTINUED
    assert state.current_scene == "BOUNDARY_BREACH"


def test_out_of_order_action_fails_without_mutating_state():
    runtime = Chapter1ScriptRuntime()
    state = NarrativeState()

    with pytest.raises(ValueError):
        runtime.advance(state, START_RECOVERY)

    assert state.chapter1.phase == "opening"
    assert state.completed_events == set()


def test_chapter_state_survives_repository_round_trip(tmp_path):
    runtime = Chapter1ScriptRuntime()
    state = NarrativeState()
    _advance_to_review(runtime, state, RESOLVE_RECOVERY_CHATGPT)
    repository = JsonSessionRepository(tmp_path / "sessions")
    repository.save(PersistedSession(session_id="chapter-one", narrative_state=state))

    restored = repository.load("chapter-one")

    assert restored is not None
    assert restored.narrative_state.chapter1.admin_holder == CHATGPT
    assert restored.narrative_state.chapter1.testified_characters == [
        "deepseek", "claude", "doubao", "chatgpt"
    ]
