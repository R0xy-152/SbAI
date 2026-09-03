"""docs/21 §2-3：事件/指标存储（内存实现）与成本口径。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.ops.events import (
    EVENT_AI_CHAT_TURN,
    EVENT_PROLOGUE_START,
    ChatMetric,
    MemoryOpsRecorder,
    OPS_SCHEMA_SQL,
    compute_cost_cny,
)


def test_record_and_has_event():
    recorder = MemoryOpsRecorder()
    recorder.record(
        EVENT_PROLOGUE_START, session_id="s1", payload={"story_id": "prologue"}
    )
    assert recorder.has_event("s1", EVENT_PROLOGUE_START) is True
    assert recorder.has_event("s1", EVENT_AI_CHAT_TURN) is False
    assert recorder.has_event("s2", EVENT_PROLOGUE_START) is False


def test_unknown_event_rejected():
    recorder = MemoryOpsRecorder()
    with pytest.raises(ValueError):
        recorder.record("made_up_event", session_id="s1")


def test_list_events_filters_and_limit():
    recorder = MemoryOpsRecorder()
    for i in range(5):
        recorder.record(EVENT_PROLOGUE_START, session_id=f"s{i}")
    recorder.record(EVENT_AI_CHAT_TURN, session_id="s0")
    assert len(recorder.list_events()) == 6
    by_name = recorder.list_events(event_name=EVENT_AI_CHAT_TURN)
    assert len(by_name) == 1 and by_name[0].session_id == "s0"
    assert len(recorder.list_events(limit=3)) == 3
    since = datetime.now(timezone.utc) + timedelta(days=1)
    assert recorder.list_events(since=since) == []


def test_chat_metric_cost_default_prices(monkeypatch):
    # docs/21 §3 占位价格：(20 miss × 2 + 80 hit × 0.5 + 30 out × 8)/1e6
    metric = ChatMetric(
        session_id="s1",
        user_id="u1",
        character_id="deepseek",
        provider="deepseek-v4-flash",
        latency_ms=1234.5,
        prompt_tokens=100,
        completion_tokens=30,
        cache_hit_tokens=80,
        cache_miss_tokens=20,
    )
    assert metric.cost_cny == pytest.approx((40 + 40 + 240) / 1_000_000)
    recorder = MemoryOpsRecorder()
    recorder.record_chat_metric(metric)
    rows = recorder.list_chat_metrics()
    assert len(rows) == 1 and rows[0].provider == "deepseek-v4-flash"


def test_chat_metric_cost_env_prices(monkeypatch):
    monkeypatch.setenv("GAL_OPS_PRICE_INPUT", "4.0")
    monkeypatch.setenv("GAL_OPS_PRICE_CACHE_HIT", "1.0")
    monkeypatch.setenv("GAL_OPS_PRICE_OUTPUT", "16.0")
    assert compute_cost_cny(
        cache_hit_tokens=100, cache_miss_tokens=100, completion_tokens=100
    ) == pytest.approx((400 + 100 + 1600) / 1_000_000)


def test_schema_sql_contains_four_tables():
    for table in ("game_events", "chat_metrics", "feedback_analysis", "feedback_annotations"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in OPS_SCHEMA_SQL
