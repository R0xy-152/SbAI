from __future__ import annotations

from fastapi import HTTPException, Request


def current_user_id(request: Request, legacy_player_id: str | None = None) -> str | None:
    # Legacy player_id is accepted only when authentication is explicitly off
    # (isolated old tests/local fixtures). Production always ignores it.
    if request.app.state.auth_disabled:
        return legacy_player_id
    return request.state.user.id


def require_owned_session(request: Request, session_id: str | None) -> None:
    if session_id is None or request.app.state.auth_disabled:
        return
    if not request.app.state.auth_service.repository.owns_game_session(
        request.state.user.id, session_id
    ):
        raise HTTPException(status_code=404, detail="unknown session")


def bind_session(request: Request, session_id: str) -> None:
    if request.app.state.auth_disabled:
        return
    if not request.app.state.auth_service.repository.bind_game_session(
        request.state.user.id, session_id
    ):
        raise HTTPException(status_code=404, detail="unknown session")
