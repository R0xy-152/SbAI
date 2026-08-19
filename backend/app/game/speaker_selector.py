"""Bounded LLM proposal of the public-scene replying character."""

from __future__ import annotations

import json

from app.providers.base import LLMProvider, ProviderError


class SpeakerSelector:
    def __init__(self, provider: LLMProvider, default_character: str = "deepseek") -> None:
        self._provider = provider
        self._default = default_character

    def choose(self, message: str, available: set[str]) -> str:
        allowed = sorted(available)
        fallback = self._default if self._default in available else allowed[0]
        if len(allowed) == 1:
            return fallback
        try:
            raw = self._provider.complete(
                system=("Choose the best public-scene respondent. Output only JSON "
                        "{\"character_id\": \"...\"}. Allowed: " + ", ".join(allowed)),
                user=message,
                response_format={"type": "json_object"},
            )
            candidate = json.loads(raw).get("character_id")
            return candidate if candidate in available else fallback
        except (ProviderError, ValueError, TypeError, json.JSONDecodeError):
            return fallback
