"""GameSave repository tests (docs/13 §16, §20, §26.3).

Both backends behind SaveRepository — the JSON file fixture (always runs) and
PostgreSQL JSONB (runs when GAL_POSTGRES_DSN is reachable, e.g. under
`docker compose up -d postgres`) — must satisfy the same slot semantics:

- at most one AUTO and one MANUAL per slot_index per player (§16.1);
- overwriting a slot updates it instead of duplicating;
- list returns only the queried player's saves, newest-updated first;
- delete removes exactly one slot.
"""

from __future__ import annotations

import os

import pytest

from app.save.repository import (
    AUTO,
    MANUAL,
    GameSave,
    JsonSaveRepository,
    PostgresSaveRepository,
    SaveRepository,
)

POSTGRES_DSN = os.environ.get("GAL_TEST_POSTGRES_DSN")


def _make_save(player_id: str, slot_type: str, slot_index: int | None, save_id: str | None = None, **kw) -> GameSave:
    return GameSave(
        id=save_id or f"save-{player_id}-{slot_type}-{slot_index}",
        player_id=player_id,
        slot_type=slot_type,
        slot_index=slot_index,
        title=kw.get("title", "t"),
        source_session_id=kw.get("source_session_id", "src"),
        schema_version=kw.get("schema_version", 1),
        snapshot=kw.get("snapshot", {"schema_version": 1, "narrative": {}}),
        chapter_id=kw.get("chapter_id", "ch1"),
        phase=kw.get("phase", "investigation"),
        created_at=kw.get("created_at", "2026-08-19T00:00:00+00:00"),
        updated_at=kw.get("updated_at", "2026-08-19T00:00:00+00:00"),
    )


@pytest.fixture
def json_repository(tmp_path):
    return JsonSaveRepository(tmp_path / "saves")


@pytest.fixture
def postgres_repository():
    if not POSTGRES_DSN:
        pytest.skip("GAL_TEST_POSTGRES_DSN not set (run `docker compose up -d postgres`)")
    repo = PostgresSaveRepository(POSTGRES_DSN)
    # clean slate per test: the shared DB accumulates saves from prior tests
    with repo._conn() as conn:
        conn.execute("DELETE FROM game_saves")
    return repo


@pytest.fixture(params=["json", "postgres"])
def repository(request, json_repository, postgres_repository):
    return json_repository if request.param == "json" else postgres_repository


def test_upsert_and_get_slot(repository: SaveRepository):
    repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1", title="slot1"))
    got = repository.get_slot("p1", MANUAL, 1)
    assert got is not None and got.id == "m1" and got.title == "slot1"
    assert repository.get_slot("p1", MANUAL, 2) is None
    assert repository.get_slot("p1", AUTO, None) is None


def test_overwrite_keeps_slot_identity_and_moves_updated_at(repository: SaveRepository):
    repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1", created_at="2026-08-19T00:00:00+00:00", updated_at="2026-08-19T00:00:00+00:00", phase="opening"))
    # overwrite = upsert with the SAME id (the service reuses the slot id)
    repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1", created_at="2026-08-19T00:00:00+00:00", updated_at="2026-08-19T02:00:00+00:00", phase="investigation"))
    saves = repository.list_by_player("p1")
    # overwrite replaces, does not duplicate (§16.1)
    assert len(saves) == 1
    assert saves[0].id == "m1" and saves[0].phase == "investigation"
    assert saves[0].updated_at == "2026-08-19T02:00:00+00:00"


def test_auto_slot_at_most_one(repository: SaveRepository):
    repository.upsert(_make_save("p1", AUTO, None, save_id="a1"))
    # overwrite = upsert with the SAME id (the service reuses the slot id)
    repository.upsert(_make_save("p1", AUTO, None, save_id="a1"))
    autos = [s for s in repository.list_by_player("p1") if s.slot_type == AUTO]
    assert len(autos) == 1 and autos[0].id == "a1"


def test_list_is_player_scoped_and_newest_first(repository: SaveRepository):
    repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1", updated_at="2026-08-19T00:00:00+00:00"))
    repository.upsert(_make_save("p1", MANUAL, 2, save_id="m2", updated_at="2026-08-19T03:00:00+00:00"))
    repository.upsert(_make_save("p2", MANUAL, 1, save_id="m3", updated_at="2026-08-19T05:00:00+00:00"))
    p1 = repository.list_by_player("p1")
    assert [s.id for s in p1] == ["m2", "m1"]
    assert [s.id for s in repository.list_by_player("p2")] == ["m3"]


def test_get_by_id(repository: SaveRepository):
    repository.upsert(_make_save("p1", MANUAL, 3, save_id="m3", snapshot={"schema_version": 1, "x": 1}))
    save = repository.get_by_id("m3")
    assert save is not None and save.snapshot == {"schema_version": 1, "x": 1}
    assert repository.get_by_id("nope") is None


def test_delete_slot(repository: SaveRepository):
    repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1"))
    assert repository.delete_slot("p1", MANUAL, 1) is True
    assert repository.get_slot("p1", MANUAL, 1) is None
    assert repository.delete_slot("p1", MANUAL, 1) is False


def test_json_upsert_is_atomic_on_replace_failure(json_repository, monkeypatch):
    """docs/13 §18 / §26.3 transaction rollback: ``os.replace`` is the single
    commit point of the JSON backend. A failed replace must leave the previous
    slot content untouched and no readable partial .json behind (all-or-nothing)."""
    import os as _os

    json_repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1", title="old"))
    original = json_repository.get_slot("p1", MANUAL, 1)
    assert original is not None and original.title == "old"

    def _boom(_src, _dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(_os, "replace", _boom)
    with pytest.raises(OSError):
        json_repository.upsert(_make_save("p1", MANUAL, 1, save_id="m1", title="new"))

    # the previous committed content survives the failed overwrite
    got = json_repository.get_slot("p1", MANUAL, 1)
    assert got is not None and got.title == "old"
    assert [s.id for s in json_repository.list_by_player("p1")] == ["m1"]
    # no readable partial save: only the committed m1.json matches *.json
    names = [
        p.name
        for p in (json_repository._data_dir / "p1").iterdir()
        if p.name.endswith(".json")
    ]
    assert names == ["m1.json"]

# ── T2review P1-2：player_id / save_id 路径穿越防护 ────────────────────────


def test_player_id_traversal_is_rejected(tmp_path):
    repo = JsonSaveRepository(tmp_path / "saves")
    with pytest.raises(ValueError, match="invalid player_id"):
        repo._player_dir("../escaped")
    with pytest.raises(ValueError, match="invalid player_id"):
        repo.list_by_player("../escaped")


def test_save_id_traversal_never_reads_outside_root(tmp_path):
    repo = JsonSaveRepository(tmp_path / "saves")
    assert repo.get_by_id("../../etc/passwd") is None
    with pytest.raises(ValueError, match="invalid save_id"):
        repo._path("p1", "../escaped")

