"""Final self-proof order and persistence (docs/08)."""

import pytest

from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository


class _Runtime:
    character_id = "deepseek"
    def respond(self, request): raise AssertionError
    def safe_fallback(self): raise AssertionError


def _ready(orchestrator):
    session = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session)
    state.chapter1.recovery_status = "resolved"
    state.chapter1.admin_holder = "player"
    return session


def test_self_proofs_are_ordered_and_persisted(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": _Runtime()}, repository=repo)
    session = _ready(orchestrator)
    assert orchestrator.start_security_review(session)["status"] == "OPEN"
    for character in ("deepseek", "claude", "doubao", "chatgpt"):
        result = orchestrator.testify(session, character)
        assert result["character_id"] == character
    assert repo.load(session).narrative_state.chapter1.testified_characters == ["deepseek", "claude", "doubao", "chatgpt"]


def test_out_of_order_self_proof_is_rejected():
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": _Runtime()})
    session = _ready(orchestrator)
    orchestrator.start_security_review(session)
    with pytest.raises(ValueError):
        orchestrator.testify(session, "chatgpt")
