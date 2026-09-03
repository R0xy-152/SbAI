"""docs/20 developer note: prologue 问句 + 收集 + 导出。

覆盖：静态性格问句、PrologueRuntime 的 pending 状态、Orchestrator 授权/清除、
auth repository 落库、invite-codes.md 解析与 xlsx 导出、以及端到端 API 链路。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import DeveloperNote, MemoryAuthRepository
from app.auth.export import load_invite_codes, write_xlsx
from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.persistence.repository import JsonSessionRepository
from app.script.developer_note import DEVELOPER_NOTE_QUESTIONS, developer_note_question
from app.script.prologue_content import PROLOGUE_CHARACTERS
from app.script.prologue_runtime import PrologueRuntime
from app.script.story_runtime import StoryRuntime


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="自由交流回复")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="……")


def _runtimes() -> dict:
    return {cid: _Runtime(cid) for cid in (*PROLOGUE_CHARACTERS, "doubao")}


def _wired(tmp_path) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        _runtimes(),
        repository=JsonSessionRepository(tmp_path / "sessions"),
        availability={"claude": "claude_has_appeared", "chatgpt": "chatgpt_has_appeared"},
        story_runtime=StoryRuntime(),
        prologue_runtime=PrologueRuntime(),
    )


def _finish_prologue(orchestrator: GameOrchestrator) -> tuple[str, str]:
    view = orchestrator.story_advance(None, story_id="prologue")
    session_id = view["session_id"]
    for _ in range(2000):
        node = view["node"]
        if node["kind"] == "choice":
            option = node["options"][0]["id"]
            view = orchestrator.story_choose(session_id, option, story_id="prologue")
        else:
            view = orchestrator.story_advance(session_id, story_id="prologue")
        if view["finished"]:
            break
    return session_id, view["node"]["character_id"]


# ---- 1. 静态性格问句 ----

def test_question_exists_for_each_prologue_character():
    for cid in PROLOGUE_CHARACTERS:
        assert developer_note_question(cid)
    assert developer_note_question("doubao") is None
    assert all("开发者" in q for q in DEVELOPER_NOTE_QUESTIONS.values())


# ---- 2. PrologueRuntime pending 状态 ----

def _chat_choice_snapshot() -> dict:
    return {
        "story_id": "prologue",
        "phase": "chat_choice",
        "line_index": 0,
        "visited_character_ids": list(PROLOGUE_CHARACTERS),
        "active_character_id": None,
        "chat_character_id": None,
    }


def test_pending_after_chat_choice_and_cleared_after_collect():
    runtime = PrologueRuntime()
    runtime.restore("s", _chat_choice_snapshot())
    runtime.choose("s", "claude")
    assert runtime.developer_note_pending("s") is True
    assert runtime.collect_developer_note("s") == "claude"
    assert runtime.developer_note_pending("s") is False
    assert runtime.collect_developer_note("s") is None  # 幂等


def test_snapshot_restores_pending_flag_and_legacy_defaults_false():
    runtime = PrologueRuntime()
    runtime.restore("s", _chat_choice_snapshot())
    runtime.choose("s", "deepseek")
    assert runtime.snapshot("s")["developer_note_pending"] is True

    target = PrologueRuntime()
    target.restore("t", runtime.snapshot("s"))
    assert target.developer_note_pending("t") is True

    # 旧快照缺字段 → 默认 False，不回退为重新询问
    legacy = PrologueRuntime()
    legacy.restore("legacy", {**_chat_choice_snapshot(), "phase": "finished", "chat_character_id": "chatgpt"})
    assert legacy.developer_note_pending("legacy") is False


# ---- 3. Orchestrator 授权 / 清除 ----

def test_orchestrator_exposes_question_and_submits(tmp_path):
    orchestrator = _wired(tmp_path)
    session_id, character_id = _finish_prologue(orchestrator)
    state = orchestrator.get_investigation_state(session_id)
    assert state["developer_note_pending"] is True
    assert state["developer_note_question"] == developer_note_question(character_id)

    assert orchestrator.developer_note_character(session_id) == character_id
    orchestrator.complete_developer_note(session_id)
    orchestrator.complete_developer_note(session_id)  # 幂等
    state = orchestrator.get_investigation_state(session_id)
    assert state["developer_note_pending"] is False
    with pytest.raises(ValueError, match="already collected"):
        orchestrator.developer_note_character(session_id)


def test_submit_rejects_non_prologue(tmp_path):
    orchestrator = _wired(tmp_path)
    session_id = orchestrator.handle_turn(None, "你好").session_id
    with pytest.raises(ValueError, match="free chat has not started"):
        orchestrator.developer_note_character(session_id)


# ---- 4. repository + export ----

def test_memory_repo_adds_and_lists_notes():
    repo = MemoryAuthRepository()
    note = DeveloperNote(
        user_id="u", display_name="网易-01", label="网易", character_id="deepseek",
        content="很好", session_id="s", created_at=datetime.now(timezone.utc),
    )
    assert repo.add_developer_note(note) is True
    assert repo.add_developer_note(note) is False  # 同 session 幂等
    assert [n.content for n in repo.list_developer_notes()] == ["很好"]


def test_export_roundtrip(tmp_path):
    src = tmp_path / "invite-codes.md"
    src.write_text(
        "| 邀请码 | 对应关系 |\n| --- | --- |\n| AAA | 网易 |\n| BBB | 腾讯 |\n",
        encoding="utf-8",
    )
    codes = load_invite_codes(src)
    assert codes == [("AAA", "网易"), ("BBB", "腾讯")]

    notes = [DeveloperNote(
        user_id="u", display_name="网易-01", label="网易", character_id="deepseek",
        content="很好玩", session_id="s", created_at=datetime.now(timezone.utc),
    )]
    out = tmp_path / "out.xlsx"
    write_xlsx(out, codes, notes)
    assert out.exists()

    from openpyxl import load_workbook

    wb = load_workbook(out)
    rows = list(wb["邀请码"].values)
    assert rows[0] == ("邀请码", "对应关系", "对开发者的话")
    assert rows[1] == ("AAA", "网易", "很好玩")
    assert rows[2][0] == "BBB" and rows[2][1] == "腾讯"
    assert rows[2][2] in (None, "")  # openpyxl 把空串读回为 None
    detail = list(wb["对开发者的话"].values)
    assert detail[0] == ("对应关系", "显示名", "角色", "内容", "时间", "session_id")
    assert detail[1][0] == "网易"


# ---- 5. 端到端 API（不扣额度） ----

def _secured_app(monkeypatch):
    monkeypatch.setenv("GAL_PROVIDER", "mock")
    monkeypatch.setenv("GAL_AUTH_REQUIRED", "true")
    monkeypatch.setenv("GAL_AUTH_BACKEND", "memory")
    monkeypatch.setenv("GAL_AUTH_SECRET", "test-secret")
    return create_app()


def test_api_submit_note_does_not_consume_quota(monkeypatch, tmp_path):
    app = _secured_app(monkeypatch)
    app.state.orchestrator = _wired(tmp_path)
    _, invite = app.state.auth_service.create_user("网易-01", 100, "网易")
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"invite_code": invite})
        session_id, character_id = _finish_prologue(app.state.orchestrator)
        # 绑定归属（模拟登录后玩家创建会话）
        app.state.auth_service.repository.bind_game_session(
            app.state.auth_service.repository.list_users()[0].id, session_id
        )

        before = client.get("/api/auth/me").json()["quota_remaining"]
        resp = client.post(
            "/api/developer-note", json={"session_id": session_id, "message": "开发者加油"}
        )
        assert resp.status_code == 200
        assert resp.json()["stored"] is True
        assert resp.json()["character_id"] == character_id

        after = client.get("/api/auth/me").json()["quota_remaining"]
        assert after == before  # 留言不扣额度

        notes = app.state.auth_service.list_developer_notes()
        assert [n.content for n in notes] == ["开发者加油"]
        assert notes[0].label == "网易"

        # 重复提交 fail closed
        again = client.post(
            "/api/developer-note", json={"session_id": session_id, "message": "再来"}
        )
        assert again.status_code == 400
