"""Backend-authoritative physical scene actions (docs/01 §4)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.chat import get_orchestrator
from app.game.orchestrator import GameOrchestrator

router = APIRouter()


class InvestigationActionRequest(BaseModel):
    session_id: str | None = None
    action: Literal["INSPECT_HOTSPOT", "PAPER_RUBBING_COMPLETE"]
    hotspot_id: str


class InvestigationActionResponse(BaseModel):
    session_id: str
    outcome: str
    hotspot_id: str
    evidence_id: str | None = None
    state: dict


@router.post("/api/game/action", response_model=InvestigationActionResponse)
def investigation_action(
    payload: InvestigationActionRequest,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> InvestigationActionResponse:
    try:
        result = orchestrator.handle_investigation_action(
            payload.session_id, payload.action, payload.hotspot_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InvestigationActionResponse(**result.__dict__)


@router.get("/api/game/state")
def investigation_state(
    session_id: str,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> dict:
    try:
        return orchestrator.get_investigation_state(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
