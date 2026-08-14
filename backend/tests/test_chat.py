"""TV-03 backend tests: mock chat round trip and session association."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(monkeypatch):
    # Pin the deterministic mock provider so API tests never depend on a live
    # model or on whether DEEPSEEK_API_KEY happens to be set in the environment.
    monkeypatch.setenv("GAL_PROVIDER", "mock")
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _send(client, message, session_id=None):
    payload = {"message": message}
    if session_id is not None:
        payload["session_id"] = session_id
    return client.post("/api/chat", json=payload)


def test_first_request_creates_session(client):
    response = _send(client, "这里是什么地方？")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["character_id"] == "deepseek"
    assert "这里是什么地方？" in body["dialogue"]
    assert body["message_count"] == 1


def test_reuses_session_and_increments_count(client):
    first = _send(client, "你好").json()
    second = _send(client, "墙上有个数字", session_id=first["session_id"]).json()
    assert second["session_id"] == first["session_id"]
    assert second["message_count"] == 2


def test_unknown_session_id_gets_fresh_session(client):
    first = _send(client, "你好", session_id="not-a-real-session").json()
    assert first["session_id"] != "not-a-real-session"
    assert first["message_count"] == 1


def test_ten_consecutive_requests_stay_in_session(client):
    session_id = None
    for turn in range(1, 11):
        response = _send(client, f"第 {turn} 句话", session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["message_count"] == turn
        session_id = body["session_id"]


def test_blank_message_rejected(client):
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 400


def test_retry_after_invalid_request_keeps_session(client):
    client.post("/api/chat", json={"message": "   "})
    first = _send(client, "重新来").json()
    assert first["message_count"] == 1


TEN_NATURAL_INPUTS = [
    "这里是什么地方？",
    "我们怎么才能出去？",
    "你看得见墙上的字吗？",
    "我叫阿明，你呢？",
    "你觉得是谁把我们抓来的？",
    "我好害怕。",
    "你能帮我解开绳子吗？",
    "你饿吗？",
    "我们在哪个城市？",
    "再说一遍，我不太明白。",
]


@pytest.mark.parametrize("message", TEN_NATURAL_INPUTS)
def test_ten_natural_inputs_via_api_all_usable(client, message):
    """TV-04 API contract: every natural-language input yields a usable reply.

    Run against the deterministic mock provider; the real-model pass is
    blocked on the DEEPSEEK_API_KEY environment variable.
    """
    response = _send(client, message)
    assert response.status_code == 200
    body = response.json()
    assert body["character_id"] == "deepseek"
    assert body["dialogue"].strip()
