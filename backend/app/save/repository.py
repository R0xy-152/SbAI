"""GameSave entity + SaveRepository (docs/13 §16, §20).

The Save entity is a *record*: it carries the slot metadata and the opaque
snapshot JSON, but never invents game state — the snapshot is produced by the
orchestrator's authoritative state (docs/13 §14.2). Slot semantics (docs/13
§16.1): at most one AUTO per player and one MANUAL save per slot_index 1..6;
overwriting a slot updates it instead of creating duplicates.

Two backends implement the same interface:

- ``JsonSaveRepository`` — the TV-14-style durable JSON fixture (docs/06 §10),
  used when PostgreSQL is not configured. Each save is one file, written
  atomically (tmp + os.replace), so a crash never leaves a half-written save
  (docs/13 §18: Capture must be all-or-nothing).
- ``PostgresSaveRepository`` — the docs/13 §16 target: ``snapshot`` is a JSONB
  column, slot uniqueness is enforced by partial unique indexes, and an upsert
  is a single transaction (docs/13 §18.1).
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AUTO = "AUTO"
MANUAL = "MANUAL"
MANUAL_SLOTS = 6

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS game_saves (
    id                 TEXT PRIMARY KEY,
    player_id          TEXT NOT NULL,
    slot_type          TEXT NOT NULL CHECK (slot_type IN ('AUTO','MANUAL')),
    slot_index         INTEGER,
    title              TEXT,
    source_session_id  TEXT,
    schema_version     INTEGER NOT NULL,
    snapshot           JSONB NOT NULL,
    chapter_id         TEXT,
    phase              TEXT,
    created_at         TEXT,
    updated_at         TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_game_saves_auto
    ON game_saves (player_id) WHERE slot_type = 'AUTO';
CREATE UNIQUE INDEX IF NOT EXISTS uq_game_saves_manual
    ON game_saves (player_id, slot_index) WHERE slot_type = 'MANUAL';
"""


@dataclass
class GameSave:
    """One save slot record (docs/13 §16). ``snapshot`` is the opaque capture;
    it is never shipped to the Frontend (docs/13 §29)."""

    id: str
    player_id: str
    slot_type: str
    slot_index: int | None
    title: str | None
    source_session_id: str | None
    schema_version: int
    snapshot: dict
    chapter_id: str | None
    phase: str | None
    created_at: str
    updated_at: str

    def info(self) -> dict:
        """The slot metadata the Frontend may see (docs/13 §20.1) — no snapshot."""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "slot_type": self.slot_type,
            "slot_index": self.slot_index,
            "title": self.title,
            "source_session_id": self.source_session_id,
            "chapter_id": self.chapter_id,
            "phase": self.phase,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SaveRepository(ABC):
    """Read/write save slots for one anonymous player (docs/13 §16, §20)."""

    @abstractmethod
    def upsert(self, save: GameSave) -> None:
        """Create or overwrite the slot this save occupies (docs/13 §16.1)."""

    @abstractmethod
    def get_by_id(self, save_id: str) -> GameSave | None:
        """The save with this id, or None."""

    @abstractmethod
    def list_by_player(self, player_id: str) -> list[GameSave]:
        """All saves owned by one player, newest-updated first."""

    @abstractmethod
    def get_slot(
        self, player_id: str, slot_type: str, slot_index: int | None
    ) -> GameSave | None:
        """The save currently occupying a slot, or None (docs/13 §20.1)."""

    @abstractmethod
    def delete_slot(
        self, player_id: str, slot_type: str, slot_index: int | None
    ) -> bool:
        """Delete the slot; True if a save was removed (docs/13 §26.3)."""


def new_save_id() -> str:
    return uuid.uuid4().hex


# T2review P1-2：player_id / save_id 是后端命名空间键，不是自由文件路径。
_PLAYER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# save_id 同样只允许不透明字符集：不含路径分隔符/点号即不可能穿越。
_SAVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _check_player_id(player_id: str) -> str:
    if not isinstance(player_id, str) or not _PLAYER_ID_RE.fullmatch(player_id):
        raise ValueError("invalid player_id")
    return player_id


def _check_save_id(save_id: str) -> str:
    if not isinstance(save_id, str) or not _SAVE_ID_RE.fullmatch(save_id):
        raise ValueError("invalid save_id")
    return save_id


class JsonSaveRepository(SaveRepository):
    """Durable JSON-file fixture behind SaveRepository (docs/13 Task 6 local
    path, mirroring JsonSessionRepository; PostgreSQL is the target backend).

    One file per save under ``<data_dir>/<player_id>/<save_id>.json``, written
    atomically so Capture is all-or-nothing (docs/13 §18). Slot lookups scan
    the player's directory — at most 7 saves per player, so this is bounded.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)

    def _player_dir(self, player_id: str) -> Path:
        return self._data_dir / _check_player_id(player_id)

    def _path(self, player_id: str, save_id: str) -> Path:
        path = self._player_dir(player_id) / f"{_check_save_id(save_id)}.json"
        # 二次防护（T2review P1-2）：resolve 后目标必须仍在存档根内
        root = self._data_dir.resolve()
        if root not in path.resolve().parents:
            raise ValueError("save path escapes the save root")
        return path

    def upsert(self, save: GameSave) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(save.player_id, save.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(_save_to_dict(save), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, path)

    def get_by_id(self, save_id: str) -> GameSave | None:
        # Saves are namespaced by player; a bare id needs a scan across players.
        if not self._data_dir.is_dir():
            return None
        for player_dir in self._data_dir.iterdir():
            if not player_dir.is_dir():
                continue
            try:
                path = self._path(player_dir.name, save_id)
            except ValueError:
                continue
            if path.exists():
                return self._read(path)
        return None

    def list_by_player(self, player_id: str) -> list[GameSave]:
        player_dir = self._player_dir(player_id)
        if not player_dir.is_dir():
            return []
        saves = []
        for path in sorted(player_dir.glob("*.json")):
            save = self._read(path)
            if save is not None:
                saves.append(save)
        saves.sort(key=lambda s: s.updated_at, reverse=True)
        return saves

    def get_slot(
        self, player_id: str, slot_type: str, slot_index: int | None
    ) -> GameSave | None:
        for save in self.list_by_player(player_id):
            if save.slot_type == slot_type and save.slot_index == slot_index:
                return save
        return None

    def delete_slot(
        self, player_id: str, slot_type: str, slot_index: int | None
    ) -> bool:
        for save in self.list_by_player(player_id):
            if save.slot_type == slot_type and save.slot_index == slot_index:
                try:
                    self._path(player_id, save.id).unlink()
                except FileNotFoundError:
                    pass
                return True
        return False

    def _read(self, path: Path) -> GameSave | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return _save_from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            # A corrupt/partial file is treated as no save — never a crash and
            # never a half-restored game (docs/13 §18).
            return None


class PostgresSaveRepository(SaveRepository):
    """PostgreSQL JSONB save store (docs/13 §16 target).

    Schema and slot uniqueness live in the database (docs/13 §16.1). The table
    is created idempotently on first use so the backend can start before the
    database is ready. Every upsert is one transaction (docs/13 §18.1): a
    failed capture leaves the previous slot content untouched.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._lock = threading.Lock()
        self._initialized = False

    def _ensure_schema(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            import psycopg  # imported lazily so JSON fallback needs no driver

            with psycopg.connect(self._dsn) as conn:
                conn.execute(SCHEMA_SQL)
            self._initialized = True

    def _conn(self):
        import psycopg

        self._ensure_schema()
        return psycopg.connect(self._dsn)

    def upsert(self, save: GameSave) -> None:
        # Partial unique indexes need the matching conflict target per slot
        # type (docs/13 §16.1). AUTO conflicts on (player_id) with its partial
        # WHERE; MANUAL on (player_id, slot_index) with its partial WHERE. The
        # index predicate is a clause after the column list, not inside it.
        if save.slot_type == AUTO:
            conflict = "ON CONFLICT (player_id) WHERE slot_type = 'AUTO'"
        else:
            conflict = (
                "ON CONFLICT (player_id, slot_index) WHERE slot_type = 'MANUAL'"
            )
        sql = f"""
            INSERT INTO game_saves (
                id, player_id, slot_type, slot_index, title, source_session_id,
                schema_version, snapshot, chapter_id, phase, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            {conflict} DO UPDATE SET
                id = EXCLUDED.id,
                title = EXCLUDED.title,
                source_session_id = EXCLUDED.source_session_id,
                schema_version = EXCLUDED.schema_version,
                snapshot = EXCLUDED.snapshot,
                chapter_id = EXCLUDED.chapter_id,
                phase = EXCLUDED.phase,
                updated_at = EXCLUDED.updated_at
        """
        with self._conn() as conn:
            conn.execute(
                sql,
                (
                    save.id,
                    save.player_id,
                    save.slot_type,
                    save.slot_index,
                    save.title,
                    save.source_session_id,
                    save.schema_version,
                    json.dumps(save.snapshot),
                    save.chapter_id,
                    save.phase,
                    save.created_at,
                    save.updated_at,
                ),
            )

    def get_by_id(self, save_id: str) -> GameSave | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM game_saves WHERE id = %s", (save_id,)
            ).fetchone()
        return _save_from_row(row) if row is not None else None

    def list_by_player(self, player_id: str) -> list[GameSave]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM game_saves WHERE player_id = %s"
                " ORDER BY updated_at DESC",
                (player_id,),
            ).fetchall()
        return [_save_from_row(row) for row in rows]

    def get_slot(
        self, player_id: str, slot_type: str, slot_index: int | None
    ) -> GameSave | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM game_saves WHERE player_id = %s AND slot_type = %s"
                " AND slot_index IS NOT DISTINCT FROM %s",
                (player_id, slot_type, slot_index),
            ).fetchone()
        return _save_from_row(row) if row is not None else None

    def delete_slot(
        self, player_id: str, slot_type: str, slot_index: int | None
    ) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM game_saves WHERE player_id = %s AND slot_type = %s"
                " AND slot_index IS NOT DISTINCT FROM %s",
                (player_id, slot_type, slot_index),
            )
        return cur.rowcount > 0


def _save_to_dict(save: GameSave) -> dict:
    return {
        "id": save.id,
        "player_id": save.player_id,
        "slot_type": save.slot_type,
        "slot_index": save.slot_index,
        "title": save.title,
        "source_session_id": save.source_session_id,
        "schema_version": save.schema_version,
        "snapshot": save.snapshot,
        "chapter_id": save.chapter_id,
        "phase": save.phase,
        "created_at": save.created_at,
        "updated_at": save.updated_at,
    }


def _save_from_dict(data: dict) -> GameSave:
    return GameSave(
        id=data["id"],
        player_id=data["player_id"],
        slot_type=data["slot_type"],
        slot_index=data["slot_index"],
        title=data["title"],
        source_session_id=data["source_session_id"],
        schema_version=data["schema_version"],
        snapshot=data["snapshot"],
        chapter_id=data["chapter_id"],
        phase=data["phase"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _save_from_row(row: Any) -> GameSave:
    # psycopg row: id, player_id, slot_type, slot_index, title, source_session_id,
    # schema_version, snapshot, chapter_id, phase, created_at, updated_at
    # psycopg3 returns JSONB columns already deserialized (dict), not a string.
    return GameSave(
        id=row[0],
        player_id=row[1],
        slot_type=row[2],
        slot_index=row[3],
        title=row[4],
        source_session_id=row[5],
        schema_version=row[6],
        snapshot=row[7],
        chapter_id=row[8],
        phase=row[9],
        created_at=row[10],
        updated_at=row[11],
    )
