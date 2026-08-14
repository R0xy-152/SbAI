"""TV-04 provider tests — no network and no API key required."""

import json
import logging

import httpx
import pytest

from app.providers.base import ProviderConfigError, ProviderError
from app.providers.deepseek import DEEPSEEK_API_URL, DEEPSEEK_MODEL, DeepSeekProvider


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    provider = DeepSeekProvider(api_key="")
    with pytest.raises(ProviderConfigError):
        provider.complete(system="s", user="你好")


def _provider_with_transport(handler):
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return DeepSeekProvider(api_key="test-key", client=client)


def test_complete_sends_expected_request():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == DEEPSEEK_API_URL
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == DEEPSEEK_MODEL
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1] == {"role": "user", "content": "你好"}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "模拟回复内容"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="你好") == "模拟回复内容"


def test_complete_forwards_response_format():
    # docs JSON Output: response_format must reach the request payload so the
    # model is constrained to emit legal JSON.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(
        system="s", user="u", response_format={"type": "json_object"}
    ) == "{}"


def test_complete_omits_response_format_when_none():
    # response_format is optional: absent from the payload unless requested.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "response_format" not in body
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "{}"


def test_complete_forwards_thinking():
    # docs 思考模式: a caller may disable the default-on chain-of-thought.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["thinking"] == {"type": "disabled"}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(
        system="s", user="u", thinking={"type": "disabled"}
    ) == "{}"


def test_complete_omits_thinking_when_none():
    # thinking is optional: absent from the payload unless requested (it is
    # on by default server-side).
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "thinking" not in body
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "{}"


def test_complete_accepts_injected_api_key_without_env(monkeypatch):
    # The env var is absent but an explicit key is passed.
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"


def test_empty_choices_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")


def test_empty_content_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "   "}}]},
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


def test_complete_logs_cache_usage(caplog):
    # docs 上下文硬盘缓存: surface cache hit/miss tokens so the fixed
    # system-prompt prefix hit rate can be measured in the backend logs.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {
                    "prompt_cache_hit_tokens": 120,
                    "prompt_cache_miss_tokens": 30,
                },
            },
        )

    provider = _provider_with_transport(handler)
    with caplog.at_level(logging.INFO):
        assert provider.complete(system="s", user="u") == "ok"
    assert "DeepSeek cache tokens" in caplog.text
    assert "hit=120" in caplog.text
    assert "miss=30" in caplog.text


def test_timeout_raises_provider_error():
    # docs/06 §21 Case A: a provider timeout is a recoverable failure.
    # httpx.TimeoutException is an HTTPError, so the adapter's single except
    # clause must surface it as ProviderError — never crash the request.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout after 30s")

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")
