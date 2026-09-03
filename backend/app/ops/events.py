"""运营事件埋点与指标存储（docs/21 §2-3）。

OpsRecorder 是「事后记录」副作用：任何写失败只记日志、绝不破坏游戏回合
（与 Auto Save 同约定，docs/13 §21）。事件 payload 只存结构化属性，不存
玩家消息正文，便于聚合与追溯。
"""

from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

# ---- docs/21 §2：事件字典 ----

EVENT_PROLOGUE_START = "prologue_start"
EVENT_PROLOGUE_VISIT_CHOSEN = "prologue_visit_chosen"
EVENT_PROLOGUE_VISIT_COMPLETED = "prologue_visit_completed"
EVENT_PROLOGUE_CHOICE = "prologue_choice"
EVENT_PROLOGUE_COMPLETED = "prologue_completed"
EVENT_AI_CHAT_ENTER = "ai_chat_enter"
EVENT_AI_CHAT_TURN = "ai_chat_turn"
EVENT_AI_CHAT_ERROR = "ai_chat_error"
EVENT_AI_CHAT_BLOCKED = "ai_chat_blocked"
EVENT_VALIDATION_REJECT = "validation_reject"

EVENT_NAMES = frozenset(
    {
        EVENT_PROLOGUE_START,
        EVENT_PROLOGUE_VISIT_CHOSEN,
        EVENT_PROLOGUE_VISIT_COMPLETED,
        EVENT_PROLOGUE_CHOICE,
        EVENT_PROLOGUE_COMPLETED,
        EVENT_AI_CHAT_ENTER,
        EVENT_AI_CHAT_TURN,
        EVENT_AI_CHAT_ERROR,
        EVENT_AI_CHAT_BLOCKED,
        EVENT_VALIDATION_REJECT,
    }
)

# docs/21 §3：game_events / chat_metrics / feedback_analysis /
# feedback_annotations 四表。feedback 表与 auth 仓库同库（GAL_POSTGRES_DSN），
# 两个 store 各自执行本 SQL，幂等（CREATE IF NOT EXISTS）。
OPS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS game_events (
    id           BIGSERIAL PRIMARY KEY,
    event_name   TEXT NOT NULL,
    session_id   TEXT,
    user_id      TEXT,
    character_id TEXT,
    payload      JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_game_events_name_time
    ON game_events(event_name, created_at);
CREATE INDEX IF NOT EXISTS ix_game_events_session ON game_events(session_id);
CREATE INDEX IF NOT EXISTS ix_game_events_user ON game_events(user_id);
CREATE TABLE IF NOT EXISTS chat_metrics (
    id                BIGSERIAL PRIMARY KEY,
    session_id        TEXT,
    user_id           TEXT,
    character_id      TEXT,
    provider          TEXT NOT NULL DEFAULT 'unknown',
    latency_ms        DOUBLE PRECISION NOT NULL DEFAULT 0,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cache_hit_tokens  INTEGER NOT NULL DEFAULT 0,
    cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
    cost_cny          DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_chat_metrics_time ON chat_metrics(created_at);
CREATE TABLE IF NOT EXISTS feedback_analysis (
    id               BIGSERIAL PRIMARY KEY,
    note_key         TEXT NOT NULL UNIQUE,
    dedupe_key       TEXT,
    topic            TEXT NOT NULL DEFAULT 'other',
    severity         TEXT NOT NULL DEFAULT 'low',
    scene            TEXT,
    is_duplicate_of  TEXT,
    summary          TEXT,
    model            TEXT,
    status           TEXT NOT NULL DEFAULT 'classified',
    raw_json         TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_feedback_analysis_dedupe
    ON feedback_analysis(dedupe_key);
CREATE TABLE IF NOT EXISTS feedback_annotations (
    id               BIGSERIAL PRIMARY KEY,
    note_key         TEXT NOT NULL,
    topic_correct    BOOLEAN NOT NULL,
    severity_correct BOOLEAN NOT NULL,
    annotator        TEXT NOT NULL DEFAULT 'human',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_feedback_annotations_note
    ON feedback_annotations(note_key);
"""


# ---- docs/21 §3：成本口径（每 1M token 单价，人民币，环境变量可覆盖） ----

def _price(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


def compute_cost_cny(
    *, cache_hit_tokens: int, cache_miss_tokens: int, completion_tokens: int
) -> float:
    """成本 = (miss×input + hit×cache_hit + completion×output)/1e6（docs/21 §3）。

    价格是占位口径（DeepSeek 公开价档），token 原始数已落库，口径变化可重算。
    """
    return (
        cache_miss_tokens * _price("GAL_OPS_PRICE_INPUT", 2.0)
        + cache_hit_tokens * _price("GAL_OPS_PRICE_CACHE_HIT", 0.5)
        + completion_tokens * _price("GAL_OPS_PRICE_OUTPUT", 8.0)
    ) / 1_000_000


@dataclass(frozen=True)
class OpsEvent:
    """一条运营事件（docs/21 §2）。payload 是结构化 dict，不存消息正文。"""

    event_name: str
    session_id: str | None = None
    user_id: str | None = None
    character_id: str | None = None
    payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_public(self) -> dict:
        return {
            "event_name": self.event_name,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ChatMetric:
    """一次 AI 回复的延迟与 token 用量（docs/21 §3）。"""

    session_id: str | None
    user_id: str | None
    character_id: str | None
    provider: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cache_hit_tokens: int
    cache_miss_tokens: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def cost_cny(self) -> float:
        return compute_cost_cny(
            cache_hit_tokens=self.cache_hit_tokens,
            cache_miss_tokens=self.cache_miss_tokens,
            completion_tokens=self.completion_tokens,
        )

    def to_public(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "provider": self.provider,
            "latency_ms": round(self.latency_ms, 1),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cache_hit_tokens": self.cache_hit_tokens,
            "cache_miss_tokens": self.cache_miss_tokens,
            "cost_cny": round(self.cost_cny, 6),
            "created_at": self.created_at.isoformat(),
        }


class OpsRecorder(ABC):
    """事件与指标的写入/读取接口（docs/21 §3）。"""

    @abstractmethod
    def record(
        self,
        event_name: str,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        character_id: str | None = None,
        payload: dict | None = None,
    ) -> None: ...

    @abstractmethod
    def has_event(self, session_id: str, event_name: str) -> bool: ...

    @abstractmethod
    def record_chat_metric(self, metric: ChatMetric) -> None: ...

    @abstractmethod
    def list_events(
        self,
        *,
        event_name: str | None = None,
        session_id: str | None = None,
        limit: int = 1000,
        since: datetime | None = None,
    ) -> list[OpsEvent]: ...

    @abstractmethod
    def list_chat_metrics(
        self, *, limit: int = 5000, since: datetime | None = None
    ) -> list[ChatMetric]: ...


class MemoryOpsRecorder(OpsRecorder):
    """Thread-safe 内存实现；本地开发/测试用（docs/21 §3）。"""

    def __init__(self) -> None:
        self._events: list[OpsEvent] = []
        self._metrics: list[ChatMetric] = []
        self._lock = threading.Lock()

    def record(
        self,
        event_name: str,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        character_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        if event_name not in EVENT_NAMES:
            raise ValueError(f"unknown ops event {event_name!r}")
        event = OpsEvent(
            event_name=event_name,
            session_id=session_id,
            user_id=user_id,
            character_id=character_id,
            payload=dict(payload or {}),
        )
        with self._lock:
            self._events.append(event)

    def has_event(self, session_id: str, event_name: str) -> bool:
        with self._lock:
            return any(
                e.session_id == session_id and e.event_name == event_name
                for e in self._events
            )

    def record_chat_metric(self, metric: ChatMetric) -> None:
        with self._lock:
            self._metrics.append(metric)

    def list_events(
        self,
        *,
        event_name: str | None = None,
        session_id: str | None = None,
        limit: int = 1000,
        since: datetime | None = None,
    ) -> list[OpsEvent]:
        with self._lock:
            rows = list(self._events)
        if event_name is not None:
            rows = [e for e in rows if e.event_name == event_name]
        if session_id is not None:
            rows = [e for e in rows if e.session_id == session_id]
        if since is not None:
            rows = [e for e in rows if e.created_at >= since]
        return rows[-limit:]

    def list_chat_metrics(
        self, *, limit: int = 5000, since: datetime | None = None
    ) -> list[ChatMetric]:
        with self._lock:
            rows = list(self._metrics)
        if since is not None:
            rows = [m for m in rows if m.created_at >= since]
        return rows[-limit:]


class PostgresOpsRecorder(OpsRecorder):
    """生产实现：与 auth 仓库同库、同 DSN（docs/21 §3）。"""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._initialized = False
        self._lock = threading.Lock()

    def _ensure_schema(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            import psycopg

            with psycopg.connect(self._dsn) as conn:
                conn.execute(OPS_SCHEMA_SQL)
            self._initialized = True

    def _conn(self):
        import psycopg

        self._ensure_schema()
        return psycopg.connect(self._dsn)

    def record(
        self,
        event_name: str,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        character_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        if event_name not in EVENT_NAMES:
            raise ValueError(f"unknown ops event {event_name!r}")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO game_events"
                " (event_name, session_id, user_id, character_id, payload)"
                " VALUES (%s, %s, %s, %s, %s::jsonb)",
                (
                    event_name,
                    session_id,
                    user_id,
                    character_id,
                    json.dumps(payload or {}, ensure_ascii=False),
                ),
            )

    def has_event(self, session_id: str, event_name: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM game_events"
                " WHERE session_id = %s AND event_name = %s LIMIT 1",
                (session_id, event_name),
            ).fetchone()
            return row is not None

    def record_chat_metric(self, metric: ChatMetric) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chat_metrics"
                " (session_id, user_id, character_id, provider, latency_ms,"
                "  prompt_tokens, completion_tokens, cache_hit_tokens,"
                "  cache_miss_tokens, cost_cny)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    metric.session_id,
                    metric.user_id,
                    metric.character_id,
                    metric.provider,
                    metric.latency_ms,
                    metric.prompt_tokens,
                    metric.completion_tokens,
                    metric.cache_hit_tokens,
                    metric.cache_miss_tokens,
                    metric.cost_cny,
                ),
            )

    @staticmethod
    def _event(row) -> OpsEvent:
        return OpsEvent(
            event_name=row[1],
            session_id=row[2],
            user_id=row[3],
            character_id=row[4],
            payload=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
            created_at=row[6],
        )

    def list_events(
        self,
        *,
        event_name: str | None = None,
        session_id: str | None = None,
        limit: int = 1000,
        since: datetime | None = None,
    ) -> list[OpsEvent]:
        clauses, params = [], []
        if event_name is not None:
            clauses.append("event_name = %s")
            params.append(event_name)
        if session_id is not None:
            clauses.append("session_id = %s")
            params.append(session_id)
        if since is not None:
            clauses.append("created_at >= %s")
            params.append(since)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, event_name, session_id, user_id, character_id,"
                " payload, created_at FROM game_events"
                f"{where} ORDER BY created_at DESC LIMIT %s",
                (*params, limit),
            ).fetchall()
        return list(reversed([self._event(row) for row in rows]))

    @staticmethod
    def _metric(row) -> ChatMetric:
        return ChatMetric(
            session_id=row[1],
            user_id=row[2],
            character_id=row[3],
            provider=row[4],
            latency_ms=float(row[5]),
            prompt_tokens=row[6],
            completion_tokens=row[7],
            cache_hit_tokens=row[8],
            cache_miss_tokens=row[9],
            created_at=row[11],
        )

    def list_chat_metrics(
        self, *, limit: int = 5000, since: datetime | None = None
    ) -> list[ChatMetric]:
        where, params = "", []
        if since is not None:
            where = " WHERE created_at >= %s"
            params.append(since)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, session_id, user_id, character_id, provider,"
                " latency_ms, prompt_tokens, completion_tokens, cache_hit_tokens,"
                " cache_miss_tokens, cost_cny, created_at FROM chat_metrics"
                f"{where} ORDER BY created_at DESC LIMIT %s",
                (*params, limit),
            ).fetchall()
        return list(reversed([self._metric(row) for row in rows]))
