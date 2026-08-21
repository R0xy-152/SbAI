"""快速上线固定剧本 API（临时组件，对应 story_runtime.py）。

停用 AI 回复期间，前端只用这三个端点推进剧本：
- GET  /api/story/current?session_id=...   —— 刷新/读档后恢复当前展示节点
- POST /api/story/advance {session_id?, player_id?} —— 「继续」：下一节点
- POST /api/story/choose {session_id, option_id, player_id?} —— 选项 A/B/C

session_id 为空时 advance 由 orchestrator 铸造新会话（与 /api/chat 同约定）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.authz import bind_session, current_user_id, require_owned_session
from app.game.orchestrator import GameOrchestrator

router = APIRouter()


class StoryAdvanceRequest(BaseModel):
    session_id: str | None = None
    # docs/13 §15：匿名浏览器命名空间，供场景边界 AUTO 自动存档绑定。
    player_id: str | None = Field(default=None, max_length=64)


class StoryChooseRequest(BaseModel):
    session_id: str
    option_id: str = Field(min_length=1, max_length=64)
    player_id: str | None = Field(default=None, max_length=64)


class StoryNodeView(BaseModel):
    kind: str
    speaker: str | None = None
    text: str | None = None
    emotion: str | None = None
    choice_id: str | None = None
    scene_id: str | None = None
    options: list[dict] = []


class StoryView(BaseModel):
    session_id: str
    started: bool
    finished: bool
    node: StoryNodeView | None = None
    # 当前节点所属场景的标题与演出指令（纯表现数据；end 节点为 None）
    scene: dict | None = None
    scene_changed: bool = False


def get_orchestrator(request: Request) -> GameOrchestrator:
    return request.app.state.orchestrator


@router.get("/api/story/current", response_model=StoryView)
def story_current(
    request: Request,
    session_id: str | None = None,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> StoryView:
    """当前展示节点。不移动游标；未知会话由 orchestrator 铸造新会话（游标
    未开始，前端随后用 advance 起步）。"""
    require_owned_session(request, session_id)
    try:
        view = orchestrator.story_current(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bind_session(request, view["session_id"])
    return StoryView(**view)


@router.post("/api/story/advance", response_model=StoryView)
def story_advance(
    payload: StoryAdvanceRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> StoryView:
    """「继续」：移动到下一节点。首次调用即开始故事。"""
    require_owned_session(request, payload.session_id)
    try:
        view = orchestrator.story_advance(
            payload.session_id, player_id=current_user_id(request, payload.player_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bind_session(request, view["session_id"])
    return StoryView(**view)


@router.post("/api/story/choose", response_model=StoryView)
def story_choose(
    payload: StoryChooseRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> StoryView:
    """提交一个 A/B/C 选项，返回该选项的第一句台词。"""
    require_owned_session(request, payload.session_id)
    try:
        view = orchestrator.story_choose(
            payload.session_id,
            payload.option_id,
            player_id=current_user_id(request, payload.player_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StoryView(**view)
