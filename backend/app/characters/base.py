"""Character Runtime interface and request/response types (docs/04 §4-5, §40)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CharacterRequest:
    """Logical input to a character runtime (docs/04 §5)."""

    character_id: str
    player_message: str
    recent_conversation: list[dict] = field(default_factory=list)


@dataclass
class CharacterResponse:
    """Validated output every runtime must produce (docs/04 §40).

    TV-04 only requires character_id + dialogue. The structured extras
    (emotion, animation_proposal, memory_proposals, action_proposals,
    fact_refs) arrive with TV-05.
    """

    character_id: str
    dialogue: str


class CharacterRuntime(ABC):
    character_id: str = ""

    @abstractmethod
    def respond(self, request: CharacterRequest) -> CharacterResponse:
        """Produce the character's reply for this request."""
