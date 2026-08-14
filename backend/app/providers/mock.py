"""Deterministic mock provider.

Lets the whole Player → Character Runtime → Provider chain run without an API
key. A TV fixture, not production content.
"""

from __future__ import annotations

import json

from app.providers.base import LLMProvider, ProviderError


class MockProvider(LLMProvider):
    def __init__(self, fail: bool = False, malformed: bool = False) -> None:
        self._fail = fail
        self._malformed = malformed

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        if self._fail:
            raise ProviderError("mock provider failure (injected for tests)")
        if self._malformed:
            # Simulates a model that answers with non-JSON prose.
            return "抱歉，我刚刚没听清，你能再说一遍吗？"
        # TV-05: the mock mirrors the structured output the real model must
        # produce, so the schema-validation path is exercised without a key.
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": f"这是 DeepSeek 的本地模拟回复：你说“{user}”。",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )
