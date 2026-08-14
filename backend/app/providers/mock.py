"""Deterministic mock provider.

Lets the whole Player → Character Runtime → Provider chain run without an API
key. A TV fixture, not production content.
"""

from __future__ import annotations

from app.providers.base import LLMProvider, ProviderError


class MockProvider(LLMProvider):
    def __init__(self, fail: bool = False) -> None:
        self._fail = fail

    def complete(self, *, system: str, user: str, max_tokens: int = 256) -> str:
        if self._fail:
            raise ProviderError("mock provider failure (injected for tests)")
        return f"这是 DeepSeek 的本地模拟回复：你说“{user}”。"
