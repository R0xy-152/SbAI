"""Per-session, per-character Character State (docs/04 §9).

The first concrete character state was the two-axis mood (see CharacterMood);
it has grown into CharacterState — mood plus the character's own last_reasoning
from the previous turn, fed back so its train of thought stays continuous
("逻辑链拷打" continuity). This service owns that map, mirroring StateService
(the narrative-state container): each session's character states are fully
isolated, created on first use, and seeded back from a persisted snapshot on
Session Restore (docs/02 §21). Only the Game Orchestrator reads/commits these;
the LLM never mutates state directly — its mood / reasoning output is a
*proposal* that lands only after the reply passes validation
(Validate-Before-Commit).
"""

from __future__ import annotations

from app.characters.base import CharacterMood, CharacterState


class CharacterStateService:
    """Owns the per-session per-character state (docs/04 §9)."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, CharacterState]] = {}

    def _ensure_state(self, session_id: str, character_id: str) -> CharacterState:
        states = self._states.setdefault(session_id, {})
        state = states.get(character_id)
        if state is None:
            state = CharacterState()
            states[character_id] = state
        return state

    def state_for(
        self, session_id: str, character_id: str
    ) -> CharacterState | None:
        """The character's committed state, or None if none has been committed
        yet — so the prompt stays clean on the very first turn and only carries
        a state line once there is actual state to convey."""
        return self._states.get(session_id, {}).get(character_id)

    def mood_for(self, session_id: str, character_id: str) -> CharacterMood | None:
        """The character's committed mood, or None if no state exists yet."""
        state = self.state_for(session_id, character_id)
        return state.mood if state is not None else None

    def reasoning_for(self, session_id: str, character_id: str) -> str:
        """The character's last committed reasoning, or "" if none yet."""
        state = self.state_for(session_id, character_id)
        return state.last_reasoning if state is not None else ""

    def commit_mood(
        self, session_id: str, character_id: str, mood: CharacterMood
    ) -> None:
        """Store the character's updated mood. The orchestrator calls this only
        after the reply passes validation (docs/04 §51), so a rejected reply
        never changes the character's state."""
        self._ensure_state(session_id, character_id).mood = mood

    def commit_reasoning(
        self, session_id: str, character_id: str, reasoning: str
    ) -> None:
        """Store the character's reasoning for the next turn's continuity.
        Empty reasoning is ignored so a missing reason keeps the previous one."""
        if reasoning:
            self._ensure_state(session_id, character_id).last_reasoning = reasoning

    def snapshot(self, session_id: str) -> dict[str, CharacterState]:
        """The per-character states to persist (docs/02 §21)."""
        return dict(self._states.get(session_id, {}))

    def restore(self, session_id: str, states: dict[str, CharacterState]) -> None:
        """Seed persisted states (TV-14 Session Restore)."""
        self._states[session_id] = dict(states)
