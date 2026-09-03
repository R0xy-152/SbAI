"""生成「二维码直达登录」物料（档位 B，docs/18 评估）。

把 invite-codes.md 里的邀请码逐一编码成
  https://sbai.xin/login#invite=<邀请码>
的二维码 PNG；扫码即自动登录直达标题/开始界面（前端 LoginView 读
route.hash 自动登录，见 frontend-vue/src/views/LoginView.vue）。

邀请码放片段（#）里：不出浏览器，不进 nginx/Caddy 访问日志、不进 Referer。

用法：
    backend/.venv/bin/python deploy/gen_invite_qr.py \
        --invite-codes invite-codes.md \
        --base https://sbai.xin \
        --out deploy/invite-qr

注意：明文邀请码只在建号/轮换时打印一次、DB 只存 HMAC。本脚本依赖
invite-codes.md 台账；请确保台账与线上实际账号（auth.cli list）同步，
否则扫码会 401。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import segno


def load_invite_codes(path: Path) -> list[tuple[str, str]]:
    """解析 invite-codes.md 的 Markdown 表格，返回 (邀请码, 对应关系)。

    与 backend/app/auth/export.py 的 load_invite_codes 同逻辑（独立副本，
    避免 ops 脚本依赖 backend 运行时）。
    """
    rows: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        code, label = cells[0], cells[1]
        if code in {"邀请码"} or set(code) <= {"-", ":"}:
            continue
        if not code or not label:
            continue
        rows.append((code, label))
    if not rows:
        raise SystemExit(f"no invite-code rows parsed from {path}")
    return rows


def slugify(label: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", label, flags=re.UNICODE).strip("-")
    return slug or "account"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate invite-code QR codes")
    parser.add_argument("--invite-codes", default="invite-codes.md")
    parser.add_argument("--base", default="https://sbai.xin")
    parser.add_argument("--out", default="deploy/invite-qr")
    parser.add_argument("--scale", type=int, default=8, help="PNG 每模块像素（越大越清晰）")
    args = parser.parse_args(argv)

    codes = load_invite_codes(Path(args.invite_codes))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest = [
        "# 邀请码二维码清单",
        "",
        "| # | 对应关系 | 邀请码 | 文件 | URL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, (code, label) in enumerate(codes, start=1):
        url = f"{args.base.rstrip(chr(47))}/login#invite={code}"
        filename = f"{index:02d}-{slugify(label)}.png"
        segno.make(url).save(out / filename, scale=args.scale, border=2)
        manifest.append(f"| {index} | {label} | {code} | {filename} | {url} |")

    (out / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"generated {len(codes)} QR codes -> {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
