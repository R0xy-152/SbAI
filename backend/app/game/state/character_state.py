"""Per-session, per-character Character State (docs/04 §9).

The first concrete character state is the two-axis mood (positive/excitement,
see ``CharacterMood``). This service owns that map, mirroring ``StateService``
(the narrative-state container): each session's character moods are fully
isolated, created on first use, and seeded back from a persisted snapshot on
Session Restore (docs/02 §21). Only the Game Orchestrator reads/commits these;
the LLM never mutates state directly — its ``mood`` output is a *proposal* that
lands only after the reply passes validation (Validate-Before-Commit).
"""

from __future__ import annotations

from app.characters.base import CharacterMood


class CharacterStateService:
    """Owns the per-session per-character mood (docs/04 §9)."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, CharacterMood]] = {}

    def mood_for(self, session_id: str, character_id: str) -> CharacterMood | None:
        """The character's committed mood, or None if none has been committed
        yet — so the prompt stays clean on the very first turn and only carries
        a mood line once there is actual emotional state to convey."""
        return self._states.get(session_id, {}).get(character_id)

    def commit_mood(
        self, session_id: str, character_id: str, mood: CharacterMood
    ) -> None:
        """Store the character's updated mood. The orchestrator calls this only
        after the reply passes validation (docs/04 §51), so a rejected reply
        never changes the character's state."""
        self._states.setdefault(session_id, {})[character_id] = mood

    def snapshot(self, session_id: str) -> dict[str, CharacterMood]:
        """The per-character moods to persist (docs/02 §21)."""
        return dict(self._states.get(session_id, {}))

    def restore(self, session_id: str, states: dict[str, CharacterMood]) -> None:
        """Seed persisted moods (TV-14 Session Restore)."""
        self._states[session_id] = dict(states)
