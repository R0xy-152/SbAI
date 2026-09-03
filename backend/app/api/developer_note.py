"""POST /api/developer-note —— 收集序章「对开发者的话」（docs/20）。

玩家在序章自由聊天前，由所选角色问固定语义问句；此端点把玩家的留言落库
（并可选推送到开发者 webhook），不扣 AI 额度、不调用 LLM。
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.authz import current_user_id, require_owned_session
from app.auth import DeveloperNote
from app.game.orchestrator import GameOrchestrator
from app.script.developer_note import DEVELOPER_NOTE_ACKNOWLEDGEMENT

logger = logging.getLogger(__name__)

router = APIRouter()


class DeveloperNoteRequest(BaseModel):
    session_id: str
    # 留空 = 跳过留言（前端「跳过」按钮或空提交）。
    message: str = Field(default="", max_length=500)
    player_id: str | None = Field(default=None, max_length=64)


class DeveloperNoteResponse(BaseModel):
    session_id: str
    stored: bool
    character_id: str
    acknowledgement: str


def get_orchestrator(request: Request) -> GameOrchestrator:
    return request.app.state.orchestrator


def _push_webhook(note: DeveloperNote) -> None:
    """可选：把留言推到飞书/企业微信 webhook（GAL_DEVELOPER_NOTE_WEBHOOK）。

    通过 GAL_DEVELOPER_NOTE_WEBHOOK_KIND 选择报文格式（feishu 默认 / wecom），
    两种机器人的 text 消息结构不同，无法用同一份 JSON（docs/20 §4）。
    尽力而为：失败只记日志，绝不影响留言落库；后台线程 fire-and-forget，
    不阻塞玩家提交。
    """
    webhook = os.environ.get("GAL_DEVELOPER_NOTE_WEBHOOK", "").strip()
    if not webhook:
        return
    kind = os.environ.get("GAL_DEVELOPER_NOTE_WEBHOOK_KIND", "feishu").strip().lower()
    text = (
        f"【对开发者的话】{note.display_name}"
        f"（{note.label or '未分组'} / {note.character_id}）：{note.content}"
    )
    if kind in {"wecom", "wechat_work", "企业微信"}:
        payload = {"msgtype": "text", "text": {"content": text}}
    else:
        payload = {"msg_type": "text", "content": {"text": text}}

    def _send() -> None:
        try:
            httpx.post(webhook, json=payload, timeout=5.0)
        except Exception:  # noqa: BLE001 - best effort
            logger.warning("developer note webhook push failed", exc_info=True)

    threading.Thread(target=_send, daemon=True).start()


@router.post("/api/developer-note", response_model=DeveloperNoteResponse)
def submit_developer_note(
    payload: DeveloperNoteRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> DeveloperNoteResponse:
    message = payload.message.strip()
    require_owned_session(request, payload.session_id)
    user = request.state.user
    try:
        character_id = orchestrator.developer_note_character(
            payload.session_id,
            player_id=current_user_id(request, payload.player_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = bool(message)
    if stored:
        note = DeveloperNote(
            user_id=user.id,
            display_name=user.display_name,
            label=getattr(user, "label", None),
            character_id=character_id,
            content=message,
            session_id=payload.session_id,
            created_at=datetime.now(timezone.utc),
        )
        # docs/20 §4：先落库、后清 pending。落库成功才推送；落库失败则 pending
        # 保持 True，玩家可重试（code review：Spec c）。
        if request.app.state.auth_service.add_developer_note(note):
            _push_webhook(note)
    orchestrator.complete_developer_note(payload.session_id)

    return DeveloperNoteResponse(
        session_id=payload.session_id,
        stored=stored,
        character_id=character_id,
        acknowledgement=DEVELOPER_NOTE_ACKNOWLEDGEMENT if stored else "已跳过留言。",
    )
