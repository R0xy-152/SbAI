from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.auth import AuthService, MemoryAuthRepository, UserRecord
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.providers.mock import MockProvider


def _secured_app(monkeypatch):
    monkeypatch.setenv("GAL_PROVIDER", "mock")
    monkeypatch.setenv("GAL_AUTH_REQUIRED", "true")
    monkeypatch.setenv("GAL_AUTH_BACKEND", "memory")
    monkeypatch.setenv("GAL_AUTH_SECRET", "test-secret")
    return create_app()


def _account(app, name="展示账号", quota=100):
    return app.state.auth_service.create_user(name, quota)


def test_login_me_logout_and_reusable_cross_device(monkeypatch):
    app = _secured_app(monkeypatch)
    user, invite = _account(app)
    with TestClient(app) as first, TestClient(app) as second:
        assert first.get("/api/auth/me").status_code == 401
        assert first.post("/api/auth/login", json={"invite_code": "wrong"}).status_code == 401

        login = first.post("/api/auth/login", json={"invite_code": invite.lower()})
        assert login.status_code == 200
        assert login.json()["user_id"] == user.id
        assert "gal_auth" in first.cookies
        assert first.get("/api/auth/me").json()["quota_remaining"] == 100

        assert second.post("/api/auth/login", json={"invite_code": invite}).status_code == 200
        assert second.get("/api/auth/me").json()["user_id"] == user.id

        assert first.post("/api/auth/logout").status_code == 200
        assert first.get("/api/auth/me").status_code == 401
        assert second.get("/api/auth/me").status_code == 200


def test_disabled_account_invalidates_existing_session(monkeypatch):
    app = _secured_app(monkeypatch)
    user, invite = _account(app)
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"invite_code": invite})
        app.state.auth_service.repository.set_status(user.id, "DISABLED")
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/auth/login", json={"invite_code": invite}).status_code == 401


def test_chat_consumes_permanent_quota_and_blocks_before_runtime(monkeypatch):
    app = _secured_app(monkeypatch)
    _, invite = _account(app, quota=1)
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"invite_code": invite})
        first = client.post("/api/chat", json={"message": "你好"})
        assert first.status_code == 200
        assert first.json()["quota_remaining"] == 0
        exhausted = client.post("/api/chat", json={"message": "再聊一次"})
        assert exhausted.status_code == 429
        assert client.get("/api/auth/me").json()["quota_used"] == 1


def test_provider_failure_refunds_reserved_quota(monkeypatch):
    app = _secured_app(monkeypatch)
    _, invite = _account(app, quota=1)
    app.state.orchestrator = GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(MockProvider(fail=True))}
    )
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"invite_code": invite})
        assert client.post("/api/chat", json={"message": "你好"}).status_code == 503
        assert client.get("/api/auth/me").json()["quota_remaining"] == 1


def test_session_and_save_are_account_scoped(monkeypatch):
    app = _secured_app(monkeypatch)
    _, invite_a = _account(app, "A")
    _, invite_b = _account(app, "B")
    with TestClient(app) as first, TestClient(app) as second:
        first.post("/api/auth/login", json={"invite_code": invite_a})
        second.post("/api/auth/login", json={"invite_code": invite_b})
        session_id = first.post("/api/chat", json={"message": "我的会话"}).json()["session_id"]
        assert first.get("/api/chat/history", params={"session_id": session_id}).status_code == 200
        assert second.get("/api/chat/history", params={"session_id": session_id}).status_code == 404
        assert second.post(
            "/api/saves/manual/1", json={"session_id": session_id}
        ).status_code == 404


def test_expired_session_is_rejected():
    repository = MemoryAuthRepository()
    service = AuthService(repository, "secret")
    user, _ = service.create_user("Expired")
    repository.record_login(
        user.id, service.token_digest("expired-token"), datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    assert service.authenticate("expired-token") is None


def test_quota_last_slot_is_atomic():
    repository = MemoryAuthRepository()
    user = UserRecord(
        id="u", display_name="U", invite_code_digest="d", status="ACTIVE",
        quota_total=1, quota_used=0, created_at=datetime.now(timezone.utc),
    )
    repository.create_user(user)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: repository.reserve_quota("u"), range(2)))
    assert sorted(results, key=lambda value: value is None) == [0, None]
