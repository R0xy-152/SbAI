"""GPT second summary gate (docs/11 Phase G)."""

from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore


class _ClaudeRuntime:
    character_id = "claude"

    def respond(self, request):
        return CharacterResponse(character_id="claude", dialogue="我访问过 Recovery Interface。", claim_refs=["CL_CLAUDE_05"])

    def safe_fallback(self):
        return CharacterResponse(character_id="claude", dialogue="……")


def test_second_gpt_summary_requires_all_three_investigation_outputs():
    orchestrator = GameOrchestrator(SessionStore(), {"claude": _ClaudeRuntime()}, default_character="claude")
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.narrative_flags.add("claude_recovery_disclosure_open")
    state.chapter1.acquired_evidence.update({"EV06_SESSION_REPLAY_MARKER", "EV08_GPT_RECOVERY_SERVICE"})

    orchestrator.handle_turn(session_id, "你访问过 Recovery Interface 吗？", character_id="claude")

    assert "EV07_CLAUDE_RECOVERY_ACCESS" in state.chapter1.acquired_evidence
    assert "EV11_GPT_SECOND_SUMMARY" in state.chapter1.acquired_evidence
