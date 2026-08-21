from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import datetime, timezone


AUTH_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id                  TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    invite_code_digest  TEXT NOT NULL UNIQUE,
    status              TEXT NOT NULL CHECK (status IN ('ACTIVE','DISABLED')),
    quota_total         INTEGER NOT NULL CHECK (quota_total >= 0),
    quota_used          INTEGER NOT NULL DEFAULT 0 CHECK (quota_used >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_digest  TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_user ON auth_sessions(user_id);
CREATE TABLE IF NOT EXISTS game_session_owners (
    session_id  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_game_session_owners_user
    ON game_session_owners(user_id);
"""


@dataclass(frozen=True)
class UserRecord:
    id: str
    display_name: str
    invite_code_digest: str
    status: str
    quota_total: int
    quota_used: int
    created_at: datetime
    last_login_at: datetime | None = None

    @property
    def quota_remaining(self) -> int:
        return max(0, self.quota_total - self.quota_used)


class AuthRepository(ABC):
    @abstractmethod
    def create_user(self, user: UserRecord) -> None: ...

    @abstractmethod
    def list_users(self) -> list[UserRecord]: ...

    @abstractmethod
    def get_user(self, user_id: str) -> UserRecord | None: ...

    @abstractmethod
    def find_by_invite(self, digest: str) -> UserRecord | None: ...

    @abstractmethod
    def record_login(self, user_id: str, token_digest: str, expires_at: datetime) -> None: ...

    @abstractmethod
    def user_for_session(self, token_digest: str, now: datetime) -> UserRecord | None: ...

    @abstractmethod
    def revoke_session(self, token_digest: str) -> None: ...

    @abstractmethod
    def revoke_all_sessions(self, user_id: str) -> int: ...

    @abstractmethod
    def reserve_quota(self, user_id: str) -> int | None: ...

    @abstractmethod
    def refund_quota(self, user_id: str) -> int: ...

    @abstractmethod
    def add_quota(self, user_id: str, amount: int) -> UserRecord | None: ...

    @abstractmethod
    def set_status(self, user_id: str, status: str) -> UserRecord | None: ...

    @abstractmethod
    def rotate_invite(self, user_id: str, digest: str) -> UserRecord | None: ...

    @abstractmethod
    def bind_game_session(self, user_id: str, session_id: str) -> bool: ...

    @abstractmethod
    def owns_game_session(self, user_id: str, session_id: str) -> bool: ...


class MemoryAuthRepository(AuthRepository):
    """Thread-safe local/test implementation; production uses PostgreSQL."""

    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}
        self._sessions: dict[str, tuple[str, datetime, datetime | None]] = {}
        self._owners: dict[str, str] = {}
        self._lock = threading.Lock()

    def create_user(self, user: UserRecord) -> None:
        with self._lock:
            if user.id in self._users or any(
                item.invite_code_digest == user.invite_code_digest
                for item in self._users.values()
            ):
                raise ValueError("user or invite already exists")
            self._users[user.id] = user

    def list_users(self) -> list[UserRecord]:
        with self._lock:
            return sorted(self._users.values(), key=lambda user: user.created_at)

    def get_user(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self._users.get(user_id)

    def find_by_invite(self, digest: str) -> UserRecord | None:
        with self._lock:
            return next(
                (user for user in self._users.values() if user.invite_code_digest == digest),
                None,
            )

    def record_login(self, user_id: str, token_digest: str, expires_at: datetime) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            user = self._users[user_id]
            self._users[user_id] = replace(user, last_login_at=now)
            self._sessions[token_digest] = (user_id, expires_at, None)

    def user_for_session(self, token_digest: str, now: datetime) -> UserRecord | None:
        with self._lock:
            session = self._sessions.get(token_digest)
            if session is None:
                return None
            user_id, expires_at, revoked_at = session
            user = self._users.get(user_id)
            if revoked_at is not None or expires_at <= now or user is None or user.status != "ACTIVE":
                return None
            return user

    def revoke_session(self, token_digest: str) -> None:
        with self._lock:
            session = self._sessions.get(token_digest)
            if session is not None:
                self._sessions[token_digest] = (session[0], session[1], datetime.now(timezone.utc))

    def revoke_all_sessions(self, user_id: str) -> int:
        count = 0
        with self._lock:
            now = datetime.now(timezone.utc)
            for digest, session in list(self._sessions.items()):
                if session[0] == user_id and session[2] is None:
                    self._sessions[digest] = (session[0], session[1], now)
                    count += 1
        return count

    def reserve_quota(self, user_id: str) -> int | None:
        with self._lock:
            user = self._users.get(user_id)
            if user is None or user.status != "ACTIVE" or user.quota_used >= user.quota_total:
                return None
            user = replace(user, quota_used=user.quota_used + 1)
            self._users[user_id] = user
            return user.quota_remaining

    def refund_quota(self, user_id: str) -> int:
        with self._lock:
            user = self._users[user_id]
            user = replace(user, quota_used=max(0, user.quota_used - 1))
            self._users[user_id] = user
            return user.quota_remaining

    def add_quota(self, user_id: str, amount: int) -> UserRecord | None:
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
            user = replace(user, quota_total=user.quota_total + amount)
            self._users[user_id] = user
            return user

    def set_status(self, user_id: str, status: str) -> UserRecord | None:
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
            user = replace(user, status=status)
            self._users[user_id] = user
            return user

    def rotate_invite(self, user_id: str, digest: str) -> UserRecord | None:
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
            if any(item.id != user_id and item.invite_code_digest == digest for item in self._users.values()):
                raise ValueError("invite already exists")
            user = replace(user, invite_code_digest=digest)
            self._users[user_id] = user
            return user

    def bind_game_session(self, user_id: str, session_id: str) -> bool:
        with self._lock:
            owner = self._owners.setdefault(session_id, user_id)
            return owner == user_id

    def owns_game_session(self, user_id: str, session_id: str) -> bool:
        with self._lock:
            return self._owners.get(session_id) == user_id


class PostgresAuthRepository(AuthRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._initialized = False
        self._lock = threading.Lock()

    def _ensure_schema(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            import psycopg

            with psycopg.connect(self._dsn) as conn:
                conn.execute(AUTH_SCHEMA_SQL)
            self._initialized = True

    def _conn(self):
        import psycopg

        self._ensure_schema()
        return psycopg.connect(self._dsn)

    @staticmethod
    def _user(row) -> UserRecord | None:
        if row is None:
            return None
        return UserRecord(
            id=row[0], display_name=row[1], invite_code_digest=row[2], status=row[3],
            quota_total=row[4], quota_used=row[5], created_at=row[6], last_login_at=row[7],
        )

    def create_user(self, user: UserRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO users (id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (user.id, user.display_name, user.invite_code_digest, user.status,
                 user.quota_total, user.quota_used, user.created_at, user.last_login_at),
            )

    def list_users(self) -> list[UserRecord]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at FROM users ORDER BY created_at").fetchall()
        return [self._user(row) for row in rows]

    def get_user(self, user_id: str) -> UserRecord | None:
        with self._conn() as conn:
            row = conn.execute("SELECT id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at FROM users WHERE id=%s", (user_id,)).fetchone()
        return self._user(row)

    def find_by_invite(self, digest: str) -> UserRecord | None:
        with self._conn() as conn:
            row = conn.execute("SELECT id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at FROM users WHERE invite_code_digest=%s", (digest,)).fetchone()
        return self._user(row)

    def record_login(self, user_id: str, token_digest: str, expires_at: datetime) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE users SET last_login_at=NOW() WHERE id=%s", (user_id,))
            conn.execute("INSERT INTO auth_sessions (token_digest,user_id,expires_at) VALUES (%s,%s,%s)", (token_digest, user_id, expires_at))

    def user_for_session(self, token_digest: str, now: datetime) -> UserRecord | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT u.id,u.display_name,u.invite_code_digest,u.status,u.quota_total,u.quota_used,u.created_at,u.last_login_at FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_digest=%s AND s.revoked_at IS NULL AND s.expires_at>%s AND u.status='ACTIVE'",
                (token_digest, now),
            ).fetchone()
        return self._user(row)

    def revoke_session(self, token_digest: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE auth_sessions SET revoked_at=COALESCE(revoked_at,NOW()) WHERE token_digest=%s", (token_digest,))

    def revoke_all_sessions(self, user_id: str) -> int:
        with self._conn() as conn:
            cur = conn.execute("UPDATE auth_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL", (user_id,))
        return cur.rowcount

    def reserve_quota(self, user_id: str) -> int | None:
        with self._conn() as conn:
            row = conn.execute(
                "UPDATE users SET quota_used=quota_used+1 WHERE id=%s AND status='ACTIVE' AND quota_used<quota_total RETURNING quota_total-quota_used",
                (user_id,),
            ).fetchone()
        return int(row[0]) if row is not None else None

    def refund_quota(self, user_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "UPDATE users SET quota_used=GREATEST(0,quota_used-1) WHERE id=%s RETURNING quota_total-quota_used",
                (user_id,),
            ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return int(row[0])

    def add_quota(self, user_id: str, amount: int) -> UserRecord | None:
        with self._conn() as conn:
            row = conn.execute(
                "UPDATE users SET quota_total=quota_total+%s WHERE id=%s RETURNING id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at",
                (amount, user_id),
            ).fetchone()
        return self._user(row)

    def set_status(self, user_id: str, status: str) -> UserRecord | None:
        with self._conn() as conn:
            row = conn.execute(
                "UPDATE users SET status=%s WHERE id=%s RETURNING id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at",
                (status, user_id),
            ).fetchone()
        return self._user(row)

    def rotate_invite(self, user_id: str, digest: str) -> UserRecord | None:
        with self._conn() as conn:
            row = conn.execute(
                "UPDATE users SET invite_code_digest=%s WHERE id=%s RETURNING id,display_name,invite_code_digest,status,quota_total,quota_used,created_at,last_login_at",
                (digest, user_id),
            ).fetchone()
        return self._user(row)

    def bind_game_session(self, user_id: str, session_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("INSERT INTO game_session_owners (session_id,user_id) VALUES (%s,%s) ON CONFLICT (session_id) DO NOTHING", (session_id, user_id))
            row = conn.execute("SELECT user_id FROM game_session_owners WHERE session_id=%s", (session_id,)).fetchone()
        return row is not None and row[0] == user_id

    def owns_game_session(self, user_id: str, session_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM game_session_owners WHERE session_id=%s AND user_id=%s", (session_id, user_id)).fetchone()
        return row is not None
