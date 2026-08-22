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
        # A small frequency penalty curbs verbatim repetition (复读) — one of
        # the clearest "AI 人机感" tells — without breaking persona. None = leave
        # the API default (0.0). Range is [-2, 2]; 0.5 is a conservative default.
        frequency_penalty: float | None = 0.5,
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
        self._frequency_penalty = frequency_penalty

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
        if self._frequency_penalty is not None:
            payload["frequency_penalty"] = self._frequency_penalty
        if thinking is not None:
            # DeepSeek thinking mode is on by default (effort=high); a caller
            # may pass {"type": "disabled"} to turn it off for cheaper, faster
            # non-reasoning turns (docs 思考模式).
            payload["thinking"] = thinking
        # 注意：JSON 模式不强制关 thinking —— 真机探针证实 json_object 与
        # thinking 可以同时开启并正常返回 JSON；失败模式是概率性的：
        # reasoning 较长时会把 max_tokens 全部耗尽（finish=length），content
        # 为空。修复策略见下方「空 content 自动降级重试」，而不是一刀切关
        # 掉 thinking（真机 503 复盘 v2）。
        headers = {"Authorization": f"Bearer {self._api_key}"}

        def post(p: dict) -> httpx.Response:
            # 瞬时故障自动重试一次（5xx / 网络超时）；4xx（鉴权/余额等）
            # 立即失败不重试 —— 避免把配置错误伪装成瞬时抖动。
            last_error: httpx.HTTPError | None = None
            for attempt in range(2):
                try:
                    response = self._client.post(
                        self._base_url,
                        headers=headers,
                        json=p,
                        timeout=self._timeout,
                    )
                    response.raise_for_status()
                    return response
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
            raise ProviderError(f"DeepSeek request failed: {last_error}") from last_error

        def parse(response: httpx.Response) -> str:
            # T2review P1-14：非 JSON / 非对象响应必须落入统一 ProviderError
            # 边界，而不是逃逸成 400/500。
            try:
                data = response.json()
            except ValueError as exc:
                raise ProviderError(f"DeepSeek returned a non-JSON body: {exc}") from exc
            if not isinstance(data, dict):
                raise ProviderError("DeepSeek response is not a JSON object")
            # Context caching observability (docs 上下文硬盘缓存): surface how
            # much of the input prefix hit the cache vs. was recomputed.
            usage = data.get("usage") or {}
            logger.info(
                "DeepSeek cache tokens: hit=%s miss=%s",
                usage.get("prompt_cache_hit_tokens", 0),
                usage.get("prompt_cache_miss_tokens", 0),
            )
            choices = data.get("choices") or []
            if not choices:
                raise ProviderError("DeepSeek response contains no choices")
            return choices[0].get("message", {}).get("content", "").strip()

        content = parse(post(payload))

        # 空 content 自动降级重试一次（真机 503 复盘 v2 根因修复）：
        # thinking 开启时 reasoning 可能耗尽 max_tokens 预算 → content 为空
        #（API 本身 200，finish_reason=length，与账户余额无关）。此时用
        # thinking=disabled 重试一次：默认保持推理质量，空回复不再变成 503。
        thinking_disabled = thinking is not None and thinking.get("type") == "disabled"
        if not content and not thinking_disabled:
            logger.warning(
                "DeepSeek returned empty content with thinking on; "
                "retrying once with thinking disabled"
            )
            fallback = dict(payload)
            fallback["thinking"] = {"type": "disabled"}
            content = parse(post(fallback))
        if not content:
            raise ProviderError("DeepSeek response content is empty")
        return content
