"""Save API tests (docs/13 §20, §26.3).

Endpoints: GET /api/saves, POST /api/saves/manual/{slot}, POST /api/saves/auto,
POST /api/saves/{id}/load, DELETE /api/saves/manual/{slot}. The snapshot is
backend-captured (docs/13 §14.2): the API never accepts game state from the
client, and list responses carry slot metadata only (docs/13 §29).
"""

from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from app.game.investigation import CH1_NOTE_01, INSPECT_HOTSPOT, PAPER_RUBBING_COMPLETE
from app.main import create_app
from app.persistence.repository import JsonSessionRepository
from app.save import JsonSaveRepository, SaveSnapshotService
from app.save.service import SCHEMA_VERSION


def _app(tmp_path, monkeypatch):
    # Pin the deterministic mock provider (CLAUDE.md fixture contract): the app
    # must never reach a live model or depend on whether DEEPSEEK_API_KEY happens
    # to be set in the environment (the narrative interpreter then degrades the
    # turn to noop → the checkpoint side effect is skipped → flaky autos).
    monkeypatch.setenv("GAL_PROVIDER", "mock")
    app = create_app()
    session_repo = JsonSessionRepository(tmp_path / "sessions")
    save_service = SaveSnapshotService(JsonSaveRepository(tmp_path / "saves"))
    # Inject both repositories so Task 8 auto-save tests stay isolated and the
    # orchestrator's side effect uses the same repo the API layer does.
    app.state.orchestrator._repository = session_repo
    app.state.orchestrator._save_service = save_service
    app.state.save_service = save_service
    return app


def _opened_session(client: TestClient, player_id: str | None = None) -> str:
    """A session that has passed the opening (so it is saveable)."""
    opened = client.post(
        "/api/chat/opening",
        json={"player_id": player_id} if player_id is not None else {},
    ).json()
    return opened["session_id"]


def _session_with_evidence(client: TestClient, player_id: str | None = None) -> str:
    session_id = _opened_session(client, player_id)
    client.post(
        "/api/game/action",
        json={"session_id": session_id, "action": INSPECT_HOTSPOT, "hotspot_id": CH1_NOTE_01},
    )
    client.post(
        "/api/game/action",
        json={"session_id": session_id, "action": PAPER_RUBBING_COMPLETE, "hotspot_id": CH1_NOTE_01},
    )
    return session_id


def test_manual_save_list_and_load_roundtrip(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        session_id = _session_with_evidence(client)

        saved = client.post(
            "/api/saves/manual/1",
            json={"player_id": "p1", "session_id": session_id, "title": "测试存档"},
        )
        assert saved.status_code == 200
        meta = saved.json()
        assert meta["slot_type"] == "MANUAL" and meta["slot_index"] == 1
        assert meta["phase"] == "investigation"
        assert "snapshot" not in meta  # docs/13 §29: never shipped to browser

        listing = client.get("/api/saves", params={"player_id": "p1"}).json()
        assert listing["auto"] is None
        assert listing["manual"][0] is not None
        assert listing["manual"][0]["id"] == meta["id"]
        assert all(s is None for s in listing["manual"][1:])

        # mutate the live session, then load
        client.post("/api/chat", json={"session_id": session_id, "message": "继续说。", "character_id": "deepseek"})
        loaded = client.post(
            f"/api/saves/{meta['id']}/load", json={"player_id": "p1"}
        )
        assert loaded.status_code == 200
        body = loaded.json()
        new_session_id = body["session_id"]
        assert new_session_id != session_id  # docs/13 §19.1: NEW Active Session
        assert "state" in body and "history" in body
        # the loaded session has the saved evidence
        ev = client.get("/api/game/evidence", params={"session_id": new_session_id}).json()
        assert any(e["evidence_id"] == "EV01_NOTE_V03" for e in ev)


def test_auto_save_overwrites_single_slot(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        session_id = _opened_session(client, "p1")
        first = client.get("/api/saves", params={"player_id": "p1"}).json()["auto"]
        session_id2 = _opened_session(client, "p1")
        second = client.get("/api/saves", params={"player_id": "p1"}).json()["auto"]

        listing = client.get("/api/saves", params={"player_id": "p1"}).json()
        assert listing["auto"] is not None
        # single AUTO slot: the newest overwrote, identity kept (docs/13 §16.1)
        assert listing["auto"]["id"] == first["id"]
        assert listing["auto"]["source_session_id"] == session_id2


def test_load_invalid_save_id_is_404(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        res = client.post("/api/saves/nope/load", json={"player_id": "p1"})
        assert res.status_code == 404


def test_delete_manual_slot(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        session_id = _opened_session(client)
        client.post("/api/saves/manual/2", json={"player_id": "p1", "session_id": session_id})
        assert client.delete("/api/saves/manual/2", params={"player_id": "p1"}).json()["deleted"] is True
        listing = client.get("/api/saves", params={"player_id": "p1"}).json()
        assert listing["manual"][1] is None
        assert client.delete("/api/saves/manual/2", params={"player_id": "p1"}).json()["deleted"] is False


def test_save_list_is_player_scoped(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        session_id = _opened_session(client)
        client.post("/api/saves/manual/1", json={"player_id": "p1", "session_id": session_id})
        client.post("/api/saves/manual/1", json={"player_id": "p2", "session_id": session_id})
        assert client.get("/api/saves", params={"player_id": "p1"}).json()["manual"][0] is not None
        assert client.get("/api/saves", params={"player_id": "p3"}).json()["manual"][0] is None


def test_auth_disabled_vue_client_can_list_saves_without_legacy_player_id(tmp_path, monkeypatch):
    """The current Vue client relies on the middleware's deterministic local user."""
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        response = client.get("/api/saves")
        assert response.status_code == 200
        assert response.json() == {"auto": None, "manual": [None] * 6}


# ── docs/13 Task 8: Auto Save 是 Narrative commit 后的 side effect ─────────

def _auto_meta(client: TestClient, player_id: str) -> dict | None:
    return client.get("/api/saves", params={"player_id": player_id}).json()["auto"]


def test_opening_complete_auto_saves_on_opening(tmp_path, monkeypatch):
    """docs/13 Task 8 acceptance #1: the opening endpoint commits + persists,
    then the AUTO slot appears (updated_at moves) for that player."""
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        assert _auto_meta(client, "p1") is None
        opened = client.post("/api/chat/opening", json={"player_id": "p1"}).json()
        session_id = opened["session_id"]
        auto = _auto_meta(client, "p1")
        assert auto is not None and auto["source_session_id"] == session_id
        # another player does not see it (docs/13 §15 namespace)
        assert _auto_meta(client, "p2") is None


def test_claude_appeared_auto_saves_after_0317(tmp_path, monkeypatch):
    """docs/13 Task 8 acceptance #2: the turn that commits Claude's appearance
    overwrites the AUTO slot with the same session."""
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        session_id = _session_with_evidence(client, "p1")  # EV01 + chapter started
        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "你好", "player_id": "p1"},
        )
        before = _auto_meta(client, "p1")
        assert before is not None

        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "03:17 是什么意思？", "player_id": "p1"},
        )
        after = _auto_meta(client, "p1")
        assert after["source_session_id"] == session_id
        assert after["updated_at"] > before["updated_at"]
