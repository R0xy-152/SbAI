"""Per-session Narrative State service (docs/03 §5).

The Game Orchestrator coordinates one player turn; it no longer owns the
per-session NarrativeState map itself. This service owns that map: each
session's state is fully isolated, created on first use, and seeded back from a
persisted snapshot on Session Restore (docs/02 §21). Only the Narrative Engine
commits to these states (docs/03 §28-29); this service is a plain container,
not a gate.
"""

from __future__ import annotations

from app.narrative.state import NarrativeState


class StateService:
    """Owns the per-session NarrativeState (docs/03 §5)."""

    def __init__(self) -> None:
        self._states: dict[str, NarrativeState] = {}

    def state_for(self, session_id: str) -> NarrativeState:
        """The session's state, created on first use."""
        state = self._states.get(session_id)
        if state is None:
            state = NarrativeState()
            self._states[session_id] = state
        return state

    def get(self, session_id: str) -> NarrativeState | None:
        """Non-mutating lookup (snapshot building needs it)."""
        return self._states.get(session_id)

    def restore(self, session_id: str, state: NarrativeState) -> None:
        """Seed a persisted state (TV-14 Session Restore)."""
        self._states[session_id] = state

    def is_empty(self) -> bool:
        return not self._states

    def __contains__(self, session_id: str) -> bool:
        return session_id in self._states
