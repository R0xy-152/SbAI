"""Authored availability progression for docs/11 checkpoints."""

from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="已整理当前线索。")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


def test_doubao_appears_only_after_player_uses_gpt_first_summary():
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"chatgpt": _Runtime("chatgpt"), "doubao": _Runtime("doubao")},
        default_character="chatgpt",
    )
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.chapter1.available_characters.add("chatgpt")

    result = orchestrator.handle_turn(session_id, "请整理目前线索。", character_id="chatgpt")

    assert result.presentation == ("SHOW_CHARACTER doubao",)
    assert "doubao" in state.chapter1.available_characters
    assert "doubao_has_appeared" in state.narrative_flags
