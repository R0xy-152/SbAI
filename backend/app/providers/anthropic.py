"""Anthropic provider adapter.

Calls Anthropic's Messages API over HTTP. The API key lives only in the backend
environment (docs/02 §43): it is read from the ANTHROPIC_API_KEY environment
variable and must never be committed to the repo.
"""

from __future__ import annotations

import os
import time

import httpx

from app.providers.base import LLMProvider, ProviderConfigError, ProviderError

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    supports_metrics = True  # docs/21 §4：complete() 尽力填充延迟/token 出参

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = ANTHROPIC_API_URL,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
        temperature: float | None = 0.1,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url
        self._client = client if client is not None else httpx.Client()
        self._timeout = timeout
        # Low temperature for consistent, in-persona roleplay (the reference
        # template's 0.1). None = leave the API default.
        self._temperature = temperature

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
        metrics: dict | None = None,
    ) -> str:
        # metrics（docs/21 §4）：尽力填充延迟与 usage；生产未启用 Anthropic，
        # 该路径当前只由显式 CLAUDE_PROVIDER=anthropic 配置触发。
        started = time.perf_counter()
        if not self._api_key:
            raise ProviderConfigError("ANTHROPIC_API_KEY is not set")

        # The Messages API has no OpenAI-style `response_format` or `thinking`
        # knobs. They arrive as provider-agnostic hints from the shared runtime,
        # so both are deliberately ignored here (Anthropic thinking is off by
        # default), and `thinking` is never forwarded.
        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if self._temperature is not None:
            payload["temperature"] = self._temperature
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        try:
            response = self._client.post(
                self._base_url,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc

        # T2review P1-14：非 JSON / 非对象响应统一落入 ProviderError 边界。
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"Anthropic returned a non-JSON body: {exc}") from exc
        if not isinstance(data, dict):
            raise ProviderError("Anthropic response is not a JSON object")
        content = data.get("content") or []
        if not content:
            raise ProviderError("Anthropic response contains no content")
        first = content[0]
        text = (first.get("text", "") if isinstance(first, dict) else "").strip()
        if not text:
            raise ProviderError("Anthropic response content is empty")
        if metrics is not None:
            usage = data.get("usage") or {}
            metrics["latency_ms"] = metrics.get("latency_ms", 0.0) + (
                time.perf_counter() - started
            ) * 1000.0
            metrics["prompt_tokens"] = metrics.get("prompt_tokens", 0) + int(
                usage.get("input_tokens", 0) or 0
            )
            metrics["completion_tokens"] = metrics.get(
                "completion_tokens", 0
            ) + int(usage.get("output_tokens", 0) or 0)
            metrics["cache_hit_tokens"] = metrics.get("cache_hit_tokens", 0) + int(
                (usage.get("cache_read_input_tokens", 0) or 0)
            )
            metrics["cache_miss_tokens"] = metrics.get(
                "cache_miss_tokens", 0
            ) + max(0, int(usage.get("input_tokens", 0) or 0) - int(
                usage.get("cache_read_input_tokens", 0) or 0
            ))
            metrics["model"] = ANTHROPIC_MODEL
            metrics["calls"] = metrics.get("calls", 0) + 1
        return text
