"""docs/14 T1: available-options generator（investigate / chat_routing）。

D3：只下发当前合法选项——未解锁的热点与角色永远不出现（防剧透）；
D5/D7：对话路由选项在角色登场后出现，payload 由前端回传既有端点。
"""

from __future__ import annotations

from app.characters.base import CharacterMood, CharacterResponse
from app.game.investigation import (
    CH1_C02_DOOR,
    CH1_CHARACTER_REGISTRY,
    CH1_NOTE_01,
    INSPECT_HOTSPOT,
    PAPER_RUBBING_COMPLETE,
)
from app.game.options import KIND_CHAT_ROUTING, KIND_INVESTIGATE, build_options
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(
            character_id=self.character_id,
            dialogue=f"{self.character_id} 回应。",
            next_mood=CharacterMood(positive=0.5, excitement=0.2),
        )

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


def _orchestrator(tmp_path) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {c: _Runtime(c) for c in ("deepseek", "claude", "chatgpt", "doubao")},
        repository=JsonSessionRepository(tmp_path / "sess"),
    )


def _ids(options):
    return [o.id for o in options]


def test_opening_offers_only_paper_investigate(tmp_path):
    """开场（未调查、无登场角色）：只有桌上的纸；无对话路由（D3 防剧透）。"""
    orch = _orchestrator(tmp_path)
    sid = orch.handle_turn(None, "你好").session_id
    options = build_options(orch._state.state_for(sid))
    assert _ids(options) == ["investigate:CH1_NOTE_01"]
    paper = options[0]
    assert paper.kind == KIND_INVESTIGATE
    assert paper.payload["steps"] == [
        {"action": INSPECT_HOTSPOT, "hotspot_id": CH1_NOTE_01},
        {"action": PAPER_RUBBING_COMPLETE, "hotspot_id": CH1_NOTE_01},
    ]
    assert paper.hint  # 拓印预览（D6 小面板文案）


def test_completed_paper_no_longer_offered(tmp_path):
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    orch.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    options = build_options(orch._state.state_for(inspected.session_id))
    assert _ids(options) == []  # 纸已完成、Claude 未登场：无选项


def test_claude_unlocks_hotspots_and_routing(tmp_path):
    """03:17 后：其余 3 个热点 + 「找 Claude 谈谈」；GPT/豆包仍不可见（D3）。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")  # 确定性 Gate counter=2 → Claude 登场
    options = build_options(orch._state.state_for(sid))
    assert set(_ids(options)) == {
        "investigate:CH1_TERMINAL_MAIN",
        "investigate:CH1_C02_DOOR",
        "investigate:CH1_CHARACTER_REGISTRY",
        "chat_routing:claude",
    }
    routing = next(o for o in options if o.kind == KIND_CHAT_ROUTING)
    assert routing.label == "找 Claude 谈谈"
    assert routing.payload == {"character_id": "claude"}
    # 未登场角色绝不下发
    assert "chat_routing:chatgpt" not in _ids(options)
    assert "chat_routing:doubao" not in _ids(options)


def test_other_hotspot_single_step_and_disappears_when_done(tmp_path):
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    # 调查注册表（INSPECT 一步完成）
    done = orch.handle_investigation_action(sid, INSPECT_HOTSPOT, CH1_CHARACTER_REGISTRY)
    assert done.outcome == "COMPLETED"
    options = build_options(orch._state.state_for(sid))
    assert "investigate:CH1_CHARACTER_REGISTRY" not in _ids(options)
    door = next(o for o in options if o.id == f"investigate:{CH1_C02_DOOR}")
    assert door.payload["steps"] == [
        {"action": INSPECT_HOTSPOT, "hotspot_id": CH1_C02_DOOR}
    ]


def test_routing_follows_available_characters(tmp_path):
    """路由选项严格跟随 available_characters；默认回应者 deepseek 不出选项。"""
    orch = _orchestrator(tmp_path)
    sid = orch.handle_turn(None, "你好").session_id
    state = orch._state.state_for(sid)
    state.chapter1.available_characters.update({"claude", "chatgpt", "doubao"})
    options = build_options(state)
    routing_ids = {
        o.payload["character_id"] for o in options if o.kind == KIND_CHAT_ROUTING
    }
    assert routing_ids == {"claude", "chatgpt", "doubao"}


def test_state_view_and_load_carry_options(tmp_path):
    """GET /api/game/state 视图与 Load 的 gameview_state 都携带 options。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    view = orch.get_investigation_state(sid)
    assert "options" in view
    assert [o["id"] for o in view["options"]] == _ids(
        build_options(orch._state.state_for(sid))
    )
    gv = orch.gameview_state(sid)
    assert "options" in gv["state"]
