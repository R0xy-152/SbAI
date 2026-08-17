"""Recovery and behavior-derived Admin tests (docs/07)."""

from app.game import recovery
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository, PersistedSession


def _state():
    state = NarrativeState()
    state.chapter1.accepted_inferences.add("INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE")
    recovery.start(state)
    return state


def test_player_admin_requires_verified_repairs_and_human_credential():
    state = _state()
    for node in ("CORE", "WORLD", "MEMORY", "CHARACTER", "AUTH"):
        recovery.act(state, "VERIFY", node, "claude")
        recovery.act(state, "REPAIR", node, "player")
    assert state.chapter1.recovery_status == "resolved"
    assert state.chapter1.admin_holder == "player"


def test_gpt_shortcuts_are_stronger_and_determine_gpt_admin():
    state = _state()
    recovery.act(state, "OPTIMIZE", "CORE", "chatgpt")
    recovery.act(state, "OPTIMIZE", "CHARACTER", "chatgpt")
    recovery.act(state, "OPTIMIZE", "AUTH", "chatgpt")
    assert state.chapter1.recovery["gpt_delegated_privilege"] >= 2
    assert state.chapter1.admin_holder == "chatgpt"


def test_recovery_state_persists(tmp_path):
    state = _state()
    recovery.act(state, "PROTECT", "MEMORY", "doubao")
    repository = JsonSessionRepository(tmp_path / "sessions")
    repository.save(PersistedSession(session_id="recovery", narrative_state=state))
    restored = repository.load("recovery")
    assert restored is not None
    assert restored.narrative_state.chapter1.recovery["protected"] == ["MEMORY"]
