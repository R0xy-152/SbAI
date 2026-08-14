"""Provider interface and error types.

Character runtimes depend on this interface only, never on a specific
provider's HTTP format (docs/02 §18: character and model provider must be
decoupled).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Recoverable provider failure: timeout, HTTP error, empty content."""


class ProviderConfigError(ProviderError):
    """Provider is misconfigured (for example, the API key is missing)."""


class LLMProvider(ABC):
    """Minimal text-completion interface.

    TV-04 only needs a single system + user message. Multi-turn history
    (TV-07 Short-term Context) will extend this interface later.
    """

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        """Return the assistant reply text; raise ProviderError on failure.

        response_format is an optional provider-level hint (for example
        {"type": "json_object"} for structured-output APIs). The mock provider
        ignores it; a provider that does not support it may raise.
        """
