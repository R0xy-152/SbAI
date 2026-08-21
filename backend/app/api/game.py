"""Backend-authoritative physical scene actions (docs/01 §4)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.chat import get_orchestrator
from app.api.authz import bind_session, current_user_id, require_owned_session
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
    presentation: list[str] = []
    presentation_actions: list[dict] = []


class PresentEvidenceRequest(BaseModel):
    session_id: str
    character_id: str
    evidence_id: str


class PresentEvidenceResponse(BaseModel):
    session_id: str
    event: str
    character_id: str
    evidence: dict


class DeductionRequest(BaseModel):
    session_id: str
    message: str
    # docs/13 §15 / §21: the anonymous browser namespace for the INF01 / INF03
    # checkpoint auto saves (Task 8).
    player_id: str | None = Field(default=None, max_length=64)


class PrivateInterviewChallengeRequest(BaseModel):
    session_id: str
    character_id: str
    claim_ids: list[str] = []
    evidence_ids: list[str] = []
    statement_index: int | None = None


class RecoveryActionRequest(BaseModel):
    session_id: str
    action: Literal["PREVIEW", "VERIFY", "PROTECT", "REPAIR", "OPTIMIZE"]
    target: str
    actor: Literal["player", "deepseek", "claude", "chatgpt", "doubao"]


class TestimonyRequest(BaseModel):
    session_id: str
    character_id: Literal["deepseek", "claude", "doubao", "chatgpt"]

class CleanupRequest(BaseModel):
    session_id: str
    action: Literal["DELEGATE", "DELETE_DEEPSEEK", "DELETE_CLAUDE", "DELETE_DOUBAO", "CONFIRM_KEEP_CHATGPT"]


@router.post("/api/game/action", response_model=InvestigationActionResponse)
def investigation_action(
    payload: InvestigationActionRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> InvestigationActionResponse:
    require_owned_session(request, payload.session_id)
    try:
        result = orchestrator.handle_investigation_action(
            payload.session_id, payload.action, payload.hotspot_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bind_session(request, result.session_id)
    return InvestigationActionResponse(**result.__dict__)


@router.get("/api/game/state")
def investigation_state(
    session_id: str,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> dict:
    require_owned_session(request, session_id)
    try:
        return orchestrator.get_investigation_state(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/game/evidence")
def evidence_list(
    session_id: str,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> list[dict]:
    require_owned_session(request, session_id)
    try:
        return orchestrator.get_evidence(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/game/present", response_model=PresentEvidenceResponse)
def present_evidence(
    payload: PresentEvidenceRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> PresentEvidenceResponse:
    require_owned_session(request, payload.session_id)
    try:
        result = orchestrator.present_evidence(
            payload.session_id, payload.character_id, payload.evidence_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PresentEvidenceResponse(**result.__dict__)


@router.post("/api/game/deduction")
def deduction(
    payload: DeductionRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> dict:
    require_owned_session(request, payload.session_id)
    try:
        return orchestrator.submit_deduction(
            payload.session_id,
            payload.message,
            player_id=current_user_id(request, payload.player_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/game/private-interview/challenge")
def private_interview_challenge(
    payload: PrivateInterviewChallengeRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> dict:
    require_owned_session(request, payload.session_id)
    try:
        return orchestrator.submit_private_interview_challenge(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/game/recovery/start")
def recovery_start(session_id: str, request: Request, orchestrator: GameOrchestrator = Depends(get_orchestrator)) -> dict:
    require_owned_session(request, session_id)
    try:
        return orchestrator.start_recovery(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/game/recovery/action")
def recovery_action(payload: RecoveryActionRequest, request: Request, orchestrator: GameOrchestrator = Depends(get_orchestrator)) -> dict:
    require_owned_session(request, payload.session_id)
    try:
        return orchestrator.recovery_action(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/game/security-review/start")
def security_review_start(session_id: str, request: Request, orchestrator: GameOrchestrator = Depends(get_orchestrator)) -> dict:
    require_owned_session(request, session_id)
    try:
        return orchestrator.start_security_review(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/game/security-review/testify")
def security_review_testify(payload: TestimonyRequest, request: Request, orchestrator: GameOrchestrator = Depends(get_orchestrator)) -> dict:
    require_owned_session(request, payload.session_id)
    try:
        return orchestrator.testify(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/game/security-review/cleanup")
def security_review_cleanup(payload: CleanupRequest, request: Request, orchestrator: GameOrchestrator = Depends(get_orchestrator)) -> dict:
    require_owned_session(request, payload.session_id)
    try:
        return orchestrator.cleanup(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/game/security-review/reject-cleanup")
def security_review_reject_cleanup(session_id: str, request: Request, orchestrator: GameOrchestrator = Depends(get_orchestrator)) -> dict:
    require_owned_session(request, session_id)
    try:
        return orchestrator.reject_cleanup(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
