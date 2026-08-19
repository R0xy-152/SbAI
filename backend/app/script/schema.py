"""Script Event Schema (docs/12 §15-26, §36-37).

The first-version Script DSL is a bounded set of eleven event types, validated
by Pydantic (docs/12 §36: Backend Pydantic 定义 Script Event Schema，Frontend 不
解析 YAML). Content is authored as Python structures (user decision) and parsed
through :func:`load_sequences`, which fails closed on any reference problem —
unknown event type, missing required field, nonexistent node/condition/animation/
transition target — and reports script_id + step index (docs/12 §37).

``ScriptError`` is the runtime's fail-closed error (docs/12 §17, §24): a script
proposing something the current Narrative State does not allow.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, ValidationError

from app.characters.base import ALLOWED_ANIMATIONS, ALLOWED_EMOTIONS

CHARACTER_IDS = frozenset({"deepseek", "claude", "chatgpt", "doubao", "system"})
SCRIPT_SLOTS = frozenset({"LEFT", "CENTER_LEFT", "CENTER", "CENTER_RIGHT", "RIGHT"})
# Presentation-step actions are the non-character effects (docs/12 §23); the
# character_show/update/... steps map directly to CHARACTER_* actions.
PRESENTATION_ACTIONS = frozenset(
    {"screen_glitch", "screen_shake", "dialogue_focus", "input_lock", "input_unlock"}
)
# Unlock targets are only characters the Narrative Runtime can legally open.
# chatgpt is deliberately excluded: his availability belongs to the deduction
# runtime alone (docs/12 §33 — the strongest boundary demonstration).
UNLOCK_TARGETS = frozenset({"claude", "doubao"})
PHASE_TARGETS = frozenset({"INVESTIGATION_CLAUDE", "RECOVERY_REQUIRED"})


class ScriptLoadError(ValueError):
    """A Script Content reference could not be validated (docs/12 §37)."""

    def __init__(self, script_id: str, step_index: int, message: str) -> None:
        super().__init__(f"[script:{script_id} step:{step_index}] {message}")
        self.script_id = script_id
        self.step_index = step_index


class ScriptError(ValueError):
    """A runtime fail-closed error: the script proposed something disallowed."""

    def __init__(self, script_id: str, step_index: int, message: str) -> None:
        super().__init__(f"[script:{script_id} step:{step_index}] {message}")
        self.script_id = script_id
        self.step_index = step_index


class BackgroundStep(BaseModel):
    type: Literal["background"] = "background"
    background: str
    transition: Literal["fade", "none"] = "fade"


class CharacterShowStep(BaseModel):
    type: Literal["character_show"] = "character_show"
    character: str
    emotion: str = "neutral"
    slot: str | None = None
    animation: str = "none"


class CharacterHideStep(BaseModel):
    type: Literal["character_hide"] = "character_hide"
    character: str
    animation: str = "fade_out"


class CharacterUpdateStep(BaseModel):
    type: Literal["character_update"] = "character_update"
    character: str
    emotion: str | None = None
    slot: str | None = None
    scale: float | None = None
    offset_x: float | None = None
    offset_y: float | None = None
    animation: str | None = None


class ScriptDialogueStep(BaseModel):
    type: Literal["script_dialogue"] = "script_dialogue"
    character: str
    node: str


class PlayerInputStep(BaseModel):
    type: Literal["player_input"] = "player_input"
    mode: str = "investigation"


class AiDialogueStep(BaseModel):
    type: Literal["ai_dialogue"] = "ai_dialogue"
    character: str
    directive: str | None = None


class PresentationStep(BaseModel):
    type: Literal["presentation"] = "presentation"
    action: str
    intensity: str = "medium"


class NarrativeGateStep(BaseModel):
    type: Literal["narrative_gate"] = "narrative_gate"
    condition: str


class UnlockStep(BaseModel):
    type: Literal["unlock"] = "unlock"
    target: str


class PhaseTransitionStep(BaseModel):
    type: Literal["phase_transition"] = "phase_transition"
    to: str


ScriptStep = Annotated[
    Union[
        BackgroundStep,
        CharacterShowStep,
        CharacterHideStep,
        CharacterUpdateStep,
        ScriptDialogueStep,
        PlayerInputStep,
        AiDialogueStep,
        PresentationStep,
        NarrativeGateStep,
        UnlockStep,
        PhaseTransitionStep,
    ],
    Field(discriminator="type"),
]


class ScriptSequence(BaseModel):
    script_id: str
    steps: list[ScriptStep]


# Which fields each event type requires (docs/12 §37: 缺少必填字段 → fail).
_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "background": ("background",),
    "character_show": ("character",),
    "character_hide": ("character",),
    "character_update": ("character",),
    "script_dialogue": ("character", "node"),
    "player_input": (),
    "ai_dialogue": ("character",),
    "presentation": ("action",),
    "narrative_gate": ("condition",),
    "unlock": ("target",),
    "phase_transition": ("to",),
}


def load_sequences(sequences: list[dict]) -> dict[str, ScriptSequence]:
    """Parse authored Python content into validated ScriptSequence models.

    Fails closed with script_id + step index on: unknown event type, missing
    required field, or a Pydantic field/union error (docs/12 §37). Reference
    checks (node / condition / animation / transition target / character) are
    performed later by the ScriptRegistry so it has access to the registries.
    """
    loaded: dict[str, ScriptSequence] = {}
    for data in sequences:
        script_id = data.get("script_id")
        if not isinstance(script_id, str) or not script_id:
            raise ScriptLoadError("<sequence>", -1, "script_id is required")
        steps = data.get("steps")
        if not isinstance(steps, list):
            raise ScriptLoadError(script_id, -1, "steps must be a list")
        if script_id in loaded:
            raise ScriptLoadError(script_id, -1, "duplicate script_id")
        for index, raw in enumerate(steps):
            if not isinstance(raw, dict):
                raise ScriptLoadError(script_id, index, "step must be an object")
            step_type = raw.get("type")
            if step_type not in _REQUIRED_FIELDS:
                raise ScriptLoadError(script_id, index, f"unknown event type {step_type!r}")
            for field_name in _REQUIRED_FIELDS[step_type]:
                if raw.get(field_name) is None:
                    raise ScriptLoadError(
                        script_id, index, f"missing required field {field_name!r}"
                    )
        try:
            loaded[script_id] = ScriptSequence(**data)
        except ValidationError as exc:
            first = exc.errors()[0]
            raise ScriptLoadError(
                script_id, -1, f"{first['loc']}: {first['msg']}"
            ) from exc
    return loaded
