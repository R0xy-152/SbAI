"""Semantic Validation Gate (docs/04 §47-51).

Schema Validation (parse_character_response) only checks that the model's raw
output is *well-formed*. This gate checks that the structured response is also
*permissible*: the character is who it claims, references only its own known
Facts, does not reach for knowledge it is forbidden (DeepSeek's visual
blindness), and proposes only allowed actions. It is the defense-in-depth
layer that turns "the prompt asked nicely" into a hard boundary (docs/04 §51:
Validate Before Present — do not rely on prompt constraints alone).

A rejected response must never reach History, Memory, Game State or the
Frontend; the caller falls back to a safe, story-neutral line instead.
"""

from __future__ import annotations

from app.characters.base import ALLOWED_RELATIONSHIP_STAGES, CharacterResponse
from app.game.scene import Scene

# docs/04 §46 / docs/05 §40: the Fact ids each character is currently
# authorized to reference. Empty in this MVP — no character may cite a Fact id
# it was not handed by the authorized Context (docs/04 §8), so any non-empty
# fact_refs is rejected. This table is content config, kept separate from the
# runtime code (docs/00: content and runtime are separated).
CHARACTER_KNOWN_FACTS: dict[str, frozenset[str]] = {
    "deepseek": frozenset(),
    "claude": frozenset(),
}

# docs/04 §45: the action types the Narrative Runtime currently accepts as
# proposals. Empty in this MVP — the only legal state change is through a
# Narrative Event (docs/03 §28), never a character's self-proposed action, so
# any action_proposals is rejected (Fail Closed).
ALLOWED_ACTION_TYPES: frozenset[str] = frozenset()


class ResponseRejected(Exception):
    """The response is well-formed but not permissible (docs/04 §50).

    Raised with a reason string; caught by the caller, which falls back.
    """


def validate_response(
    response: CharacterResponse,
    *,
    character_id: str,
    scene: Scene,
    allowed_evidence_ids: frozenset[str] = frozenset(),
    allowed_observed_fact_ids: frozenset[str] = frozenset(),
) -> None:
    """Run Character + Narrative Validation over a structured response.

    Raises ResponseRejected on the first violation; returns None when the
    response is approved (docs/04 §49-51).
    """
    _character_validation(response, character_id=character_id, scene=scene)
    for evidence_id in response.evidence_refs:
        if evidence_id not in allowed_evidence_ids:
            raise ResponseRejected(
                f"{character_id} is not authorized to reference evidence {evidence_id!r}"
            )
    for fact_id in response.observed_fact_refs:
        if fact_id not in allowed_observed_fact_ids:
            raise ResponseRejected(
                f"{character_id} is not authorized to observe fact {fact_id!r}"
            )
    _narrative_validation(response)


def _character_validation(
    response: CharacterResponse, *, character_id: str, scene: Scene
) -> None:
    # The speaker must be the character this turn is addressed to (docs/04 §49).
    if response.character_id != character_id:
        raise ResponseRejected(
            f"character_id {response.character_id!r} does not match current {character_id!r}"
        )

    # Fact references must all be within this character's authorized knowledge
    # (docs/04 §46, docs/05 §40). Anything outside is information the model
    # was never handed and must not be able to cite.
    known = CHARACTER_KNOWN_FACTS.get(character_id, frozenset())
    for ref in response.fact_refs:
        if ref not in known:
            raise ResponseRejected(
                f"{character_id} is not authorized to reference fact {ref!r}"
            )

    # DeepSeek's visual blindness is a permission boundary, not a prompt
    # preference (docs/04 §20): if she names the scene's visual ground truth,
    # she has been handed it out-of-band, and the reply is rejected.
    if character_id == "deepseek" and scene.wall_code:
        if scene.wall_code in response.dialogue or scene.wall_code in response.reasoning:
            raise ResponseRejected(
                "deepseek referenced unauthorized visual scene fact"
            )

    if (
        response.next_relationship_stage is not None
        and response.next_relationship_stage not in ALLOWED_RELATIONSHIP_STAGES
    ):
        raise ResponseRejected("relationship stage is not allowed")


def _narrative_validation(response: CharacterResponse) -> None:
    # Only the Narrative Runtime may change Game State, and only through a
    # committed Event (docs/03 §17, §28). A character's action_proposals are
    # proposals only (docs/04 §45): they must be within the currently allowed
    # set, and here the set is empty — no self-proposed action is accepted.
    for proposal in response.action_proposals:
        if proposal.type not in ALLOWED_ACTION_TYPES:
            raise ResponseRejected(
                f"action proposal {proposal.type!r} is not currently allowed"
            )
