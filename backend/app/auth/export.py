"""「对开发者的话」导出：把 invite-codes.md 与留言合并成 Excel（docs/20）。

明文邀请码只存在于仓库内的 invite-codes.md（开发者的运维台账），数据库
仍只保存 HMAC（docs/18）。导出时用留言的 label（对应关系）与台账里的
「对应关系」列对齐；无 label 的旧账号回落到 display_name。
"""

from __future__ import annotations

from pathlib import Path

from app.auth.repository import DeveloperNote


def load_invite_codes(path: Path) -> list[tuple[str, str]]:
    """解析 invite-codes.md 的 Markdown 表格，返回 (邀请码, 对应关系) 列表。

    跳过表头、分隔行与空单元格；找不到可解析行时抛出，fail closed。
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
        raise ValueError(f"no invite-code rows parsed from {path}")
    return rows


def _notes_by_label(notes: list[DeveloperNote]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for note in notes:
        key = note.label or note.display_name
        grouped.setdefault(key, []).append(note.content)
    return grouped


def write_xlsx(
    out: Path,
    invite_codes: list[tuple[str, str]],
    notes: list[DeveloperNote],
) -> None:
    """生成两张 sheet 的 xlsx：邀请码（含「对开发者的话」列）+ 留言明细。"""
    from openpyxl import Workbook

    grouped = _notes_by_label(notes)
    wb = Workbook()

    ws = wb.active
    ws.title = "邀请码"
    ws.append(["邀请码", "对应关系", "对开发者的话"])
    for code, label in invite_codes:
        ws.append([code, label, "\n".join(grouped.get(label, []))])

    ws2 = wb.create_sheet("对开发者的话")
    ws2.append(["对应关系", "显示名", "角色", "内容", "时间", "session_id"])
    for note in notes:
        ws2.append([
            note.label or note.display_name,
            note.display_name,
            note.character_id,
            note.content,
            note.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            note.session_id,
        ])

    wb.save(out)
