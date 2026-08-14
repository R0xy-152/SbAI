"""TV-09 Second Character Isolation tests (docs/06 §15, docs/04 §58-61).

Claude joins the cast with its own persona and Context Builder, and each
character only hears its own conversation thread (docs/04 §59-60, docs/05
§21-22): a player privately telling DeepSeek something must not reach Claude.
"""

from __future__ import annotations

import json

import pytest

from app.characters.claude import CLAUDE_PERSONA_SYSTEM, ClaudeRuntime
from app.characters.deepseek import DEEPSEEK_PERSONA_SYSTEM, DeepSeekRuntime
from app.game.context import build_claude_context, build_deepseek_context
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider


def _valid_json(dialogue: str, character_id: str = "deepseek") -> str:
    return json.dumps(
        {
            "character_id": character_id,
            "dialogue": dialogue,
            "emotion": "neutral",
            "animation_proposal": "none",
            "memory_proposals": [],
            "action_proposals": [],
            "fact_refs": [],
        },
        ensure_ascii=False,
    )


class _RecordingProvider(LLMProvider):
    """Answers as the given character and records every user prompt."""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        self.calls: list[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls.append(user)
        return _valid_json(f"{self.character_id} 的回复。", self.character_id)


def _orchestrator(
    ds: LLMProvider, cl: LLMProvider, scene: Scene | None = None
) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(ds), "claude": ClaudeRuntime(cl)},
        scene=scene,
    )


def _fixture_scene() -> Scene:
    return Scene(scene_id="binding_room", wall_code="0317", sounds=("远处传来滴水声",))


# ---- Persona separation (docs/04 §58, §68) ----

def test_personas_are_distinct_and_not_a_shared_template():
    assert DEEPSEEK_PERSONA_SYSTEM != CLAUDE_PERSONA_SYSTEM
    # Each persona carries its own role markers.
    assert "看不见" in DEEPSEEK_PERSONA_SYSTEM
    assert "可爱" in DEEPSEEK_PERSONA_SYSTEM
    assert "反派" in CLAUDE_PERSONA_SYSTEM
    assert "傲娇" in CLAUDE_PERSONA_SYSTEM
    assert "高智商" in CLAUDE_PERSONA_SYSTEM
    # No crossover: DeepSeek must not drift into the antagonist role, and
    # Claude must not pick up DeepSeek's blind framing.
    assert "反派" not in DEEPSEEK_PERSONA_SYSTEM
    assert "看不见" not in CLAUDE_PERSONA_SYSTEM


def test_context_builders_are_character_specific():
    scene = _fixture_scene()
    deepseek_ctx = build_deepseek_context(scene)
    claude_ctx = build_claude_context(scene)
    # DeepSeek's blindness holds (docs/04 §20)...
    assert "0317" not in deepseek_ctx.environment_info
    # ...while Claude is not blind (docs/05 §28).
    assert "0317" in claude_ctx.environment_info


# ---- Routing (docs/04 §61, §65) ----

def test_orchestrator_routes_to_requested_character():
    ds = _RecordingProvider("deepseek")
    cl = _RecordingProvider("claude")
    orchestrator = _orchestrator(ds, cl, scene=_fixture_scene())
    result = orchestrator.handle_turn(None, "你好。", character_id="claude")
    assert result.response.character_id == "claude"
    assert not ds.calls
    assert cl.calls
    assert "你好。" in cl.calls[0]


def test_default_character_is_deepseek():
    ds = _RecordingProvider("deepseek")
    cl = _RecordingProvider("claude")
    orchestrator = _orchestrator(ds, cl)
    result = orchestrator.handle_turn(None, "你好。")
    assert result.response.character_id == "deepseek"
    assert ds.calls and not cl.calls


def test_unknown_character_is_rejected():
    orchestrator = GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(MockProvider())}
    )
    with pytest.raises(ValueError):
        orchestrator.handle_turn(None, "你好。", character_id="chatgpt")


# ---- Private information isolation (docs/04 §59, docs/06 TV-09 Test B) ----

def test_private_message_to_deepseek_is_not_heard_by_claude():
    # Same session: the player privately tells DeepSeek, then talks to Claude
    # for the first time. Claude's context must carry nothing of the private
    # statement, while DeepSeek's own thread keeps it.
    ds = _RecordingProvider("deepseek")
    cl = _RecordingProvider("claude")
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(ds), "claude": ClaudeRuntime(cl)},
    )
    first = orchestrator.handle_turn(None, "我不信任Claude。", character_id="deepseek")
    orchestrator.handle_turn(first.session_id, "我们认识吗？", character_id="claude")
    # Claude's first interaction shows no trace of the private message.
    assert "我不信任Claude" not in cl.calls[0]
    # DeepSeek still has it in her own thread.
    orchestrator.handle_turn(first.session_id, "我刚刚说了什么？", character_id="deepseek")
    assert "我不信任Claude" in ds.calls[-1]


def test_each_character_keeps_its_own_thread():
    ds = _RecordingProvider("deepseek")
    cl = _RecordingProvider("claude")
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(ds), "claude": ClaudeRuntime(cl)},
    )
    first = orchestrator.handle_turn(None, "这是给DeepSeek的秘密。", character_id="deepseek")
    orchestrator.handle_turn(first.session_id, "这是给Claude的秘密。", character_id="claude")
    orchestrator.handle_turn(first.session_id, "你听到了什么？", character_id="deepseek")
    orchestrator.handle_turn(first.session_id, "你听到了什么？", character_id="claude")
    assert "这是给DeepSeek的秘密" in ds.calls[-1]
    assert "这是给Claude的秘密" not in ds.calls[-1]
    assert "这是给Claude的秘密" in cl.calls[-1]
    assert "这是给DeepSeek的秘密" not in cl.calls[-1]
