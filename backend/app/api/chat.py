"""POST /api/chat — TV-04 chat turn.

Delegates to the Game Orchestrator, which resolves the session and calls the
current character runtime. The API layer stays free of persona and provider
details (docs/02 §12).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.game.orchestrator import GameOrchestrator
from app.providers.base import ProviderError

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    character_id: str
    dialogue: str
    message_count: int


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
        result = orchestrator.handle_turn(payload.session_id, message)
    except ProviderError as exc:
        # docs/04 §55: a provider failure is a recoverable error, not a reason
        # to fabricate a reply. The player can retry.
        raise HTTPException(status_code=503, detail="character provider unavailable") from exc

    return ChatResponse(
        session_id=result.session_id,
        character_id=result.response.character_id,
        dialogue=result.response.dialogue,
        message_count=result.message_count,
    )
