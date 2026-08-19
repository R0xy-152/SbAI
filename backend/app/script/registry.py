"""Script Registry: dialogue nodes, sequences and begin-triggers (docs/12 §20, §28).

Owns the authored references and validates them once at wiring time (fail
closed, docs/12 §37). The trigger table is data: ``(condition_id, script_id)``
pairs evaluated highest-priority first — the Script Runtime starts a script
only when its condition holds over the authoritative Narrative State.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.characters.base import ALLOWED_ANIMATIONS, ALLOWED_EMOTIONS
from app.script.conditions import CONDITION_REGISTRY
from app.script.schema import (
    CHARACTER_IDS,
    PHASE_TARGETS,
    PRESENTATION_ACTIONS,
    SCRIPT_SLOTS,
    UNLOCK_TARGETS,
    NarrativeGateStep,
    PhaseTransitionStep,
    PresentationStep,
    ScriptDialogueStep,
    ScriptLoadError,
    ScriptSequence,
    UnlockStep,
)


@dataclass(frozen=True)
class DialogueNode:
    """One reusable fixed line (docs/12 §20: node ID, not inline text).

    ``character`` is carried on the node so the runtime can build the wire
    ``ScriptSequenceLine`` directly, and so the same text can be reused from a
    different speaker only by declaring a different node.
    """

    node_id: str
    character: str
    text: str
    emotion: str = "neutral"
    animation: str = "none"


# Begin-trigger table (docs/12 §29, §39): condition → script, highest priority
# first. All conditions are pure predicates over NarrativeState (conditions.py).
SCRIPT_TRIGGERS: list[tuple[str, str]] = [
    ("INCIDENT_0317_READY", "CH01_INCIDENT_0317"),
    ("DOUBAO_ARRIVAL_READY", "CH01_DOUBAO_ARRIVAL"),
    ("GPT_ARRIVAL_READY", "CH01_GPT_ARRIVAL"),
    ("INF03_ACCEPTED", "CH01_FINAL_REVEAL"),
]


class ScriptRegistry:
    def __init__(
        self,
        sequences: dict[str, ScriptSequence],
        dialogue_nodes: dict[str, DialogueNode],
        triggers: list[tuple[str, str]] = SCRIPT_TRIGGERS,
    ) -> None:
        self._sequences = dict(sequences)
        self._dialogue_nodes = dict(dialogue_nodes)
        self._triggers = list(triggers)
        self._validate()

    def _validate(self) -> None:
        for node_id, node in self._dialogue_nodes.items():
            if node.node_id != node_id:
                raise ScriptLoadError(node_id, -1, "dialogue node id mismatch")
            self._check_reference(node_id, -1, "character", node.character, CHARACTER_IDS)
            self._check_reference(node_id, -1, "emotion", node.emotion, ALLOWED_EMOTIONS)
            self._check_reference(node_id, -1, "animation", node.animation, ALLOWED_ANIMATIONS)
        for script_id, sequence in self._sequences.items():
            if sequence.script_id != script_id:
                raise ScriptLoadError(script_id, -1, "script_id key mismatch")
            for index, step in enumerate(sequence.steps):
                self._validate_step(sequence, index, step)
        for condition_id, script_id in self._triggers:
            if condition_id not in CONDITION_REGISTRY:
                raise ScriptLoadError(script_id, -1, f"unknown trigger condition {condition_id!r}")
            if script_id not in self._sequences:
                raise ScriptLoadError(script_id, -1, "trigger references unknown script")

    def _validate_step(self, sequence: ScriptSequence, index: int, step) -> None:
        script_id = sequence.script_id
        character = getattr(step, "character", None)
        if character is not None:
            self._check_reference(script_id, index, "character", character, CHARACTER_IDS)
        emotion = getattr(step, "emotion", None)
        if emotion is not None:
            self._check_reference(script_id, index, "emotion", emotion, ALLOWED_EMOTIONS)
        animation = getattr(step, "animation", None)
        if animation is not None:
            self._check_reference(script_id, index, "animation", animation, ALLOWED_ANIMATIONS)
        slot = getattr(step, "slot", None)
        if slot is not None:
            self._check_reference(script_id, index, "slot", slot, SCRIPT_SLOTS)
        if isinstance(step, ScriptDialogueStep):
            self._check_reference(script_id, index, "node", step.node, self._dialogue_nodes)
        if isinstance(step, NarrativeGateStep):
            self._check_reference(script_id, index, "condition", step.condition, CONDITION_REGISTRY)
        if isinstance(step, PresentationStep):
            self._check_reference(script_id, index, "action", step.action, PRESENTATION_ACTIONS)
        if isinstance(step, UnlockStep):
            self._check_reference(script_id, index, "target", step.target, UNLOCK_TARGETS)
        if isinstance(step, PhaseTransitionStep):
            self._check_reference(script_id, index, "to", step.to, PHASE_TARGETS)

    @staticmethod
    def _check_reference(script_id: str, index: int, field: str, value: str, allowed) -> None:
        if value not in allowed:
            raise ScriptLoadError(
                script_id, index, f"unknown {field} {value!r}"
            )

    def get(self, script_id: str) -> ScriptSequence:
        try:
            return self._sequences[script_id]
        except KeyError:
            raise ScriptLoadError(script_id, -1, "unknown script") from None

    def dialogue(self, node_id: str) -> DialogueNode:
        try:
            return self._dialogue_nodes[node_id]
        except KeyError:
            raise ScriptLoadError(node_id, -1, "unknown dialogue node") from None

    def triggers(self) -> list[tuple[str, str]]:
        return list(self._triggers)
