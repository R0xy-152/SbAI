"""Server-side account administration.

Run inside backend container, for example:
  python -m app.auth.cli create --name "Demo 01"
"""

from __future__ import annotations

import argparse
import os
import sys

from app.auth import AuthService, PostgresAuthRepository


def _service() -> AuthService:
    dsn = os.environ.get("GAL_POSTGRES_DSN")
    secret = os.environ.get("GAL_AUTH_SECRET")
    if not dsn or not secret:
        raise SystemExit("GAL_POSTGRES_DSN and GAL_AUTH_SECRET are required")
    return AuthService(PostgresAuthRepository(dsn), secret)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage invite accounts")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create an account and print its invite once")
    create.add_argument("--name", required=True)
    create.add_argument("--quota", type=int, default=100)

    sub.add_parser("list", help="list accounts without invite digests")
    sub.add_parser("usage", help="show per-account usage (quota, logins, active sessions)")

    add = sub.add_parser("add-quota", help="increase permanent quota")
    add.add_argument("user_id")
    add.add_argument("amount", type=int)

    status = sub.add_parser("disable", help="disable an account immediately")
    status.add_argument("user_id")

    enable = sub.add_parser("enable", help="enable a disabled account")
    enable.add_argument("user_id")

    rotate = sub.add_parser("rotate-code", help="replace and print the invite once")
    rotate.add_argument("user_id")

    revoke = sub.add_parser("revoke-sessions", help="log out every device")
    revoke.add_argument("user_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    service = _service()
    repository = service.repository

    if args.command == "create":
        user, invite = service.create_user(args.name, args.quota)
        print(f"user_id={user.id}")
        print(f"display_name={user.display_name}")
        print(f"invite_code={invite}")
        print("The invite code cannot be recovered from the database.")
        return 0

    if args.command == "list":
        for user in repository.list_users():
            print(
                f"{user.id}\t{user.status}\t{user.quota_used}/{user.quota_total}"
                f"\t{user.display_name}"
            )
        return 0

    if args.command == "usage":
        for usage in repository.usage_stats():
            last_login = (
                usage.last_login_at.strftime("%Y-%m-%d %H:%M:%S")
                if usage.last_login_at else "-"
            )
            print(
                f"{usage.display_name}\t{usage.status}\t"
                f"{usage.quota_used}/{usage.quota_total}\t"
                f"logins={usage.login_count}\tactive={usage.active_sessions}\t"
                f"game_sessions={usage.game_sessions}\tlast_login={last_login}"
            )
        return 0

    if args.command == "add-quota":
        if args.amount <= 0:
            raise SystemExit("amount must be positive")
        user = repository.add_quota(args.user_id, args.amount)
    elif args.command in {"disable", "enable"}:
        user = repository.set_status(
            args.user_id, "DISABLED" if args.command == "disable" else "ACTIVE"
        )
        if args.command == "disable" and user is not None:
            repository.revoke_all_sessions(args.user_id)
    elif args.command == "rotate-code":
        user, invite = service.rotate_invite(args.user_id)
        repository.revoke_all_sessions(args.user_id)
        print(f"invite_code={invite}")
    elif args.command == "revoke-sessions":
        if repository.get_user(args.user_id) is None:
            user = None
        else:
            count = repository.revoke_all_sessions(args.user_id)
            print(f"revoked={count}")
            return 0
    else:  # pragma: no cover - argparse prevents this
        return 2

    if user is None:
        print("unknown user", file=sys.stderr)
        return 1
    print(
        f"user_id={user.id} status={user.status} "
        f"quota={user.quota_used}/{user.quota_total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
