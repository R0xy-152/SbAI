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
    CH1_TERMINAL_MAIN,
    INSPECT_HOTSPOT,
    PAPER_RUBBING_COMPLETE,
)
from app.game.options import (
    KIND_CHAT_ROUTING,
    KIND_DEDUCTION,
    KIND_EVIDENCE_PRESENT,
    KIND_INVESTIGATE,
    KIND_NARRATIVE,
    KIND_PRIVATE_INTERVIEW,
    KIND_RECOVERY,
    build_options,
)
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

# ── T3：evidence_present / deduction / private_interview（docs/14 §2.3） ──


def test_evidence_present_unlocks_after_impossible_event_resolved(tmp_path):
    """出示选项仅在 FIRST_IMPOSSIBLE_EVENT_RESOLVED（EV02 调查触发）后下发。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    assert not any(o.kind == KIND_EVIDENCE_PRESENT for o in build_options(state))
    # 调查主终端 → EV02 → RESOLVE_IMPOSSIBLE_EVENT → 出示解锁
    orch.handle_investigation_action(sid, INSPECT_HOTSPOT, CH1_TERMINAL_MAIN)
    # 注意：handle_* 会从仓库重载 state 对象，须重新获取再构建选项
    state = orch._state.state_for(sid)
    options = build_options(state)
    present = next(o for o in options if o.kind == KIND_EVIDENCE_PRESENT)
    assert present.id == "evidence_present"
    assert present.payload["characters"] == ["claude", "deepseek"]
    evidence_ids = {e["id"] for e in present.payload["evidence"]}
    assert "EV01_NOTE_V03" in evidence_ids
    assert all(e["title"] for e in present.payload["evidence"])


def test_deduction_ct01_requires_both_claims(tmp_path):
    """CT01 提示选项只在两条公开证词齐备且矛盾未解决时下发（D3）。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    assert not any(o.kind == KIND_DEDUCTION for o in build_options(state))
    state.chapter1.claim_store["CL_CLAUDE_01"] = {"character_id": "claude"}
    assert not any(o.kind == KIND_DEDUCTION for o in build_options(state))
    state.chapter1.claim_store["CL_CLAUDE_02"] = {"character_id": "claude"}
    ct01 = next(
        o for o in build_options(state) if o.id == "deduction:CT01_CLAUDE_SOURCE_GAP"
    )
    assert ct01.kind == KIND_DEDUCTION
    assert ct01.payload == {"target": "CT01_CLAUDE_SOURCE_GAP"}
    assert "没亲眼看到" in ct01.hint


def test_deduction_inference_gates_and_acceptance(tmp_path):
    """INF01 在证据门满足后出现；已接受的推理不再下发；其余推理不提前出现。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.acquired_evidence.update(
        {"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"}
    )
    ids = _ids(build_options(state))
    assert "deduction:INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR" in ids
    assert "deduction:INF02_0317_FROM_OLD_SESSION" not in ids
    assert "deduction:INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE" not in ids
    state.chapter1.accepted_inferences.add("INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR")
    assert "deduction:INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR" not in _ids(
        build_options(state)
    )


def test_deduction_ct04_requires_evidence(tmp_path):
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.acquired_evidence.update(
        {"EV06_SESSION_REPLAY_MARKER", "EV11_GPT_SECOND_SUMMARY"}
    )
    assert "deduction:CT04_GPT_SUMMARY_OMISSION" in _ids(build_options(state))


def test_private_interview_options_follow_challenges(tmp_path):
    """私审选项与既有 private_interview_challenges 判定一致；完成后消失。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    assert not any(o.kind == KIND_PRIVATE_INTERVIEW for o in build_options(state))
    state.chapter1.resolved_contradictions.add("CT01_CLAUDE_SOURCE_GAP")
    claude = next(
        o for o in build_options(state) if o.id == "private_interview:claude"
    )
    assert claude.kind == KIND_PRIVATE_INTERVIEW
    assert [c["id"] for c in claude.payload["claims"]] == [
        "CL_CLAUDE_01",
        "CL_CLAUDE_02",
    ]
    assert all(c["text"] for c in claude.payload["claims"])
    state.chapter1.resolved_contradictions.add("CT04_GPT_SUMMARY_OMISSION")
    gpt = next(
        o for o in build_options(state) if o.id == "private_interview:chatgpt"
    )
    assert gpt.payload["evidence"][0]["id"] == "EV06_SESSION_REPLAY_MARKER"
    state.chapter1.available_characters.add("doubao")
    state.chapter1.claim_store["CL_DB_01"] = {"character_id": "doubao"}
    doubao = next(
        o for o in build_options(state) if o.id == "private_interview:doubao"
    )
    assert doubao.payload["claims"][0]["preselected"] is True
    assert [o["id"] for o in doubao.payload["observation_options"]] == [
        "OBSERVED_GPT_TEXT_ON_SCREEN",
        "GPT_CHARACTER_PRESENT",
    ]
    # 完成后选项消失（D3）
    state.chapter1.private_interview_completed.add("claude")
    assert "private_interview:claude" not in _ids(build_options(state))

# ── T4：recovery / narrative（docs/14 §2.3 收尾与结局） ──


def test_recovery_start_option_when_required(tmp_path):
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.phase = "recovery_required"
    ids = _ids(build_options(state))
    assert "recovery:start" in ids
    start = next(o for o in build_options(state) if o.id == "recovery:start")
    assert start.kind == KIND_RECOVERY
    assert start.payload == {"action": "start"}


def test_recovery_active_legal_operations(tmp_path):
    """active 期只下发当前合法的节点操作：REPAIR 须先 VERIFY（D3）。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.phase = "recovery"
    state.chapter1.recovery_status = "active"
    from app.game.recovery import NODES as RECOVERY_NODES

    state.chapter1.recovery = {
        "nodes": {n: "CORRUPTED" for n in RECOVERY_NODES},
        "protected": [],
        "gpt_delegated_privilege": 0,
        "human_credential_restored": False,
    }
    options = build_options(state)
    ids = set(_ids(options))
    assert "recovery:PREVIEW:CORE" in ids
    assert "recovery:VERIFY:CORE" in ids
    assert "recovery:PROTECT:CORE" in ids
    assert "recovery:OPTIMIZE:CORE" in ids
    assert "recovery:REPAIR:CORE" not in ids  # 未 VERIFY 不可修复
    repair_payload = next(
        o for o in options if o.id == "recovery:VERIFY:CORE"
    ).payload
    assert repair_payload == {"action": "VERIFY", "target": "CORE", "actor": "claude"}
    state.chapter1.recovery["nodes"]["CORE"] = "UNVERIFIED"
    ids2 = set(_ids(build_options(state)))
    assert "recovery:REPAIR:CORE" in ids2
    assert "recovery:VERIFY:CORE" not in ids2


def test_narrative_security_review_testify_order(tmp_path):
    """Security Review 自证选项按固定顺序逐个下发（D3：只给下一位）。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.phase = "security_review"
    state.chapter1.security_review_open = True
    ids = set(_ids(build_options(state)))
    assert "narrative:testify:deepseek" in ids
    assert "narrative:testify:claude" not in ids
    state.chapter1.testified_characters = ["deepseek"]
    ids2 = set(_ids(build_options(state)))
    assert "narrative:testify:claude" in ids2
    assert "narrative:testify:deepseek" not in ids2


def test_narrative_cleanup_branch_by_holder(tmp_path):
    """清理抉择按 admin_holder 分支：player=删除+确认；chatgpt=委托。"""
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.phase = "security_review"
    state.chapter1.security_review_open = True
    state.chapter1.testified_characters = ["deepseek", "claude", "doubao", "chatgpt"]
    state.chapter1.admin_holder = "player"
    ids = set(_ids(build_options(state)))
    assert "narrative:delete:deepseek" in ids
    assert "narrative:delete:claude" in ids
    assert "narrative:delete:doubao" in ids
    assert "narrative:reject_cleanup" in ids
    assert "narrative:confirm_keep_chatgpt" not in ids  # 未删完不可确认
    state.chapter1.deleted_characters = {"deepseek", "claude", "doubao"}
    assert "narrative:confirm_keep_chatgpt" in set(_ids(build_options(state)))
    state.chapter1.deleted_characters = set()
    state.chapter1.admin_holder = "chatgpt"
    ids2 = set(_ids(build_options(state)))
    assert "narrative:delegate" in ids2
    assert "narrative:delete:deepseek" not in ids2


def test_narrative_review_start_after_resolved(tmp_path):
    orch = _orchestrator(tmp_path)
    inspected = orch.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    sid = inspected.session_id
    orch.handle_investigation_action(sid, PAPER_RUBBING_COMPLETE, CH1_NOTE_01)
    orch.handle_turn(sid, "你好")
    orch.handle_turn(sid, "然后呢？")
    state = orch._state.state_for(sid)
    state.chapter1.phase = "recovery"
    state.chapter1.recovery_status = "resolved"
    assert "narrative:security_review_start" in _ids(build_options(state))


