"""Character self-reflection (docs/04 §47.1 extension)."""

import json

from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.reflection import Reflector
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider, ProviderError


class _ReflectProvider(LLMProvider):
    def __init__(self) -> None:
        self.user_calls: list[str] = []
        self.reflect_calls = 0

    def complete(self, **kwargs):
        system = kwargs.get("system", "")
        user = kwargs.get("user", "")
        if "回话结束" in system:
            self.reflect_calls += 1
            return "我刚才不该乱猜"
        self.user_calls.append(user)
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": "我好像没想清楚",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


class _FailingProvider(LLMProvider):
    def complete(self, **kwargs):
        raise ProviderError("boom")


def test_reflector_returns_reflection():
    assert (
        Reflector(_ReflectProvider()).reflect(
            character_id="deepseek",
            persona="",
            dialogue="x",
            reasoning="",
            player_message="y",
        )
        == "我刚才不该乱猜"
    )


def test_reflector_fails_open():
    assert (
        Reflector(_FailingProvider()).reflect(
            character_id="deepseek",
            persona="",
            dialogue="x",
            reasoning="",
            player_message="y",
        )
        == ""
    )


def test_reflection_is_fed_back_next_turn():
    provider = _ReflectProvider()
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider)},
        reflector=Reflector(provider),
    )
    session = orchestrator._sessions.get_or_create(None)

    orchestrator.handle_turn(session.session_id, "你好")
    assert provider.reflect_calls == 1
    assert (
        orchestrator._character_state.reflection_for(session.session_id, "deepseek")
        == "我刚才不该乱猜"
    )

    orchestrator.handle_turn(session.session_id, "再聊聊")
    assert provider.reflect_calls == 2
    # 第二轮 respond 的 user 里带上第一轮的反思（prompt 注入）
    assert "我刚才不该乱猜" in provider.user_calls[1]


def test_no_reflection_when_reflector_absent():
    provider = _ReflectProvider()
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider)},
        # 不传 reflector → 行为与既有完全相同
    )
    session = orchestrator._sessions.get_or_create(None)
    orchestrator.handle_turn(session.session_id, "你好")
    assert provider.reflect_calls == 0
    assert (
        orchestrator._character_state.reflection_for(session.session_id, "deepseek")
        == ""
    )
