"""Chapter-one inquiry interpreter tests (docs/03)."""

from __future__ import annotations

import json

from app.narrative.inquiry import (
    ASK_CHARACTER_KNOWLEDGE,
    ASK_OBSERVATION_SOURCE,
    NOOP,
    Chapter1InquiryInterpreter,
)
from app.narrative.state import NarrativeState
from app.providers.mock import MockProvider
from app.providers.base import LLMProvider


class _FixedProvider(LLMProvider):
    def __init__(self, response: dict) -> None:
        self._response = response
        self.system = ""
        self.user = ""

    def complete(self, *, system, user, max_tokens=256, response_format=None, thinking=None):
        self.system = system
        self.user = user
        return json.dumps(self._response)


def _state() -> NarrativeState:
    state = NarrativeState()
    state.chapter1.available_characters.update({"deepseek", "claude"})
    state.chapter1.acquired_evidence.add("EV_NOTE_V03")
    return state


def test_equivalent_observation_questions_share_one_bounded_inquiry():
    output = {
        "intent": ASK_OBSERVATION_SOURCE,
        "target": "claude",
        "subject": "deepseek",
        "topic": "door_open",
    }
    first = Chapter1InquiryInterpreter(_FixedProvider(output)).interpret(
        _state(), "你亲眼看见 DeepSeek 开门了吗？"
    )
    second = Chapter1InquiryInterpreter(_FixedProvider(output)).interpret(
        _state(), "你说门是她开的，消息来源是什么？"
    )
    assert first == second
    assert first.intent == ASK_OBSERVATION_SOURCE


def test_prompt_exposes_only_player_known_scope_and_interpreter_never_mutates_state():
    state = _state()
    provider = _FixedProvider({"intent": "noop"})
    result = Chapter1InquiryInterpreter(provider).interpret(state, "03:17 时发生了什么？")

    assert result.intent == NOOP
    assert provider.user == "03:17 时发生了什么？"
    assert "EV_NOTE_V03" in provider.system
    assert "ADMIN_ACTOR_CORRUPTED" not in provider.system
    assert "CURRENT_SUBJECT_IS_PLAYER_V04" not in provider.system
    assert state.chapter1.acquired_evidence == {"EV_NOTE_V03"}
    assert state.completed_events == set()


def test_mock_provider_uses_only_the_authored_claude_question_fallbacks():
    state = _state()

    attribution = Chapter1InquiryInterpreter(MockProvider()).interpret(
        state, "C-02 的门是谁打开的？"
    )
    source = Chapter1InquiryInterpreter(MockProvider()).interpret(
        state, "你亲眼看见 DeepSeek 开门了吗？"
    )

    assert attribution.intent == ASK_CHARACTER_KNOWLEDGE
    assert attribution.topic == "door_open"
    assert source.intent == ASK_OBSERVATION_SOURCE


def test_unavailable_characters_and_unknown_topics_fail_closed():
    unavailable = Chapter1InquiryInterpreter(
        _FixedProvider({"intent": ASK_OBSERVATION_SOURCE, "target": "chatgpt"})
    ).interpret(_state(), "问问 ChatGPT")
    unknown_topic = Chapter1InquiryInterpreter(
        _FixedProvider({"intent": ASK_OBSERVATION_SOURCE, "target": "claude", "topic": "reset"})
    ).interpret(_state(), "你看见重置了吗？")

    assert unavailable.intent == NOOP
    assert unknown_topic.intent == NOOP
