import json

from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.speaker_selector import SpeakerSelector
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider


class _Provider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        return json.dumps({"character_id": "claude"})


def test_selector_accepts_only_present_character():
    assert SpeakerSelector(_Provider()).choose("问 Claude", {"deepseek", "claude"}) == "claude"


def test_public_player_messages_are_audible_to_each_character():
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": object()}, default_character="deepseek")
    heard = orchestrator._heard_messages(
        [
            {
                "role": "player",
                "character_id": "deepseek",
                "heard_by": ["deepseek", "claude"],
                "content": "大家听我说",
            },
            {"role": "character", "character_id": "claude", "content": "…"},
        ],
        "claude",
    )
    assert [item["role"] for item in heard] == ["player", "character"]


def test_character_who_appears_later_does_not_hear_old_public_message():
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": object()}, default_character="deepseek")
    heard = orchestrator._heard_messages(
        [
            {
                "role": "player",
                "character_id": "deepseek",
                "heard_by": ["deepseek"],
                "content": "Claude出现前说的话",
            }
        ],
        "claude",
    )
    assert heard == []


def test_orchestrator_uses_validated_model_speaker_proposal():
    deepseek_provider = _Provider()
    claude_provider = _Provider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {
            "deepseek": DeepSeekRuntime(deepseek_provider),
            "claude": ClaudeRuntime(claude_provider),
        },
        speaker_selector=SpeakerSelector(_Provider()),
    )
    session = sessions.get_or_create(None)
    orchestrator._state.state_for(session.session_id).chapter1.available_characters.update(
        {"deepseek", "claude"}
    )

    result = orchestrator.handle_turn(session.session_id, "Claude，你怎么看？")

    assert result.response.character_id == "claude"
    assert claude_provider.calls
    assert not deepseek_provider.calls
