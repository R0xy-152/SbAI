"""In-memory session store for TV-03.

TV-03 only needs a mock chat round trip with correct session association.
This store is deliberately NOT persistent: a backend restart loses sessions.
Persistence (TV-14 Session Restore) will replace it with a real store.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field


@dataclass
class GameSession:
    """A single game session and its message log."""

    session_id: str
    messages: list[dict] = field(default_factory=list)

    def player_turn_count(self) -> int:
        return sum(1 for message in self.messages if message["role"] == "player")


class SessionStore:
    """Minimal in-memory session store (TV-03 fixture, not persistent)."""

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str | None) -> GameSession:
        """Return the existing session, or create a fresh one.

        An unknown/expired client-supplied id is never trusted: a new session
        with a freshly generated id is created instead, so a stale client can
        always recover.
        """
        with self._lock:
            if session_id is not None and session_id in self._sessions:
                return self._sessions[session_id]
            new_id = uuid.uuid4().hex
            session = GameSession(session_id=new_id)
            self._sessions[new_id] = session
            return session

    def append_message(self, session_id: str, message: dict) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"unknown session: {session_id}")
            session.messages.append(message)
