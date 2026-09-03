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


def test_json_mode_keeps_default_thinking():
    # 真机 503 复盘 v2：json_object 与 thinking 可同时开启（探针实证），
    # provider 不强制关闭 thinking —— 调用方未显式指定时不注入 thinking 键。
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        assert "thinking" not in body
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    provider = _provider_with_transport(handler)
    assert (
        provider.complete(system="s", user="u", response_format={"type": "json_object"})
        == "{}"
    )


def test_empty_content_with_thinking_falls_back_to_disabled():
    # 真机 503 复盘 v2：thinking 开启时 reasoning 耗尽 max_tokens → 空 content
    #（API 200、finish=length，与余额无关）；provider 自动降级重试一次
    #（thinking=disabled），成功则返回内容。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(request.content)
        if calls["n"] == 1:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": ""}}]},
            )
        assert body["thinking"] == {"type": "disabled"}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    provider = _provider_with_transport(handler)
    assert (
        provider.complete(system="s", user="u", response_format={"type": "json_object"})
        == "{}"
    )
    assert calls["n"] == 2


def test_empty_content_with_explicit_disabled_raises_no_loop():
    # thinking 已显式禁用仍空 content：直接 ProviderError，不得无限降级。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": ""}}]},
        )

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(
            system="s", user="u", thinking={"type": "disabled"}
        )
    assert calls["n"] == 1


def test_empty_content_without_json_mode_also_falls_back():
    # 角色对话（无 response_format）同样可能被 reasoning 挤空 content，
    # 降级重试对所有调用生效。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(request.content)
        if calls["n"] == 1:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": ""}}]},
            )
        assert body["thinking"] == {"type": "disabled"}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "好"}}]},
        )

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "好"
    assert calls["n"] == 2


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


def test_complete_sets_default_temperature():
    # The reference template's low temperature (0.1) for consistent roleplay
    # is the provider default and must reach the request payload.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["temperature"] == 0.1
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"


def test_complete_omits_temperature_when_none():
    # temperature=None restores the API default and must not be sent.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "temperature" not in body
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = DeepSeekProvider(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        temperature=None,
    )
    assert provider.complete(system="s", user="u") == "ok"


def test_complete_does_not_send_unsupported_frequency_penalty():
    # DeepSeek deprecated frequency_penalty and ignores it, especially in
    # thinking mode. Do not advertise or send a no-op control.
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "frequency_penalty" not in body
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"


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
def test_transient_5xx_retries_once_and_succeeds():
    # 真机接入 503 复盘：上游瞬时 5xx 自动重试一次后成功。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": {"message": "upstream busy"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"
    assert calls["n"] == 2


def test_persistent_5xx_raises_after_one_retry():
    # 两次 5xx：最终仍以 ProviderError 上抛（HTTP 503 给前端）。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"error": {"message": "upstream busy"}})

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")
    assert calls["n"] == 2


def test_transient_timeout_retries_once_and_succeeds():
    # 网络超时同样视为瞬时故障，重试一次。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout after 60s")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = _provider_with_transport(handler)
    assert provider.complete(system="s", user="u") == "ok"
    assert calls["n"] == 2


def test_4xx_is_not_retried():
    # 鉴权/余额等 4xx 是配置错误，立即失败且只发一次请求。
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    provider = _provider_with_transport(handler)
    with pytest.raises(ProviderError):
        provider.complete(system="s", user="u")
    assert calls["n"] == 1
