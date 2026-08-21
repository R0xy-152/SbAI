from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import InvalidInvite

router = APIRouter()


class LoginRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=128)


def _user_view(user) -> dict:
    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "quota_total": user.quota_total,
        "quota_used": user.quota_used,
        "quota_remaining": user.quota_remaining,
    }


@router.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    try:
        user, token, _ = request.app.state.auth_service.login(payload.invite_code)
    except InvalidInvite as exc:
        raise HTTPException(status_code=401, detail="invalid invite code") from exc
    response.set_cookie(
        key=request.app.state.auth_cookie_name,
        value=token,
        max_age=request.app.state.auth_cookie_max_age,
        httponly=True,
        secure=request.app.state.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return _user_view(user)


@router.get("/api/auth/me")
def me(request: Request) -> dict:
    return _user_view(request.state.user)


@router.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(request.app.state.auth_cookie_name)
    request.app.state.auth_service.logout(token)
    response.delete_cookie(
        request.app.state.auth_cookie_name,
        path="/",
        secure=request.app.state.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}
