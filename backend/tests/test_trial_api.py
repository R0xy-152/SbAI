"""HTTP-level trial_v1 checkpoint, save and restore contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.repository import JsonSessionRepository
from app.save import JsonSaveRepository, SaveSnapshotService


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("GAL_PROVIDER", "mock")
    app = create_app()
    session_repository = JsonSessionRepository(tmp_path / "sessions")
    save_service = SaveSnapshotService(JsonSaveRepository(tmp_path / "saves"))
    app.state.orchestrator._repository = session_repository
    app.state.orchestrator._save_service = save_service
    app.state.save_service = save_service
    return app


def _send(client: TestClient, session_id: str, command_type: str, index: int, **payload):
    return client.post(
        "/api/trial/command",
        json={
            "session_id": session_id,
            "command": {
                "type": command_type,
                "command_id": f"trial-api-{index}",
                **payload,
            },
        },
    )


def test_trial_checkpoint_auto_save_loads_back_into_trial(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        initial = client.get("/api/trial/current")
        assert initial.status_code == 200
        session_id = initial.json()["session_id"]

        assert _send(client, session_id, "ADVANCE", 1).status_code == 200
        assert _send(client, session_id, "ADVANCE", 2).status_code == 200
        anomaly = _send(
            client,
            session_id,
            "PLAYER_INPUT",
            3,
            message="你还好吗？",
        )
        assert anomaly.status_code == 200
        assert anomaly.json()["phase_id"] == "opening_anomaly"
        assert "原初 AI" not in anomaly.text

        saves = client.get("/api/saves")
        assert saves.status_code == 200
        auto = saves.json()["auto"]
        assert auto["chapter_id"] == "trial_v2"
        assert auto["phase"] == "opening_anomaly"

        loaded = client.post(f"/api/saves/{auto['id']}/load", json={})
        assert loaded.status_code == 200
        load_view = loaded.json()
        assert load_view["experience_id"] == "trial_v2"
        assert load_view["trial_finished"] is False
        assert load_view["story_cursor"] is None

        restored = client.get(
            "/api/trial/current",
            params={"session_id": load_view["session_id"]},
        )
        assert restored.status_code == 200
        assert restored.json()["phase_id"] == "opening_anomaly"
