"""POST /api/chat — TV-04 chat turn.

Delegates to the Game Orchestrator, which resolves the session and calls the
current character runtime. The API layer stays free of persona and provider
details (docs/02 §12).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.authz import bind_session, current_user_id, require_owned_session
from app.auth import QuotaExhausted
from app.game.orchestrator import CharacterUnavailable, GameOrchestrator
from app.providers.base import ProviderError

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = None
    # Internal compatibility override. The public UI deliberately omits this:
    # the Orchestrator asks the connected model to propose an in-scene speaker
    # and validates that proposal against authoritative presence state.
    character_id: str | None = None
    # docs/13 §15: the anonymous browser namespace the Auto Save side effect
    # (docs/13 §21, Task 8) binds to this session. Not a security boundary.
    player_id: str | None = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    session_id: str
    character_id: str
    dialogue: str
    message_count: int
    # TV-16: the speaking character's presentation, surfaced so the Frontend
    # can act on it (docs/02 §7: 根据Backend结果切换表情 / 播放允许的动画).
    emotion: str = "neutral"
    animation: str = "none"
    # TV-16: story-semantic directives from a committed narrative event
    # (docs/03 §13.6), e.g. ["SHOW_CHARACTER claude"]; empty on noop turns.
    presentation: list[str] = []
    # docs/12 §13: the structured presentation channel (registered action types
    # only). The Frontend prefers this over the flat legacy strings.
    presentation_actions: list[dict] = []
    claim_refs: list[str] = []
    script_sequence: list[dict] = []
    # Co-presence interjections (docs/04 §60): supplementary replies from other
    # present characters, in presentation order after the primary reply.
    interjections: list[dict] = []
    quota_remaining: int


class OpeningRequest(BaseModel):
    session_id: str | None = None
    # docs/13 §15 / §21: the anonymous browser namespace for the opening
    # checkpoint auto save (Task 8).
    player_id: str | None = Field(default=None, max_length=64)


class HistoryMessage(BaseModel):
    role: str
    character_id: str | None = None
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]


def get_orchestrator(request: Request) -> GameOrchestrator:
    return request.app.state.orchestrator


@router.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    require_owned_session(request, payload.session_id)
    user_id = current_user_id(request, payload.player_id)
    reserved = False
    if not request.app.state.auth_disabled:
        try:
            quota_remaining = request.app.state.auth_service.reserve_quota(user_id)
            reserved = True
        except QuotaExhausted as exc:
            raise HTTPException(status_code=429, detail="AI dialogue quota exhausted") from exc
    else:
        quota_remaining = request.state.user.quota_remaining

    try:
        result = orchestrator.handle_turn(
            payload.session_id,
            message,
            character_id=payload.character_id,
            player_id=user_id,
        )
    except ProviderError as exc:
        # docs/04 §55: a provider failure is a recoverable error, not a reason
        # to fabricate a reply. The player can retry.
        # 真机接入复盘：503 的根因必须落到日志，否则上游错误不可诊断。
        logger.warning("provider unavailable: %s", exc)
        if reserved:
            request.app.state.auth_service.refund_quota(user_id)
        raise HTTPException(status_code=503, detail="character provider unavailable") from exc
    except CharacterUnavailable as exc:
        # Presence Gate (docs/03 §13.6): the character is not interactable yet.
        # 403 (not 400) — the request is well-formed but not currently permitted.
        if reserved:
            request.app.state.auth_service.refund_quota(user_id)
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        if reserved:
            request.app.state.auth_service.refund_quota(user_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        if reserved:
            request.app.state.auth_service.refund_quota(user_id)
        raise

    try:
        bind_session(request, result.session_id)
    except Exception:
        if reserved:
            request.app.state.auth_service.refund_quota(user_id)
        raise

    return ChatResponse(
        session_id=result.session_id,
        character_id=result.response.character_id,
        dialogue=result.response.dialogue,
        message_count=result.message_count,
        emotion=result.response.emotion,
        animation=result.response.animation_proposal,
        # Each committed event's directive is one string, e.g. "SHOW_CHARACTER
        # claude" (docs/03 §13.6), so the Frontend can parse kind + target.
        presentation=[" ".join(result.presentation)] if result.presentation else [],
        presentation_actions=[a.model_dump() for a in result.presentation_actions],
        claim_refs=result.response.claim_refs,
        script_sequence=[line.__dict__ for line in result.script_sequence],
        interjections=[
            {
                "character_id": interjection.character_id,
                "dialogue": interjection.dialogue,
                "emotion": interjection.emotion,
                "animation": interjection.animation_proposal,
            }
            for interjection in result.interjections
        ],
        quota_remaining=quota_remaining,
    )


@router.post("/api/chat/opening", response_model=ChatResponse)
def opening(
    payload: OpeningRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """The session's active opening line (docs/01 §4), spoken without player
    input. Idempotent: an already-opened session returns an empty dialogue."""
    require_owned_session(request, payload.session_id)
    result = orchestrator.open_turn(
        payload.session_id,
        player_id=current_user_id(request, payload.player_id),
    )
    bind_session(request, result.session_id)
    return ChatResponse(
        session_id=result.session_id,
        character_id=result.response.character_id,
        dialogue=result.response.dialogue,
        message_count=result.message_count,
        emotion=result.response.emotion,
        animation=result.response.animation_proposal,
        presentation=[" ".join(result.presentation)] if result.presentation else [],
        presentation_actions=[a.model_dump() for a in result.presentation_actions],
        claim_refs=result.response.claim_refs,
        script_sequence=[line.__dict__ for line in result.script_sequence],
        quota_remaining=request.state.user.quota_remaining,
    )


@router.get("/api/chat/history", response_model=HistoryResponse)
def history(
    session_id: str,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> HistoryResponse:
    """The current session's dialogue, for the Frontend History view
    (docs/01 §18: 说话角色 / 对话文本 / 顺序). An unknown id is a 404, never
    a fresh session."""
    require_owned_session(request, session_id)
    try:
        messages = orchestrator.get_history(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HistoryResponse(
        session_id=session_id,
        messages=[HistoryMessage(**message) for message in messages],
    )
