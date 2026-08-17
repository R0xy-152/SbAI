"""Deterministic scene investigation runtime (docs/01)."""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.state import NarrativeState

INSPECT_HOTSPOT = "INSPECT_HOTSPOT"
PAPER_RUBBING_COMPLETE = "PAPER_RUBBING_COMPLETE"

CH1_NOTE_01 = "CH1_NOTE_01"
CH1_TERMINAL_MAIN = "CH1_TERMINAL_MAIN"
CH1_CLAUDE_AREA = "CH1_CLAUDE_AREA"


@dataclass(frozen=True)
class HotspotDefinition:
    hotspot_id: str
    scene_id: str
    interaction_type: str
    evidence_on_complete: str | None = None
    scene_fact_on_inspect: str | None = None


HOTSPOTS = {
    CH1_NOTE_01: HotspotDefinition(
        CH1_NOTE_01, "ROOM_A", "paper_rubbing", evidence_on_complete="EV_NOTE_V03"
    ),
    CH1_TERMINAL_MAIN: HotspotDefinition(
        CH1_TERMINAL_MAIN, "ROOM_A", "inspect", scene_fact_on_inspect="TERMINAL_MAIN_INSPECTED"
    ),
    CH1_CLAUDE_AREA: HotspotDefinition(
        CH1_CLAUDE_AREA, "ROOM_A", "inspect", scene_fact_on_inspect="CLAUDE_AREA_INSPECTED"
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

        current = state.chapter1.hotspot_states.get(hotspot_id, "hidden")
        if action == INSPECT_HOTSPOT:
            if current == "completed":
                return InvestigationResult(action, hotspot_id, "ALREADY_COMPLETED")
            state.chapter1.hotspot_states[hotspot_id] = "investigated"
            if hotspot.scene_fact_on_inspect is not None:
                state.chapter1.scene_facts.add(hotspot.scene_fact_on_inspect)
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
