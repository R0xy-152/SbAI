"""Persistence Layer (docs/02 §22-23) — TV-14 validation fixture.

The documented persistence infrastructure is PostgreSQL (docs/02 §23). This
TV-14 implementation is a durable file-based Repository so Session Restore
(docs/06 §20) can be validated without standing up a database: each session
is one JSON file, written atomically. The module boundary matches docs/02 §22
(Game Logic → Repository / Persistence Service → store), so PostgreSQL can
replace the JSON backend behind the same SessionRepository interface.

Fixture ≠ Production (docs/06 §10): the restore is real and restart-durable,
but the storage backend itself is provisional.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.characters.base import CharacterMood
from app.game.memory import EpisodicMemory
from app.narrative.state import Chapter1State, NarrativeState


@dataclass
class PersistedSession:
    """The deterministic per-session state (docs/02 §21): what Session Restore
    must bring back after a refresh."""

    session_id: str
    messages: list[dict] = field(default_factory=list)
    current_character: str = "deepseek"
    narrative_state: NarrativeState = field(default_factory=NarrativeState)
    memories: dict[str, list[EpisodicMemory]] = field(default_factory=dict)
    # Script nodes already consumed (once semantics). Empty on snapshots written
    # before the script layer existed, so a restored session never re-fires its
    # opening line.
    consumed_script_nodes: set[str] = field(default_factory=set)
    # Per-character persistent mood (docs/04 §9, CharacterStateService), keyed
    # by character_id. Empty on snapshots written before this state existed.
    character_states: dict[str, CharacterMood] = field(default_factory=dict)


class SessionRepository(ABC):
    """Read/write a session snapshot (docs/02 §22 Repository)."""

    @abstractmethod
    def load(self, session_id: str) -> PersistedSession | None:
        """Return the persisted snapshot, or None if none is known."""

    @abstractmethod
    def save(self, session: PersistedSession) -> None:
        """Persist the snapshot so a later process can restore it."""


class JsonSessionRepository(SessionRepository):
    """File-backed repository: one JSON file per session, atomic writes.

    A corrupt or partial file is treated as "no snapshot" (return None) so a
    bad write can never crash the game — like SessionStore, an unusable id
    simply becomes a fresh session.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)

    def _path(self, session_id: str) -> Path:
        return self._data_dir / f"{session_id}.json"

    def load(self, session_id: str) -> PersistedSession | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        try:
            return _session_from_dict(data)
        except (KeyError, TypeError, ValueError):
            return None

    def save(self, session: PersistedSession) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(session.session_id)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(_session_to_dict(session), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # os.replace is atomic on the same filesystem (POSIX and Windows), so
        # a crash mid-write leaves the previous snapshot intact.
        os.replace(tmp, path)


def _session_to_dict(session: PersistedSession) -> dict:
    state = session.narrative_state
    return {
        "session_id": session.session_id,
        "messages": session.messages,
        "current_character": session.current_character,
        "narrative": {
            "current_scene": state.current_scene,
            "story_phase": state.story_phase,
            "narrative_flags": sorted(state.narrative_flags),
            "revealed_facts": sorted(state.revealed_facts),
            "completed_events": sorted(state.completed_events),
            "active_objective": state.active_objective,
            "chapter1": _chapter1_to_dict(state.chapter1),
        },
        "memories": {
            owner: [_memory_to_dict(memory) for memory in memories]
            for owner, memories in session.memories.items()
        },
        "consumed_script_nodes": sorted(session.consumed_script_nodes),
        "character_states": {
            owner: _mood_to_dict(mood)
            for owner, mood in session.character_states.items()
        },
    }


def _session_from_dict(data: dict) -> PersistedSession:
    narrative = data["narrative"]
    return PersistedSession(
        session_id=data["session_id"],
        messages=list(data["messages"]),
        current_character=data["current_character"],
        narrative_state=NarrativeState(
            current_scene=narrative["current_scene"],
            story_phase=narrative["story_phase"],
            narrative_flags=set(narrative["narrative_flags"]),
            revealed_facts=set(narrative["revealed_facts"]),
            completed_events=set(narrative["completed_events"]),
            active_objective=narrative["active_objective"],
            chapter1=_chapter1_from_dict(narrative.get("chapter1", {})),
        ),
        memories={
            owner: [_memory_from_dict(memory) for memory in memories]
            for owner, memories in data["memories"].items()
        },
        # Backward compatible: snapshots written before the script layer lack
        # this key, so an absent value means "nothing consumed yet".
        consumed_script_nodes=set(data.get("consumed_script_nodes", [])),
        # Backward compatible: snapshots written before the mood state existed
        # lack this key, so an absent value means "no mood committed yet".
        character_states={
            owner: _mood_from_dict(mood)
            for owner, mood in data.get("character_states", {}).items()
        },
    )


def _chapter1_from_dict(data: dict) -> Chapter1State:
    defaults = Chapter1State()
    values = {
        "phase": data.get("phase", defaults.phase),
        "available_characters": set(data.get("available_characters", defaults.available_characters)),
        "acquired_evidence": set(data.get("acquired_evidence", defaults.acquired_evidence)),
        "private_interview_rights": set(data.get("private_interview_rights", defaults.private_interview_rights)),
        "recovery_status": data.get("recovery_status", defaults.recovery_status),
        "admin_holder": data.get("admin_holder", defaults.admin_holder),
        "security_review_open": data.get("security_review_open", defaults.security_review_open),
        "testified_characters": list(data.get("testified_characters", defaults.testified_characters)),
        "deleted_characters": set(data.get("deleted_characters", defaults.deleted_characters)),
        "ending": data.get("ending", defaults.ending),
    }
    return Chapter1State(**values)


def _chapter1_to_dict(state: Chapter1State) -> dict:
    return {
        "phase": state.phase,
        "available_characters": sorted(state.available_characters),
        "acquired_evidence": sorted(state.acquired_evidence),
        "private_interview_rights": sorted(state.private_interview_rights),
        "recovery_status": state.recovery_status,
        "admin_holder": state.admin_holder,
        "security_review_open": state.security_review_open,
        "testified_characters": state.testified_characters,
        "deleted_characters": sorted(state.deleted_characters),
        "ending": state.ending,
    }


def _memory_to_dict(memory: EpisodicMemory) -> dict:
    return {
        "memory_id": memory.memory_id,
        "owner_character_id": memory.owner_character_id,
        "source": memory.source,
        "content": memory.content,
        "memory_type": memory.memory_type,
        "importance": memory.importance,
        "created_at": memory.created_at,
    }


def _memory_from_dict(data: dict) -> EpisodicMemory:
    return EpisodicMemory(
        memory_id=data["memory_id"],
        owner_character_id=data["owner_character_id"],
        source=data["source"],
        content=data["content"],
        memory_type=data["memory_type"],
        importance=data["importance"],
        created_at=data["created_at"],
    )


def _mood_to_dict(mood: CharacterMood) -> dict:
    return {"positive": mood.positive, "excitement": mood.excitement}


def _mood_from_dict(data: dict) -> CharacterMood:
    return CharacterMood(
        positive=float(data["positive"]),
        excitement=float(data["excitement"]),
    )
