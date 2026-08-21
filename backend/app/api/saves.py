"""Save API (docs/13 §20).

Backend-authoritative Save Capture: the Frontend sends only player_id /
session_id / slot_index — the snapshot is produced by the SaveSnapshotService
from the orchestrator's canonical state (docs/13 §14.2, §20.2). Load returns
a new_session_id + initial GameViewState (docs/13 §20.3). Snapshot content is
never shipped to the browser (docs/13 §29): list endpoints return slot
metadata only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.chat import get_orchestrator
from app.api.authz import bind_session, current_user_id, require_owned_session
from app.game.orchestrator import GameOrchestrator
from app.save import SaveSnapshotService
from app.save.service import SaveLoadError, SaveSchemaError

router = APIRouter()


def get_save_service(request: Request) -> SaveSnapshotService:
    return request.app.state.save_service


class ManualSaveRequest(BaseModel):
    player_id: str | None = Field(default=None, min_length=1, max_length=64)
    session_id: str
    title: str | None = None


class AutoSaveRequest(BaseModel):
    player_id: str | None = Field(default=None, min_length=1, max_length=64)
    session_id: str


class LoadRequest(BaseModel):
    player_id: str | None = Field(default=None, min_length=1, max_length=64)


@router.get("/api/saves")
def list_saves(
    request: Request,
    player_id: str | None = None,
    save_service: SaveSnapshotService = Depends(get_save_service),
) -> dict:
    """docs/13 §20.1: {auto, manual:[6]} — slot metadata only, no snapshot."""
    try:
        return save_service.list_saves(current_user_id(request, player_id))
    except ValueError as exc:
        # T2review P1-2：非法 player_id（如路径穿越串）明确拒绝
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/saves/manual/{slot}")
def manual_save(
    slot: int,
    payload: ManualSaveRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
    save_service: SaveSnapshotService = Depends(get_save_service),
) -> dict:
    """docs/13 §20.2: save to one manual slot; snapshot is backend-captured."""
    try:
        require_owned_session(request, payload.session_id)
        save = save_service.save_manual(
            orchestrator,
            current_user_id(request, payload.player_id),
            payload.session_id,
            slot,
            title=payload.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return save.info()


@router.post("/api/saves/auto")
def auto_save(
    payload: AutoSaveRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
    save_service: SaveSnapshotService = Depends(get_save_service),
) -> dict:
    """docs/13 §21：覆盖唯一 AUTO slot。T2review P1-6 修复：AUTO 是确定性
    checkpoint 槽——没有新 checkpoint 的普通回合请求被拒绝（409）。"""
    try:
        require_owned_session(request, payload.session_id)
        save = save_service.save_auto(
            orchestrator, current_user_id(request, payload.player_id), payload.session_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return save.info()


@router.post("/api/saves/{save_id}/load")
def load_save(
    save_id: str,
    payload: LoadRequest,
    request: Request,
    orchestrator: GameOrchestrator = Depends(get_orchestrator),
    save_service: SaveSnapshotService = Depends(get_save_service),
) -> dict:
    """docs/13 §20.3: create a NEW Active Session from the save snapshot and
    return new_session_id + initial GameViewState."""
    try:
        result = save_service.load_save(
            orchestrator, current_user_id(request, payload.player_id), save_id
        )
        bind_session(request, result["session_id"])
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SaveSchemaError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (SaveLoadError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/api/saves/manual/{slot}")
def delete_manual_save(
    slot: int,
    request: Request,
    player_id: str | None = None,
    save_service: SaveSnapshotService = Depends(get_save_service),
) -> dict:
    """Delete one manual slot (docs/13 §26.3)."""
    try:
        deleted = save_service.delete_manual(current_user_id(request, player_id), slot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": deleted}
