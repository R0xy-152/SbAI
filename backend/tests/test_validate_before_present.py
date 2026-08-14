"""TV-06 Validate Before Present tests (docs/06 §12, docs/04 §51-54).

Deliberately fabricate invalid generated results and prove that none of them
enter official History, affect Game State, or reach the player: they are
repaired or replaced by the safe fallback instead.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider

FALLBACK = "……等一下，我脑子有点卡住了。"


class _FixedProvider(LLMProvider):
    """Returns the same text on every call (so repair also fails)."""

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        return self._text


def _structured_output(
    dialogue: str = "我是被关在这里的人。",
    character_id: str = "deepseek",
    emotion: str = "neutral",
    animation: str = "none",
) -> str:
    return json.dumps(
        {
            "character_id": character_id,
            "dialogue": dialogue,
            "emotion": emotion,
            "animation_proposal": animation,
            "memory_proposals": [],
            "action_proposals": [],
            "fact_refs": [],
        },
        ensure_ascii=False,
    )


def _app_with(provider: LLMProvider) -> tuple[object, SessionStore]:
    sessions = SessionStore()
    app = create_app()
    app.state.orchestrator = GameOrchestrator(
        sessions, {"deepseek": DeepSeekRuntime(provider)}
    )
    return app, sessions


def _post(app, message: str = "你好"):
    with TestClient(app) as client:
        return client.post("/api/chat", json={"message": message})


def _character_messages(sessions: SessionStore, session_id: str) -> list[dict]:
    session = sessions.get_or_create(session_id)
    return [m for m in session.messages if m["role"] == "character"]


def test_wrong_character_id_is_repaired_to_fallback_and_never_presented():
    # The model claims to be another character and answers about facts it must
    # not know — Character Validation must reject it.
    leaked = "我看见墙上写着密码 0427。"
    app, sessions = _app_with(
        _FixedProvider(_structured_output(dialogue=leaked, character_id="claude"))
    )
    response = _post(app)
    assert response.status_code == 200
    body = response.json()
    assert body["character_id"] == "deepseek"
    assert body["dialogue"] == FALLBACK  # safe reply, not the leaked line

    history = sessions.get_or_create(body["session_id"]).messages
    character_messages = [m for m in history if m["role"] == "character"]
    assert len(character_messages) == 1
    assert character_messages[0]["character_id"] == "deepseek"
    assert character_messages[0]["content"] == FALLBACK
    # The invalid content is nowhere in official History.
    assert all("0427" not in str(message) for message in history)


def test_invalid_animation_is_repaired_to_fallback_and_never_presented():
    app, sessions = _app_with(_FixedProvider(_structured_output(animation="spin")))
    response = _post(app)
    assert response.status_code == 200
    body = response.json()
    assert body["dialogue"] == FALLBACK
    character_messages = _character_messages(sessions, body["session_id"])
    assert len(character_messages) == 1
    assert character_messages[0]["content"] == FALLBACK


def test_malformed_output_never_enters_history():
    app, sessions = _app_with(MockProvider(malformed=True))
    response = _post(app)
    body = response.json()
    assert body["dialogue"] == FALLBACK
    history = sessions.get_or_create(body["session_id"]).messages
    # The raw (invalid) model text is not in History; the fallback is.
    assert all("没听清" not in str(message) for message in history)
    character_messages = [m for m in history if m["role"] == "character"]
    assert len(character_messages) == 1
    assert character_messages[0]["content"] == FALLBACK


def test_game_state_is_unchanged_by_invalid_output():
    # An invalid turn counts exactly one player turn and one safe reply —
    # nothing extra is committed to state.
    app, sessions = _app_with(MockProvider(malformed=True))
    body = _post(app).json()
    assert body["message_count"] == 1
    history = sessions.get_or_create(body["session_id"]).messages
    roles = [message["role"] for message in history]
    assert roles == ["player", "character"]


def test_valid_output_enters_history_as_approved_content():
    app, sessions = _app_with(
        _FixedProvider(_structured_output(dialogue="这里好黑呀，我看不见。"))
    )
    response = _post(app)
    body = response.json()
    assert body["dialogue"] == "这里好黑呀，我看不见。"  # real reply, not fallback
    character_messages = _character_messages(sessions, body["session_id"])
    assert len(character_messages) == 1
    assert character_messages[0]["content"] == "这里好黑呀，我看不见。"
