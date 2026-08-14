"""TV-04 provider tests — no network and no API key required."""

import json

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


def test_timeout_raises_provider_error():
    # docs/06 §21 Case A: a provider timeout is a recoverable failure.
    # httpx.TimeoutException is an HTTPError, so the adapter's single except
    # clause must surface it as ProviderError — never crash the request.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout after 30s")

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")
