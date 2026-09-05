"""Thin HTTP adapter for the isolated trial_v2 runtime (docs/27)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.authz import bind_session, current_user_id, require_owned_session
from app.game.orchestrator import GameOrchestrator

router = APIRouter()


class _CommandBase(BaseModel):
    command_id: str = Field(min_length=1, max_length=64)


class AdvanceCommand(_CommandBase):
    type: Literal["ADVANCE"]


class PlayerInputCommand(_CommandBase):
    type: Literal["PLAYER_INPUT"]
    message: str = Field(min_length=1, max_length=2000)


class ShardPose(BaseModel):
    shard_id: str = Field(min_length=1, max_length=32)
    x: float
    y: float
    rotation: float


class CompleteShatterCommand(_CommandBase):
    type: Literal["COMPLETE_SHATTER"]
    shards: list[ShardPose] = Field(min_length=4, max_length=4)


class SubmitReasoningCommand(_CommandBase):
    type: Literal["SUBMIT_REASONING"]
    deduction_id: str = Field(min_length=1, max_length=64)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)
    message: str = Field(min_length=1, max_length=4000)


class PermissionResponseCommand(_CommandBase):
    type: Literal["PERMISSION_RESPONSE"]
    permission_id: str = Field(min_length=1, max_length=64)
    grant: bool


class ChooseCommand(_CommandBase):
    type: Literal["CHOOSE"]
    option_id: str = Field(min_length=1, max_length=64)


class SubmitJudgmentCommand(_CommandBase):
    type: Literal["SUBMIT_JUDGMENT"]
    judgment_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


TrialCommand = Annotated[
    AdvanceCommand
    | PlayerInputCommand
    | CompleteShatterCommand
    | SubmitReasoningCommand
    | PermissionResponseCommand
    | ChooseCommand
    | SubmitJudgmentCommand,
    Field(discriminator="type"),
]


class TrialCommandRequest(BaseModel):
    session_id: str | None = None
    player_id: str | None = Field(default=None, min_length=1, max_length=64)
    command: TrialCommand


def get_orchestrator(request: Request) -> GameOrchestrator:
    return request.app.state.orchestrator


@router.get("/api/trial/current")
def trial_current(
    request: Request,
    session_id: str | None = None,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> dict:
    require_owned_session(request, session_id)
    try:
        view = orchestrator.trial_current(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bind_session(request, view["session_id"])
    return view


@router.post("/api/trial/command")
def trial_command(
    payload: TrialCommandRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
) -> dict:
    require_owned_session(request, payload.session_id)
    try:
        view = orchestrator.trial_handle(
            payload.session_id,
            payload.command.model_dump(),
            player_id=current_user_id(request, payload.player_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bind_session(request, view["session_id"])
    return view
