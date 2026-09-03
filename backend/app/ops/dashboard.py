"""内部运营看板 API（docs/21 §5）。

所有端点要求 GAL_OPS_TOKEN 门禁（x-ops-token 头或 ?token= 查询参数）；
未配置时 503 关闭——玩家侧永远看不到这些数据。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.ops.aggregate import compute_ai_metrics, compute_funnel, compute_preferences
from app.ops.feedback import FeedbackEvaluator

logger = logging.getLogger(__name__)

router = APIRouter()

_EVENT_LIMIT = 100_000
_METRIC_LIMIT = 100_000


def _gate(request: Request) -> None:
    token = os.environ.get("GAL_OPS_TOKEN", "").strip()
    if not token:
        raise HTTPException(
            status_code=503,
            detail="ops dashboard disabled (GAL_OPS_TOKEN not set)",
        )
    supplied = (
        request.headers.get("x-ops-token") or request.query_params.get("token")
    )
    if not supplied or supplied != token:
        raise HTTPException(status_code=401, detail="invalid ops token")


def _since(days: int) -> datetime | None:
    if days <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/api/ops/funnel")
def funnel(request: Request, days: int = 30) -> dict:
    _gate(request)
    events = request.app.state.ops.list_events(
        limit=_EVENT_LIMIT, since=_since(days)
    )
    return compute_funnel(events)


@router.get("/api/ops/preferences")
def preferences(request: Request, days: int = 30) -> dict:
    _gate(request)
    events = request.app.state.ops.list_events(
        limit=_EVENT_LIMIT, since=_since(days)
    )
    return compute_preferences(events)


@router.get("/api/ops/ai")
def ai_metrics(request: Request, days: int = 30) -> dict:
    _gate(request)
    events = request.app.state.ops.list_events(
        limit=_EVENT_LIMIT, since=_since(days)
    )
    metrics = request.app.state.ops.list_chat_metrics(
        limit=_METRIC_LIMIT, since=_since(days)
    )
    return compute_ai_metrics(events, metrics)


@router.get("/api/ops/events")
def events(
    request: Request,
    event_name: str | None = None,
    limit: int = 200,
) -> dict:
    _gate(request)
    limit = min(max(1, limit), 2000)
    rows = request.app.state.ops.list_events(event_name=event_name, limit=limit)
    return {"count": len(rows), "events": [e.to_public() for e in rows]}


@router.get("/api/ops/feedback")
def feedback(request: Request) -> dict:
    _gate(request)
    notes = request.app.state.auth_service.list_developer_notes()
    analyses = request.app.state.feedback_store.list_analyses()
    annotations = request.app.state.feedback_store.list_annotations()
    precision = FeedbackEvaluator(request.app.state.feedback_store).precision()
    return {
        "notes": [
            {
                "note_key": n.session_id,
                "user_id": n.user_id,
                "display_name": n.display_name,
                "label": n.label,
                "character_id": n.character_id,
                "content": n.content,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ],
        "analyses": [a.to_public() for a in analyses],
        "annotations": [a.to_public() for a in annotations],
        "precision": precision,
    }


class AnalyzeRequest(BaseModel):
    max_items: int = Field(default=200, ge=1, le=500)


@router.post("/api/ops/feedback/analyze")
def analyze(payload: AnalyzeRequest, request: Request) -> dict:
    _gate(request)
    try:
        done = request.app.state.feedback_classifier.classify_pending(
            max_items=payload.max_items
        )
    except Exception:  # 分类失败绝不影响游戏；向上如实报错
        logger.exception("feedback classification batch failed")
        raise HTTPException(status_code=500, detail="feedback classification failed")
    return {
        "analyzed": len(done),
        "failed": sum(1 for a in done if a.status == "failed"),
    }


class AnnotateRequest(BaseModel):
    note_key: str = Field(min_length=1, max_length=64)
    topic_correct: bool
    severity_correct: bool
    annotator: str = Field(default="human", max_length=64)


@router.post("/api/ops/feedback/annotate")
def annotate(payload: AnnotateRequest, request: Request) -> dict:
    _gate(request)
    evaluator = FeedbackEvaluator(request.app.state.feedback_store)
    annotation = evaluator.annotate(
        payload.note_key,
        topic_correct=payload.topic_correct,
        severity_correct=payload.severity_correct,
        annotator=payload.annotator,
    )
    return {"annotation": annotation.to_public()}
