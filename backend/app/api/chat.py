"""POST /api/chat — TV-04 chat turn.

Delegates to the Game Orchestrator, which resolves the session and calls the
current character runtime. The API layer stays free of persona and provider
details (docs/02 §12).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.game.orchestrator import CharacterUnavailable, GameOrchestrator
from app.providers.base import ProviderError

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = None
    # TV-09: explicit character selection (docs/04 §61: natural-language
    # speaker detection is an Orchestrator/Narrative decision, deferred).
    # Defaults to the orchestrator's default character.
    character_id: str | None = None


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


class OpeningRequest(BaseModel):
    session_id: str | None = None


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
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    try:
        result = orchestrator.handle_turn(
            payload.session_id, message, character_id=payload.character_id
        )
    except ProviderError as exc:
        # docs/04 §55: a provider failure is a recoverable error, not a reason
        # to fabricate a reply. The player can retry.
        raise HTTPException(status_code=503, detail="character provider unavailable") from exc
    except CharacterUnavailable as exc:
        # Presence Gate (docs/03 §13.6): the character is not interactable yet.
        # 403 (not 400) — the request is well-formed but not currently permitted.
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    )


@router.post("/api/chat/opening", response_model=ChatResponse)
def opening(
    payload: OpeningRequest,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """The session's active opening line (docs/01 §4), spoken without player
    input. Idempotent: an already-opened session returns an empty dialogue."""
    result = orchestrator.open_turn(payload.session_id)
    return ChatResponse(
        session_id=result.session_id,
        character_id=result.response.character_id,
        dialogue=result.response.dialogue,
        message_count=result.message_count,
        emotion=result.response.emotion,
        animation=result.response.animation_proposal,
        presentation=[" ".join(result.presentation)] if result.presentation else [],
    )


@router.get("/api/chat/history", response_model=HistoryResponse)
def history(
    session_id: str,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> HistoryResponse:
    """The current session's dialogue, for the Frontend History view
    (docs/01 §18: 说话角色 / 对话文本 / 顺序). An unknown id is a 404, never
    a fresh session."""
    try:
        messages = orchestrator.get_history(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HistoryResponse(
        session_id=session_id,
        messages=[HistoryMessage(**message) for message in messages],
    )
