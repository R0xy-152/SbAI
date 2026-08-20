"""DeepSeek provider adapter (TV-04).

Calls DeepSeek's OpenAI-compatible chat completions API over HTTP. The API key
lives only in the backend environment (docs/02 §43): it is read from the
DEEPSEEK_API_KEY environment variable and must never be committed to the repo.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from app.providers.base import LLMProvider, ProviderConfigError, ProviderError

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

logger = logging.getLogger(__name__)


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEEPSEEK_API_URL,
        client: httpx.Client | None = None,
        # 60s：thinking 模式 + 长上下文回合实测可超过 30s（docs 思考模式）；
        # 前端 axios 超时（130s）覆盖「首轮超时 + 重试」最坏情形。
        timeout: float = 60.0,
        temperature: float | None = 0.1,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY", "")
        self._base_url = base_url
        self._client = client if client is not None else httpx.Client()
        self._timeout = timeout
        # Low temperature for consistent, in-persona roleplay (the reference
        # template's 0.1). None = leave the API default. Note: DeepSeek's
        # thinking mode may ignore temperature; it is still set for the
        # non-thinking fallback path.
        self._temperature = temperature

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
    ) -> str:
        if not self._api_key:
            raise ProviderConfigError("DEEPSEEK_API_KEY is not set")

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if self._temperature is not None:
            payload["temperature"] = self._temperature
        if thinking is not None:
            # DeepSeek thinking mode is on by default (effort=high); a caller
            # may pass {"type": "disabled"} to turn it off for cheaper, faster
            # non-reasoning turns (docs 思考模式).
            payload["thinking"] = thinking
        elif response_format is not None:
            # 真机接入 503 复盘：json_object 输出模式下若保持默认开启的
            # thinking，推理过程会消耗 token 预算，模型常返回空 content
            #（"DeepSeek response content is empty" → ProviderError → 503）。
            # DeepSeek 官方约束：JSON 输出需关闭 thinking。调用方未显式指定
            # thinking 时，JSON 模式强制关闭。
            payload["thinking"] = {"type": "disabled"}
        headers = {"Authorization": f"Bearer {self._api_key}"}

        # 瞬时故障自动重试一次（5xx / 网络超时）；4xx（鉴权/余额等）立即失败
        # 不重试 —— 避免把配置错误伪装成瞬时抖动（真机接入 503 复盘）。
        last_error: httpx.HTTPError | None = None
        for attempt in range(2):
            try:
                response = self._client.post(
                    self._base_url,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code >= 500 and attempt == 0:
                    logger.warning(
                        "DeepSeek upstream 5xx, retrying once: %s", exc
                    )
                    time.sleep(0.4)
                    continue
                raise ProviderError(f"DeepSeek request failed: {exc}") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning(
                        "DeepSeek transport error, retrying once: %s", exc
                    )
                    time.sleep(0.4)
                    continue
                raise ProviderError(f"DeepSeek request failed: {exc}") from exc
        else:
            raise ProviderError(f"DeepSeek request failed: {last_error}") from last_error

        # T2review P1-14：非 JSON / 非对象响应必须落入统一 ProviderError
        # 边界，而不是逃逸成 400/500。
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"DeepSeek returned a non-JSON body: {exc}") from exc
        if not isinstance(data, dict):
            raise ProviderError("DeepSeek response is not a JSON object")
        # Context caching observability (docs 上下文硬盘缓存): surface how much
        # of the input prefix hit the cache vs. was recomputed, so the hit rate
        # of the fixed system prompt can be measured in the backend logs.
        usage = data.get("usage") or {}
        logger.info(
            "DeepSeek cache tokens: hit=%s miss=%s",
            usage.get("prompt_cache_hit_tokens", 0),
            usage.get("prompt_cache_miss_tokens", 0),
        )
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("DeepSeek response contains no choices")
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise ProviderError("DeepSeek response content is empty")
        return content
