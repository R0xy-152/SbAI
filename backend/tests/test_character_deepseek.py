"""TV-04 character runtime tests using the deterministic mock provider."""

import pytest

from app.characters.base import CharacterRequest
from app.characters.deepseek import DeepSeekRuntime
from app.providers.base import ProviderError
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
