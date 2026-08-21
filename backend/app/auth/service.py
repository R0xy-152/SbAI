from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.auth.repository import AuthRepository, UserRecord


class InvalidInvite(Exception):
    pass


class QuotaExhausted(Exception):
    pass


class AuthService:
    def __init__(self, repository: AuthRepository, secret: str, session_days: int = 30) -> None:
        if not secret:
            raise ValueError("GAL_AUTH_SECRET must not be empty")
        self.repository = repository
        self._secret = secret.encode("utf-8")
        self.session_days = session_days

    @staticmethod
    def generate_invite() -> str:
        raw = base64.b32encode(secrets.token_bytes(16)).decode("ascii").rstrip("=")
        return "-".join(raw[index:index + 4] for index in range(0, len(raw), 4))

    @staticmethod
    def _normalize_invite(invite: str) -> str:
        return "".join(character for character in invite.upper() if character not in " -\t\r\n")

    def invite_digest(self, invite: str) -> str:
        normalized = self._normalize_invite(invite)
        return hmac.new(self._secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_user(self, display_name: str, quota: int = 100) -> tuple[UserRecord, str]:
        if not display_name.strip():
            raise ValueError("display name must not be empty")
        if quota < 0:
            raise ValueError("quota must be non-negative")
        invite = self.generate_invite()
        user = UserRecord(
            id=uuid.uuid4().hex,
            display_name=display_name.strip(),
            invite_code_digest=self.invite_digest(invite),
            status="ACTIVE",
            quota_total=quota,
            quota_used=0,
            created_at=datetime.now(timezone.utc),
        )
        self.repository.create_user(user)
        return user, invite

    def login(self, invite: str) -> tuple[UserRecord, str, datetime]:
        normalized = self._normalize_invite(invite)
        if not normalized:
            raise InvalidInvite()
        user = self.repository.find_by_invite(self.invite_digest(normalized))
        if user is None or user.status != "ACTIVE":
            raise InvalidInvite()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.session_days)
        self.repository.record_login(user.id, self.token_digest(token), expires_at)
        refreshed = self.repository.get_user(user.id)
        return refreshed or user, token, expires_at

    def authenticate(self, token: str | None) -> UserRecord | None:
        if not token:
            return None
        return self.repository.user_for_session(
            self.token_digest(token), datetime.now(timezone.utc)
        )

    def logout(self, token: str | None) -> None:
        if token:
            self.repository.revoke_session(self.token_digest(token))

    def reserve_quota(self, user_id: str) -> int:
        remaining = self.repository.reserve_quota(user_id)
        if remaining is None:
            raise QuotaExhausted()
        return remaining

    def refund_quota(self, user_id: str) -> int:
        return self.repository.refund_quota(user_id)

    def rotate_invite(self, user_id: str) -> tuple[UserRecord, str]:
        invite = self.generate_invite()
        user = self.repository.rotate_invite(user_id, self.invite_digest(invite))
        if user is None:
            raise KeyError(user_id)
        return user, invite
