"""TV-11 POC fixture events (docs/06 §17).

Fixture ≠ production plot content (docs/06 §10): this is a validation fixture
that demonstrates the deterministic Event machinery — a Signal only changes
State through an Event. It is not real story.
"""

from __future__ import annotations

from app.narrative import signals
from app.narrative.events import Effect, NarrativeEvent, SET_FLAG, ONCE

EV_POC_CLAUDE_APPEARS = "EV_POC_CLAUDE_APPEARS"


def build_poc_events() -> list[NarrativeEvent]:
    """The single binding-room fixture: asking who trapped them makes Claude
    appear once, exactly once (docs/06 §17)."""
    return [
        NarrativeEvent(
            event_id=EV_POC_CLAUDE_APPEARS,
            trigger_signals=frozenset({signals.SIG_ASK_CAPTOR}),
            scene="binding_room",
            story_phase="prologue",
            requirement=lambda state: "claude_has_appeared" not in state.narrative_flags,
            effects=(Effect(SET_FLAG, "claude_has_appeared"),),
            presentation=("SHOW_CHARACTER", "claude"),
            repeat_policy=ONCE,
        ),
    ]
