"""Unified Presentation Action schema (docs/12 §13, §39 Task 1).

The Backend is the sole authority on who is on stage, with which emotion, and
which named animation plays. It never ships DOM/CSS parameters — only a bounded
set of registered Presentation Actions that the Frontend is allowed to execute.
Unknown actions are rejected (docs/12 §13: 任何未知 Action 拒绝执行并记录日志).

``directive_to_actions`` maps the legacy story-semantic directives from a
committed Narrative Event (docs/03 §13.6, e.g. ``("SHOW_CHARACTER", "claude")``)
into the structured channel, so existing event definitions keep working while
the Frontend migrates to ``presentation_actions``.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, field_validator

from app.characters.base import ALLOWED_ANIMATIONS, ALLOWED_EMOTIONS

logger = logging.getLogger(__name__)

PresentationActionType = Literal[
    "CHARACTER_SHOW",
    "CHARACTER_HIDE",
    "CHARACTER_EMOTION",
    "CHARACTER_ANIMATION",
    "BACKGROUND_SET",
    "BACKGROUND_FADE",
    "SCREEN_SHAKE",
    "SCREEN_GLITCH",
    "DIALOGUE_FOCUS",
    "INPUT_LOCK",
    "INPUT_UNLOCK",
]

# Explicit stage slots (docs/12 §10.1): explicit slot > manual offset > auto.
SCRIPT_SLOTS = frozenset({"LEFT", "CENTER_LEFT", "CENTER", "CENTER_RIGHT", "RIGHT"})


class PresentationAction(BaseModel):
    """One bounded, registered presentation action (docs/12 §13)."""

    type: PresentationActionType
    character_id: str | None = None
    emotion: str | None = None
    animation: str | None = None
    slot: str | None = None
    scale: float | None = None
    offset_x: float | None = None
    offset_y: float | None = None
    background: str | None = None
    transition: str | None = None
    intensity: str | None = None

    @field_validator("emotion")
    @classmethod
    def _check_emotion(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_EMOTIONS:
            raise ValueError(f"emotion {value!r} is not in the allowed set")
        return value

    @field_validator("animation")
    @classmethod
    def _check_animation(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_ANIMATIONS:
            raise ValueError(f"animation {value!r} is not in the allowed set")
        return value

    @field_validator("slot")
    @classmethod
    def _check_slot(cls, value: str | None) -> str | None:
        if value is not None and value not in SCRIPT_SLOTS:
            raise ValueError(f"slot {value!r} is not in the allowed set")
        return value


# Legacy directive kind → (structured action type, arity in the flat tuple).
# docs/03 §13.6: a committed event's presentation is a flat tuple of tokens
# such as ("SHOW_CHARACTER", "claude").
_DIRECTIVE_ARITY: dict[str, tuple[str, int]] = {
    "SHOW_CHARACTER": ("CHARACTER_SHOW", 2),
    "HIDE_CHARACTER": ("CHARACTER_HIDE", 2),
    "SET_EMOTION": ("CHARACTER_EMOTION", 3),
}


def directive_to_actions(presentation: tuple[str, ...]) -> list[PresentationAction]:
    """Map legacy event directives (docs/03 §13.6) to structured actions.

    Unknown directives are logged and skipped — never a hard failure — because
    the legacy channel is being phased out; the structured channel is produced
    directly by the Script Runtime and is already canonical.
    """
    actions: list[PresentationAction] = []
    index = 0
    while index < len(presentation):
        kind = presentation[index]
        mapping = _DIRECTIVE_ARITY.get(kind)
        if mapping is None:
            logger.debug("ignoring unknown presentation directive %r", kind)
            index += 1
            continue
        action_type, arity = mapping
        if index + arity > len(presentation):
            logger.debug("truncated presentation directive %r", kind)
            break
        token = presentation[index + 1]
        if action_type == "CHARACTER_SHOW":
            actions.append(
                PresentationAction(type="CHARACTER_SHOW", character_id=token)
            )
        elif action_type == "CHARACTER_HIDE":
            actions.append(
                PresentationAction(type="CHARACTER_HIDE", character_id=token)
            )
        elif action_type == "CHARACTER_EMOTION":
            actions.append(
                PresentationAction(
                    type="CHARACTER_EMOTION",
                    character_id=token,
                    emotion=presentation[index + 2],
                )
            )
        index += arity
    return actions
