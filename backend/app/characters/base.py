"""Character Runtime interface and request/response types (docs/04 §4-5, §40)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CharacterRequest:
    """Logical input to a character runtime (docs/04 §5)."""

    character_id: str
    player_message: str
    recent_conversation: list[dict] = field(default_factory=list)


@dataclass
class MemoryProposal:
    """Something in this turn that may be worth remembering long-term (docs/04 §44)."""

    type: str
    content: str


@dataclass
class ActionProposal:
    """A game behavior the character would like to happen (docs/04 §45).

    A proposal only: it must be routed through the Narrative Runtime, never
    applied directly to Game State.
    """

    type: str
    target: str | None = None


# Named emotion / animation allow-lists (docs/04 §42-43). The model must pick
# from these; it must not emit rendering parameters.
ALLOWED_EMOTIONS = frozenset({"neutral", "happy", "annoyed", "angry", "embarrassed", "serious"})
ALLOWED_ANIMATIONS = frozenset({"none", "shake", "strong_shake", "fade_in", "fade_out"})


@dataclass
class CharacterResponse:
    """Validated output every runtime must produce (docs/04 §40).

    TV-05 makes the response structured: beyond the spoken dialogue it carries
    a named emotion, an animation proposal, and long-term memory / game-action
    proposals. Everything here is validated before it is accepted (docs/04 §48).
    """

    character_id: str
    dialogue: str
    emotion: str = "neutral"
    animation_proposal: str = "none"
    memory_proposals: list[MemoryProposal] = field(default_factory=list)
    action_proposals: list[ActionProposal] = field(default_factory=list)
    fact_refs: list[str] = field(default_factory=list)


class CharacterResponseValidationError(Exception):
    """The model's raw output failed Schema Validation (docs/04 §48)."""


def parse_character_response(raw: str, expected_character_id: str) -> CharacterResponse:
    """Schema Validation (docs/04 §48): parse the model's raw text into a
    CharacterResponse.

    Checks: required fields present, correct types, character_id matches the
    expected character, emotion/animation in the allow-lists, and proposal
    structure. Raises CharacterResponseValidationError on any violation, so
    invalid content can be rejected / repaired / fallen back instead of being
    presented to the player.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CharacterResponseValidationError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CharacterResponseValidationError("response must be a JSON object")

    character_id = data.get("character_id")
    if not isinstance(character_id, str) or not character_id:
        raise CharacterResponseValidationError("character_id must be a non-empty string")
    if character_id != expected_character_id:
        raise CharacterResponseValidationError(
            f"character_id {character_id!r} does not match expected {expected_character_id!r}"
        )

    dialogue = data.get("dialogue")
    if not isinstance(dialogue, str) or not dialogue.strip():
        raise CharacterResponseValidationError("dialogue must be a non-empty string")

    emotion = data.get("emotion")
    if not isinstance(emotion, str) or emotion not in ALLOWED_EMOTIONS:
        raise CharacterResponseValidationError(f"emotion {emotion!r} is not in the allowed set")

    animation = data.get("animation_proposal")
    if not isinstance(animation, str) or animation not in ALLOWED_ANIMATIONS:
        raise CharacterResponseValidationError(
            f"animation_proposal {animation!r} is not in the allowed set"
        )

    return CharacterResponse(
        character_id=character_id,
        dialogue=dialogue.strip(),
        emotion=emotion,
        animation_proposal=animation,
        memory_proposals=_parse_memory_proposals(data.get("memory_proposals")),
        action_proposals=_parse_action_proposals(data.get("action_proposals")),
        fact_refs=_parse_fact_refs(data.get("fact_refs")),
    )


def _parse_memory_proposals(value) -> list[MemoryProposal]:
    if value is None:
        raise CharacterResponseValidationError("memory_proposals is required")
    if not isinstance(value, list):
        raise CharacterResponseValidationError("memory_proposals must be a list")
    proposals = []
    for item in value:
        if not isinstance(item, dict):
            raise CharacterResponseValidationError("each memory_proposal must be an object")
        proposal_type = item.get("type")
        content = item.get("content")
        if not isinstance(proposal_type, str) or not proposal_type:
            raise CharacterResponseValidationError(
                "memory_proposal.type must be a non-empty string"
            )
        if not isinstance(content, str) or not content:
            raise CharacterResponseValidationError(
                "memory_proposal.content must be a non-empty string"
            )
        proposals.append(MemoryProposal(type=proposal_type, content=content))
    return proposals


def _parse_action_proposals(value) -> list[ActionProposal]:
    if value is None:
        raise CharacterResponseValidationError("action_proposals is required")
    if not isinstance(value, list):
        raise CharacterResponseValidationError("action_proposals must be a list")
    proposals = []
    for item in value:
        if not isinstance(item, dict):
            raise CharacterResponseValidationError("each action_proposal must be an object")
        proposal_type = item.get("type")
        if not isinstance(proposal_type, str) or not proposal_type:
            raise CharacterResponseValidationError(
                "action_proposal.type must be a non-empty string"
            )
        target = item.get("target")
        if target is not None and not isinstance(target, str):
            raise CharacterResponseValidationError("action_proposal.target must be a string")
        proposals.append(ActionProposal(type=proposal_type, target=target))
    return proposals


def _parse_fact_refs(value) -> list[str]:
    if value is None:
        raise CharacterResponseValidationError("fact_refs is required")
    if not isinstance(value, list) or not all(isinstance(ref, str) for ref in value):
        raise CharacterResponseValidationError("fact_refs must be a list of strings")
    return list(value)


class CharacterRuntime(ABC):
    character_id: str = ""

    @abstractmethod
    def respond(self, request: CharacterRequest) -> CharacterResponse:
        """Produce the character's reply for this request."""
