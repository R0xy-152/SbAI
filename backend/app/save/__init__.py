"""Save Snapshot layer (docs/13 §14-21, Task 6).

GameSave / SaveRepository / SaveSnapshotService: the deterministic Save
backed by the authoritative runtime state, never by the Frontend. Two storage
backends behind the SaveRepository interface — JSON files (the TV-14-style
local fixture, used when no PostgreSQL is configured) and PostgreSQL (the
docs/13 §16 target: snapshot = JSONB). Save Capture is backend-authoritative
(docs/13 §14.2); Load creates a fresh Active Session (docs/13 §19.1).
"""

from app.save.repository import (
    AUTO,
    MANUAL,
    GameSave,
    JsonSaveRepository,
    PostgresSaveRepository,
    SaveRepository,
)
from app.save.service import (
    SCHEMA_VERSION,
    SaveLoadError,
    SaveSchemaError,
    SaveSnapshotService,
)

__all__ = [
    "AUTO",
    "MANUAL",
    "GameSave",
    "JsonSaveRepository",
    "PostgresSaveRepository",
    "SaveRepository",
    "SaveSnapshotService",
    "SaveLoadError",
    "SaveSchemaError",
    "SCHEMA_VERSION",
]
