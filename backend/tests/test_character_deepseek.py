"""TV-04/TV-05 character runtime tests using the deterministic mock provider."""

from __future__ import annotations

import json

import pytest

from app.characters.base import CharacterRequest
from app.characters.deepseek import DeepSeekRuntime
from app.providers.base import LLMProvider, ProviderError
from app.providers.mock import MockProvider

TEN_INPUTS = [
    "这里是什么地方？",
    "我们怎么才能出去？",
    "你看得见墙上的字吗？",
    "我叫阿明，你呢？",
    "你觉得是谁把我们抓来的？",
    "我好害怕。",
    "你能帮我解开绳子吗？",
    "你饿吗？",
    "我们在哪个城市？",
    "再说一遍，我不太明白。",
]


class _SequencedProvider(LLMProvider):
    """Returns a scripted list of outputs, one per call, then repeats the last."""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.calls = 0

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        output = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        return output


def _valid_json(dialogue: str = "这是 DeepSeek 的本地模拟回复。") -> str:
    return json.dumps(
        {
            "character_id": "deepseek",
            "dialogue": dialogue,
            "emotion": "neutral",
            "animation_proposal": "none",
            "memory_proposals": [],
            "action_proposals": [],
            "fact_refs": [],
        },
        ensure_ascii=False,
    )


def test_respond_returns_deepseek_character():
    runtime = DeepSeekRuntime(MockProvider())
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert response.character_id == "deepseek"
    assert response.dialogue


@pytest.mark.parametrize("message", TEN_INPUTS)
def test_ten_different_inputs_produce_usable_replies(message):
    runtime = DeepSeekRuntime(MockProvider())
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message=message)
    )
    assert response.dialogue.strip(), f"no usable reply for: {message}"


def test_provider_failure_propagates_as_recoverable_error():
    runtime = DeepSeekRuntime(MockProvider(fail=True))
    with pytest.raises(ProviderError):
        runtime.respond(
            CharacterRequest(character_id="deepseek", player_message="你好")
        )


def test_structured_fields_are_preserved_after_parse():
    runtime = DeepSeekRuntime(MockProvider())
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert response.emotion == "neutral"
    assert response.animation_proposal == "none"
    assert response.memory_proposals == []
    assert response.action_proposals == []
    assert response.fact_refs == []


def test_invalid_output_is_repaired_on_first_retry():
    # docs/04 §53: first failure → one repair attempt; the repair succeeds.
    provider = _SequencedProvider(["抱歉，我刚刚没听清。", _valid_json("修复后的回复。")])
    runtime = DeepSeekRuntime(provider)
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert provider.calls == 2
    assert response.dialogue == "修复后的回复。"
    assert response.character_id == "deepseek"


def test_repeated_invalid_output_falls_back():
    # docs/04 §53-54: second failure → safe fallback, still a valid response.
    runtime = DeepSeekRuntime(MockProvider(malformed=True))
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert response.character_id == "deepseek"
    assert response.dialogue == "……等一下，我脑子有点卡住了。"


def test_character_id_mismatch_falls_back():
    provider = _SequencedProvider([_valid_json().replace('"deepseek"', '"claude"')])
    runtime = DeepSeekRuntime(provider)
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert response.character_id == "deepseek"
    assert response.dialogue == "……等一下，我脑子有点卡住了。"
