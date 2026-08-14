"""DeepSeek provider adapter (TV-04).

Calls DeepSeek's OpenAI-compatible chat completions API over HTTP. The API key
lives only in the backend environment (docs/02 §43): it is read from the
DEEPSEEK_API_KEY environment variable and must never be committed to the repo.
"""

from __future__ import annotations

import os

import httpx

from app.providers.base import LLMProvider, ProviderConfigError, ProviderError

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEEPSEEK_API_URL,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY", "")
        self._base_url = base_url
        self._client = client if client is not None else httpx.Client()
        self._timeout = timeout

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
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
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            response = self._client.post(
                self._base_url,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"DeepSeek request failed: {exc}") from exc

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("DeepSeek response contains no choices")
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise ProviderError("DeepSeek response content is empty")
        return content
