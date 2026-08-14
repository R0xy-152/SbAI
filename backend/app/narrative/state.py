"""Narrative State (docs/03 §5).

The deterministic game state the Narrative Runtime owns. The Interpreter and
Character Runtimes only read it; only the Event engine may change it (State
Commit, docs/03 §28-29). Minimal for the current TVs: scene, phase, flags,
completed events. Facts and objectives are added as the plot grows.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NarrativeState:
    current_scene: str = "binding_room"
    story_phase: str = "prologue"
    narrative_flags: set[str] = field(default_factory=set)
    revealed_facts: set[str] = field(default_factory=set)
    completed_events: set[str] = field(default_factory=set)
    active_objective: str | None = None
