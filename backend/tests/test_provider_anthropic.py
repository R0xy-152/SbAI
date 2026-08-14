"""Anthropic provider tests — no network and no API key required.

Also proves that each generative character can be driven by its own real
provider (DeepSeek → DeepSeekProvider, Claude → AnthropicProvider) and by the
mock provider, so the Character Runtime stays provider-agnostic (docs/02 §18).
"""

import json

import httpx
import pytest

from app.characters.base import CharacterRequest
from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.providers.anthropic import ANTHROPIC_API_URL, ANTHROPIC_MODEL, AnthropicProvider
from app.providers.base import ProviderConfigError, ProviderError
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider
from app.main import build_provider


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(api_key="")
    with pytest.raises(ProviderConfigError):
        provider.complete(system="s", user="你好")


def _provider_with_transport(handler):
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return AnthropicProvider(api_key="test-key", client=client)


def _text_response(text: str) -> httpx.Response:
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


def test_complete_sends_expected_request():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == ANTHROPIC_API_URL
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert request.headers["content-type"] == "application/json"
        body = json.loads(request.content)
        assert body["model"] == ANTHROPIC_MODEL
        assert body["max_tokens"] == 256
        assert body["system"] == "s"
        assert body["messages"] == [{"role": "user", "content": "你好"}]
        return _text_response("模拟回复内容")

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="你好") == "模拟回复内容"


def test_complete_parses_content_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return _text_response("ok")

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"


def test_complete_sets_default_temperature():
    # The reference template's low temperature (0.1) is the provider default.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["temperature"] == 0.1
        return _text_response("ok")

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"


def test_complete_accepts_injected_api_key_without_env(monkeypatch):
    # The env var is absent but an explicit key is passed.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        return _text_response("ok")

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"


def test_complete_tolerates_thinking_and_omits_it_from_payload():
    # The shared runtime always passes thinking={"type": "disabled"}; the
    # Anthropic adapter must not forward it (Anthropic thinking is off by
    # default) and must not error.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "thinking" not in body
        return _text_response("ok")

    provider = _provider_with_transport(handler)
    assert (
        provider.complete(system="s", user="u", thinking={"type": "disabled"})
        == "ok"
    )


def test_complete_tolerates_response_format_and_omits_it_from_payload():
    # response_format is an OpenAI-style hint the Messages API does not have;
    # it must be ignored, not forwarded.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "response_format" not in body
        return _text_response("ok")

    provider = _provider_with_transport(handler)
    assert (
        provider.complete(system="s", user="u", response_format={"type": "json_object"})
        == "ok"
    )


def test_empty_content_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": []})

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")


def test_empty_text_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "   "}]}
        )

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")


def test_http_error_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")


def test_timeout_raises_provider_error():
    # httpx.TimeoutException is an HTTPError, so the adapter's single except
    # clause must surface it as ProviderError — never crash the request.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout after 30s")

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")


# ---- each provider drives its own character runtime ----

def _structured_json(character_id: str, dialogue: str) -> str:
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


def test_anthropic_provider_drives_claude_runtime():
    def handler(request: httpx.Request) -> httpx.Response:
        return _text_response(_structured_json("claude", "哼，别想套我话。"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    runtime = ClaudeRuntime(AnthropicProvider(api_key="test-key", client=client))
    response = runtime.respond(
        CharacterRequest(character_id="claude", player_message="你好")
    )
    assert response.character_id == "claude"
    assert response.dialogue == "哼，别想套我话。"


def test_deepseek_provider_drives_deepseek_runtime():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": _structured_json("deepseek", "我在。")}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    runtime = DeepSeekRuntime(DeepSeekProvider(api_key="test-key", client=client))
    response = runtime.respond(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert response.character_id == "deepseek"
    assert response.dialogue == "我在。"


def test_mock_provider_drives_claude_runtime():
    runtime = ClaudeRuntime(MockProvider(character_id="claude"))
    response = runtime.respond(
        CharacterRequest(character_id="claude", player_message="你好")
    )
    assert response.character_id == "claude"
    assert response.dialogue


# ---- provider assembly (main.build_provider) ----


def test_build_provider_defaults_to_shared_deepseek(monkeypatch):
    # MVP default: every generative character shares the DeepSeek adapter.
    monkeypatch.setenv("GAL_PROVIDER", "auto")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PROVIDER", raising=False)
    assert isinstance(build_provider("deepseek"), DeepSeekProvider)
    assert isinstance(build_provider("claude"), DeepSeekProvider)


def test_build_provider_claude_anthropic_opt_in(monkeypatch):
    # CLAUDE_PROVIDER=anthropic switches only Claude; DeepSeek is unchanged.
    monkeypatch.setenv("GAL_PROVIDER", "auto")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("CLAUDE_PROVIDER", "anthropic")
    assert isinstance(build_provider("claude"), AnthropicProvider)
    assert isinstance(build_provider("deepseek"), DeepSeekProvider)


def test_build_provider_anthropic_opt_in_without_key_fails(monkeypatch):
    # An explicit opt-in must not silently fall back to the wrong provider.
    monkeypatch.setenv("GAL_PROVIDER", "auto")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_PROVIDER", "anthropic")
    with pytest.raises(ProviderConfigError):
        build_provider("claude")


def test_build_provider_keyless_degrades_to_mock(monkeypatch):
    monkeypatch.setenv("GAL_PROVIDER", "auto")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PROVIDER", raising=False)
    assert isinstance(build_provider("deepseek"), MockProvider)
    assert isinstance(build_provider("claude"), MockProvider)
