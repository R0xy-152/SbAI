"""Narrative State (docs/03 §5).

The deterministic game state the Narrative Runtime owns. The Interpreter and
Character Runtimes only read it; only the Event engine may change it (State
Commit, docs/03 §28-29). Minimal for the current TVs: scene, phase, flags,
completed events. Facts and objectives are added as the plot grows.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chapter1State:
    """Authoritative state for the new chapter-one deterministic skeleton.

    This is deliberately a chapter outline, not an implementation of the
    later investigation, evidence, interview, or recovery subsystems. Those
    systems will replace the corresponding script actions in later phases.
    """

    phase: str = "opening"
    available_characters: set[str] = field(default_factory=set)
    acquired_evidence: set[str] = field(default_factory=set)
    presented_evidence: dict[str, set[str]] = field(default_factory=dict)
    evidence_selections: list[dict] = field(default_factory=list)
    doubao_statements: list[dict] = field(default_factory=list)
    resolved_contradictions: set[str] = field(default_factory=set)
    accepted_inferences: set[str] = field(default_factory=set)
    claim_store: dict[str, dict] = field(default_factory=dict)
    hotspot_states: dict[str, str] = field(default_factory=dict)
    scene_facts: set[str] = field(default_factory=set)
    private_interview_rights: set[str] = field(default_factory=set)
    recovery_status: str = "not_started"
    admin_holder: str | None = None
    security_review_open: bool = False
    testified_characters: list[str] = field(default_factory=list)
    deleted_characters: set[str] = field(default_factory=set)
    ending: str | None = None


@dataclass
class NarrativeState:
    current_scene: str = "binding_room"
    story_phase: str = "prologue"
    narrative_flags: set[str] = field(default_factory=set)
    revealed_facts: set[str] = field(default_factory=set)
    completed_events: set[str] = field(default_factory=set)
    active_objective: str | None = None
    chapter1: Chapter1State = field(default_factory=Chapter1State)
