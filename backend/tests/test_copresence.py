"""Co-presence interjection integration (docs/04 §60-62)."""

import json

from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider


class _Provider(LLMProvider):
    """Deterministic per-character provider whose dialogue optionally mentions
    another present character, to exercise the interjection path."""

    def __init__(self, character_id: str, dialogue: str) -> None:
        self.character_id = character_id
        self.dialogue = dialogue
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        return json.dumps(
            {
                "character_id": self.character_id,
                "dialogue": self.dialogue,
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


def _orchestrator(deepseek_dialogue: str, claude_dialogue: str) -> tuple[GameOrchestrator, _Provider, _Provider]:
    deepseek = _Provider("deepseek", deepseek_dialogue)
    claude = _Provider("claude", claude_dialogue)
    orchestrator = GameOrchestrator(
        SessionStore(),
        {
            "deepseek": DeepSeekRuntime(deepseek),
            "claude": ClaudeRuntime(claude),
        },
        default_character="deepseek",
    )
    return orchestrator, deepseek, claude


def _present_both(orchestrator: GameOrchestrator, session_id: str) -> None:
    orchestrator._state.state_for(session_id).chapter1.available_characters.update(
        {"deepseek", "claude"}
    )


def test_interjection_fires_when_primary_mentions_other():
    orchestrator, deepseek, claude = _orchestrator(
        "Claude 一直盯着我看，好可怕", "哼，谁盯着你了"
    )
    session = orchestrator._sessions.get_or_create(None)
    _present_both(orchestrator, session.session_id)

    result = orchestrator.handle_turn(session.session_id, "大家好")

    assert result.response.character_id == "deepseek"
    assert [i.character_id for i in result.interjections] == ["claude"]
    assert result.interjections[0].dialogue == "哼，谁盯着你了"
    # 主回应者与接话者各自被调用了一次
    assert len(deepseek.calls) == 1
    assert len(claude.calls) == 1


def test_interjector_hears_primary_reply():
    """docs/04 §60：接话者必须看到它要接的那句主回应，而非只看到玩家消息。"""
    orchestrator, _, claude = _orchestrator(
        "Claude 一直盯着我看，好可怕", "哼，谁盯着你了"
    )
    session = orchestrator._sessions.get_or_create(None)
    _present_both(orchestrator, session.session_id)

    orchestrator.handle_turn(session.session_id, "大家好")

    assert len(claude.calls) == 1
    user = claude.calls[0]["user"]
    assert "deepseek：Claude 一直盯着我看，好可怕" in user


def test_no_interjection_when_primary_mentions_nobody():
    orchestrator, deepseek, claude = _orchestrator("今天天气不错", "嗯")
    session = orchestrator._sessions.get_or_create(None)
    _present_both(orchestrator, session.session_id)

    result = orchestrator.handle_turn(session.session_id, "你好")

    assert result.response.character_id == "deepseek"
    assert result.interjections == ()
    assert not claude.calls


def test_no_interjection_in_single_character_scene():
    orchestrator, deepseek, claude = _orchestrator("Claude 你在吗", "我在")
    session = orchestrator._sessions.get_or_create(None)
    # 只 deepseek 在场；claude 虽被提到但不在场，不能接话
    orchestrator._state.state_for(session.session_id).chapter1.available_characters.update(
        {"deepseek"}
    )

    result = orchestrator.handle_turn(session.session_id, "你好")

    assert result.interjections == ()
    assert not claude.calls


def test_interjection_is_recorded_in_history():
    orchestrator, _, _ = _orchestrator("Claude 你看", "我看什么")
    session = orchestrator._sessions.get_or_create(None)
    _present_both(orchestrator, session.session_id)

    orchestrator.handle_turn(session.session_id, "大家好")
    messages = orchestrator.get_history(session.session_id)

    assert [m["role"] for m in messages] == ["player", "character", "character"]
    assert [m["character_id"] for m in messages[1:]] == ["deepseek", "claude"]


def test_named_primary_directs_reply_to_named_character():
    """docs/04 §61：玩家点名 → 该角色成为主回应者（不依赖 LLM speaker selector）。"""
    orchestrator, deepseek, claude = _orchestrator("嗯", "哼")
    session = orchestrator._sessions.get_or_create(None)
    _present_both(orchestrator, session.session_id)

    result = orchestrator.handle_turn(session.session_id, "Claude，你怎么看？")

    assert result.response.character_id == "claude"
    assert not deepseek.calls
    assert len(claude.calls) == 1
