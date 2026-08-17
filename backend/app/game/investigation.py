"""Deterministic scene investigation runtime (docs/01)."""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.state import NarrativeState

INSPECT_HOTSPOT = "INSPECT_HOTSPOT"
PAPER_RUBBING_COMPLETE = "PAPER_RUBBING_COMPLETE"

CH1_NOTE_01 = "CH1_NOTE_01"
CH1_TERMINAL_MAIN = "CH1_TERMINAL_MAIN"
CH1_C02_DOOR = "CH1_C02_DOOR"
CH1_CHARACTER_REGISTRY = "CH1_CHARACTER_REGISTRY"


@dataclass(frozen=True)
class HotspotDefinition:
    hotspot_id: str
    scene_id: str
    interaction_type: str
    evidence_on_complete: str | None = None
    evidence_on_inspect: str | None = None
    scene_fact_on_inspect: str | None = None
    requires_character: str | None = None


HOTSPOTS = {
    CH1_NOTE_01: HotspotDefinition(
        CH1_NOTE_01, "ROOM_A", "paper_rubbing", evidence_on_complete="EV01_NOTE_V03"
    ),
    CH1_TERMINAL_MAIN: HotspotDefinition(
        CH1_TERMINAL_MAIN,
        "ROOM_A",
        "inspect",
        evidence_on_inspect="EV02_ADMIN_SESSION_0317",
        scene_fact_on_inspect="TERMINAL_MAIN_INSPECTED",
        requires_character="claude",
    ),
    CH1_C02_DOOR: HotspotDefinition(
        CH1_C02_DOOR,
        "ROOM_A",
        "inspect",
        evidence_on_inspect="EV03_C02_RELEASE",
        scene_fact_on_inspect="C02_DOOR_INSPECTED",
        requires_character="claude",
    ),
    CH1_CHARACTER_REGISTRY: HotspotDefinition(
        CH1_CHARACTER_REGISTRY,
        "ROOM_A",
        "inspect",
        evidence_on_inspect="EV04_CURRENT_DEEPSEEK_REGISTRY",
        scene_fact_on_inspect="CHARACTER_REGISTRY_INSPECTED",
        requires_character="claude",
    ),
}


@dataclass(frozen=True)
class InvestigationResult:
    action: str
    hotspot_id: str
    outcome: str
    evidence_id: str | None = None


class InvestigationRuntime:
    """Own hotspot state; the frontend may request actions, never outcomes."""

    def apply(self, state: NarrativeState, action: str, hotspot_id: str) -> InvestigationResult:
        hotspot = HOTSPOTS.get(hotspot_id)
        if hotspot is None:
            raise ValueError(f"unknown hotspot: {hotspot_id}")
        if state.current_scene != hotspot.scene_id:
            raise ValueError("hotspot is not available in the current scene")
        if (
            hotspot.requires_character is not None
            and hotspot.requires_character not in state.chapter1.available_characters
        ):
            raise ValueError("hotspot is not available before the 03:17 incident")

        current = state.chapter1.hotspot_states.get(hotspot_id, "hidden")
        if action == INSPECT_HOTSPOT:
            if current == "completed":
                return InvestigationResult(action, hotspot_id, "ALREADY_COMPLETED")
            evidence_id = hotspot.evidence_on_inspect
            state.chapter1.hotspot_states[hotspot_id] = (
                "completed" if evidence_id is not None else "investigated"
            )
            if hotspot.scene_fact_on_inspect is not None:
                state.chapter1.scene_facts.add(hotspot.scene_fact_on_inspect)
            if evidence_id is not None:
                state.chapter1.acquired_evidence.add(evidence_id)
                return InvestigationResult(action, hotspot_id, "COMPLETED", evidence_id)
            return InvestigationResult(action, hotspot_id, "INVESTIGATED")

        if action == PAPER_RUBBING_COMPLETE:
            if hotspot.interaction_type != "paper_rubbing":
                raise ValueError("hotspot does not support paper rubbing")
            if current not in {"investigated", "completed"}:
                raise ValueError("hotspot must be investigated before completion")
            if current == "completed":
                return InvestigationResult(
                    action, hotspot_id, "ALREADY_COMPLETED", hotspot.evidence_on_complete
                )
            state.chapter1.hotspot_states[hotspot_id] = "completed"
            evidence_id = hotspot.evidence_on_complete
            if evidence_id is not None:
                state.chapter1.acquired_evidence.add(evidence_id)
            state.chapter1.scene_facts.add("NOTE_V03_RUBBED")
            return InvestigationResult(action, hotspot_id, "COMPLETED", evidence_id)

        raise ValueError(f"unknown investigation action: {action}")
