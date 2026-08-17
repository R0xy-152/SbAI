"""Non-Bad-End chapter closure (docs/08 §13)."""

from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository

class _Runtime:
    character_id = "deepseek"
    def respond(self, request): raise AssertionError
    def safe_fallback(self): raise AssertionError

def test_reject_cleanup_enters_boundary_breach_and_persists(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    orch = GameOrchestrator(SessionStore(), {"deepseek": _Runtime()}, repository=repo)
    session = orch._sessions.get_or_create(None).session_id
    state = orch._state.state_for(session)
    state.chapter1.phase = "security_review"
    state.chapter1.security_review_open = True
    state.chapter1.testified_characters = ["deepseek", "claude", "doubao", "chatgpt"]
    result = orch.reject_cleanup(session)
    assert result == {"phase": "to_be_continued", "ending": "to_be_continued", "scene_id": "BOUNDARY_BREACH"}
    assert repo.load(session).narrative_state.chapter1.ending == "to_be_continued"
