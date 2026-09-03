"""docs/21 §5：运营看板 API（门禁 + 聚合口径）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import DeveloperNote
from app.main import create_app
from app.ops.events import (
    EVENT_AI_CHAT_ENTER,
    EVENT_AI_CHAT_ERROR,
    EVENT_AI_CHAT_TURN,
    EVENT_PROLOGUE_COMPLETED,
    EVENT_PROLOGUE_START,
    EVENT_PROLOGUE_VISIT_CHOSEN,
    EVENT_PROLOGUE_VISIT_COMPLETED,
    EVENT_VALIDATION_REJECT,
    ChatMetric,
)
from app.ops.feedback import FeedbackClassifier, MemoryFeedbackStore

TOKEN = "test-ops-token"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("GAL_OPS_TOKEN", TOKEN)
    app = create_app()
    app.state.feedback_store = MemoryFeedbackStore()  # 与 ops 同内存后端
    _seed(app)
    with TestClient(app) as test_client:
        yield test_client


def _seed(app) -> None:
    recorder = app.state.ops
    # s1：完整走到 AI 对话（chatgpt 结尾），探班顺序 deepseek→chatgpt→claude
    recorder.record(EVENT_PROLOGUE_START, session_id="s1")
    for order, char in enumerate(("deepseek", "chatgpt", "claude"), start=1):
        recorder.record(
            EVENT_PROLOGUE_VISIT_CHOSEN,
            session_id="s1",
            character_id=char,
            payload={"character_id": char, "order": order},
        )
        recorder.record(
            EVENT_PROLOGUE_VISIT_COMPLETED,
            session_id="s1",
            character_id=char,
            payload={"character_id": char},
        )
    recorder.record(
        EVENT_PROLOGUE_COMPLETED,
        session_id="s1",
        payload={"chat_character_id": "chatgpt"},
    )
    recorder.record(EVENT_AI_CHAT_ENTER, session_id="s1", payload={"character_id": "chatgpt"})
    recorder.record(
        EVENT_AI_CHAT_TURN, session_id="s1", payload={"provider": "deepseek", "validation": "approved"}
    )
    recorder.record(
        EVENT_AI_CHAT_TURN, session_id="s1", payload={"provider": "deepseek", "validation": "approved"}
    )
    # s2：选了一次探班就流失（错误也发生在这里）
    recorder.record(EVENT_PROLOGUE_START, session_id="s2")
    recorder.record(
        EVENT_PROLOGUE_VISIT_CHOSEN,
        session_id="s2",
        character_id="deepseek",
        payload={"character_id": "deepseek", "order": 1},
    )
    recorder.record(
        EVENT_AI_CHAT_ERROR, session_id="s2", payload={"error_type": "ProviderError"}
    )
    # s3：三篇全部完成但未选聊天角色（完成两篇探班后停在第 3 篇）
    recorder.record(EVENT_PROLOGUE_START, session_id="s3")
    for char, order in (("deepseek", 1), ("chatgpt", 2), ("claude", 3)):
        recorder.record(
            EVENT_PROLOGUE_VISIT_CHOSEN,
            session_id="s3",
            character_id=char,
            payload={"character_id": char, "order": order},
        )
    for char in ("deepseek", "chatgpt"):
        recorder.record(
            EVENT_PROLOGUE_VISIT_COMPLETED,
            session_id="s3",
            character_id=char,
            payload={"character_id": char},
        )
    recorder.record(
        EVENT_VALIDATION_REJECT,
        session_id="s1",
        payload={"gate": "deterministic", "reason": "character mismatch"},
    )
    recorder.record_chat_metric(
        ChatMetric(
            session_id="s1",
            user_id=None,
            character_id="chatgpt",
            provider="deepseek",
            latency_ms=300.0,
            prompt_tokens=10,
            completion_tokens=5,
            cache_hit_tokens=0,
            cache_miss_tokens=10,
        )
    )
    recorder.record_chat_metric(
        ChatMetric(
            session_id="s1",
            user_id=None,
            character_id="chatgpt",
            provider="deepseek",
            latency_ms=100.0,
            prompt_tokens=10,
            completion_tokens=5,
            cache_hit_tokens=0,
            cache_miss_tokens=10,
        )
    )


def _headers():
    return {"x-ops-token": TOKEN}


def test_ops_endpoints_require_token(monkeypatch):
    monkeypatch.setenv("GAL_OPS_TOKEN", TOKEN)
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/ops/funnel").status_code == 401
        assert client.get("/api/ops/funnel", headers=_headers()).status_code == 200
        assert client.post("/api/ops/feedback/analyze", json={}).status_code == 401


def test_ops_disabled_without_token_env(monkeypatch):
    monkeypatch.delenv("GAL_OPS_TOKEN", raising=False)
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/ops/funnel", headers=_headers()).status_code == 503


def test_funnel_stage_counts(client):
    body = client.get("/api/ops/funnel", headers=_headers()).json()
    stages = body["stage_counts"]
    assert stages["started"] == 3
    assert stages["visit_chosen"] == 3
    assert stages["visit_completed"] == 2
    assert stages["three_visits"] == 1
    assert stages["prologue_completed"] == 1
    assert stages["ai_chat_entered"] == 1
    # 流失节点：最远阶段分布
    furthest = body["furthest_stage_counts"]
    assert furthest == {
        "ai_chat_entered": 1,
        "visit_chosen": 1,
        "visit_completed": 1,
    }
    # 按角色完成率：deepseek 2/3、chatgpt 2/2、claude 1/2
    assert body["characters"]["deepseek"]["completion_rate"] == pytest.approx(
        2 / 3, abs=1e-3
    )
    assert body["characters"]["chatgpt"]["completion_rate"] == 1.0
    assert body["characters"]["claude"]["completion_rate"] == 0.5


def test_preferences(client):
    body = client.get("/api/ops/preferences", headers=_headers()).json()
    # 三个会话的首访都是 deepseek；聊天角色只在 s1 选择过 chatgpt
    assert body["first_visit"]["deepseek"] == 3
    assert body["chat_choice"] == {"chatgpt": 1}


def test_ai_metrics(client):
    body = client.get("/api/ops/ai", headers=_headers()).json()
    assert body["turn_count"] == 2
    assert body["error_count"] == 1
    assert body["success_rate"] == pytest.approx(2 / 3, abs=1e-3)
    assert body["validation_reject_count"] == 1
    assert body["validation_reject_by_gate"] == {"deterministic": 1}
    latency = body["latency"]
    assert latency["n"] == 2
    assert latency["p50_ms"] == 100.0 and latency["p95_ms"] == 300.0
    assert body["cost"]["complete_sessions"] == 1
    assert body["cost"]["avg_per_complete_session_cny"] == pytest.approx(
        body["cost"]["total_cny"]
    )


def test_events_stream(client):
    body = client.get(
        "/api/ops/events", params={"event_name": EVENT_VALIDATION_REJECT}, headers=_headers()
    ).json()
    assert body["count"] == 1
    assert body["events"][0]["payload"]["gate"] == "deterministic"


class _FakeProvider:
    def complete(self, *, system, user, max_tokens=256, response_format=None,
                 thinking=None, metrics=None) -> str:
        return json.dumps(
            {
                "dedupe_key": "k",
                "topic": "bug",
                "severity": "medium",
                "scene": "ai_chat_chatgpt",
                "is_duplicate_of": None,
                "summary": "对话卡顿",
            },
            ensure_ascii=False,
        )


def _add_note(app, session_id: str, content: str) -> None:
    app.state.auth_service.add_developer_note(
        DeveloperNote(
            user_id="u1",
            display_name="测试",
            label=None,
            character_id="chatgpt",
            content=content,
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
        )
    )


def test_feedback_analyze_annotate_precision(client, monkeypatch):
    app = client.app
    _add_note(app, "n1", "AI 对话有点卡")
    app.state.feedback_classifier = FeedbackClassifier(
        _FakeProvider(), app.state.auth_service, app.state.feedback_store, model_name="fake"
    )
    body = client.post(
        "/api/ops/feedback/analyze", json={"max_items": 10}, headers=_headers()
    ).json()
    assert body == {"analyzed": 1, "failed": 0}

    feedback = client.get("/api/ops/feedback", headers=_headers()).json()
    assert len(feedback["notes"]) == 1 and len(feedback["analyses"]) == 1
    assert feedback["analyses"][0]["topic"] == "bug"
    assert feedback["precision"]["n"] == 0

    client.post(
        "/api/ops/feedback/annotate",
        json={"note_key": "n1", "topic_correct": True, "severity_correct": False},
        headers=_headers(),
    )
    precision = client.get("/api/ops/feedback", headers=_headers()).json()["precision"]
    assert precision["n"] == 1
    assert precision["topic"]["precision"] == 1.0
    assert precision["severity"]["precision"] == 0.0


def test_ops_endpoints_bypass_session_auth_but_keep_token_gate(monkeypatch):
    # docs/21 §5：会话认证豁免 + 仅 token 门禁——未登录可访问、无 token 仍拒绝
    monkeypatch.setenv("GAL_AUTH_REQUIRED", "true")
    monkeypatch.setenv("GAL_OPS_TOKEN", TOKEN)
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/ops/funnel", headers=_headers()).status_code == 200
        assert client.get("/api/ops/funnel").status_code == 401
        # 玩家端点仍要求登录
        assert client.get("/api/chat/history?session_id=x").status_code == 401


def test_ops_page_served_without_token():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/ops")
        assert response.status_code == 200
        assert "运营看板" in response.text
