"""Character Runtime Registry (docs/04 §61-62).

The Game Orchestrator no longer owns the runtime map or the default character.
This registry resolves "which character speaks this turn" — an explicit
character_id, the session's last speaker, then the configured default — and
looks up that character's runtime. Resolving an unknown character fails loudly
instead of guessing.
"""

from __future__ import annotations

from app.characters.base import CharacterRuntime


class CharacterRuntimeRegistry:
    def __init__(
        self,
        runtimes: dict[str, CharacterRuntime],
        default_character: str = "deepseek",
    ) -> None:
        self._runtimes = dict(runtimes)
        self.default_character = default_character

    def resolve(self, requested: str | None, last: str | None) -> str:
        """Pick the speaking character for this turn (docs/04 §61).

        Precedence: an explicit request, the session's last speaker, then the
        configured default. An id not in the registry raises ValueError — never
        a silent fallback.
        """
        character_id = requested or last or self.default_character
        if character_id not in self._runtimes:
            raise ValueError(f"unknown character: {character_id}")
        return character_id

    def get(self, character_id: str) -> CharacterRuntime:
        return self._runtimes[character_id]
