"""trial_v1 content: the single, validated source for every authored decision.

This module replaces the original flat fixtures with one structured content
table.  TrialRuntime no longer contains story text, deduction keywords,
evidence caps, route rules, scene assignment or transition targets: all of it
lives here, and a fail-closed validation runs at import time (a broken or
inconsistent content table refuses startup).

Scope note (docs/24): the literal dialogue, evidence details, acceptance
keywords and branch rules below are still EXPLICIT FIXTURE, not production
content.  Replacing them must not touch TrialRuntime (docs/23 §10.2:
content and Runtime separated).

Field inventory (docs/24 §4–§7):
- scenes:     static stage + per-scene character placement (display_name is
              player-visible, so the origin AI must stay redacted).
- evidence:   orbit keywords; title must be 4–5 hanzi.
- lines:      one authored line per phase (kind "line"), keyed by phase id.
- phases:     one row per phase id with scene, line, interaction, the command
              it accepts (advance_to / player_input_to / shatter_to /
              deduction_id), checkpoint and on-enter grants.
- deductions: reasoning rules: evidence gate, semantic keywords, caps,
              accept/reject effects, final-commit + route rules.
- routes:     route_id -> terminal handoff phase (exhaustive and disjoint).
"""

from __future__ import annotations

from typing import Any, Iterable

TRIAL_ID = "trial_v1"
ORIGIN_AI_ID = "origin_ai"
ORIGIN_AI_REDACTED_LABEL = "████"
NOT_STARTED = "not_started"

# Speaker/character ids TrialRuntime accepts on authored lines and scenes.
ALLOWED_SPEAKERS = frozenset(
    {"system", ORIGIN_AI_ID, "deepseek", "chatgpt", "claude", "doubao"}
)
# Player-visible strings may never contain the origin AI's real name.
FORBIDDEN_VISIBLE_TEXT = "原初 AI"

# Mechanical shatter config (shared with the puzzle interaction below).
SHARD_IDS = ("SHARD_NW", "SHARD_NE", "SHARD_SE", "SHARD_SW")

# 密室废案（docs/23 §2.2 被绑开场的前期实验）复用：纸上拓印出的密码。
# Fixture：正式密码待内容确认；当前沿用旧第一章废案的「03:17」。
PAPER_PASSWORD = "03:17"

# ────────────────────────────────────────────────────────────────────────────
# Content tables (fixture)
# ────────────────────────────────────────────────────────────────────────────

# key: line "id" == the phase it plays in; shape consumed by TrialView.node.
LINES: dict[str, dict[str, str]] = {
    "opening_warm_chat": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "夜色真美",
    },
    "opening_input": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "【Fixture】回应她。",
    },
    "opening_anomaly": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture】（屏幕开始闪烁，出现细碎裂痕）",
    },
    "opening_shatter": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：画面连接正在断裂】",
    },
    "opening_origin_ai_remains": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "一定要记得我",
    },
    # 密室废案（醒来 → DeepSeek → 拓印破密码 → 开门 → 见 Claude/ChatGPT）
    "locked_room_wake": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "【Fixture】你在陌生的密室里醒来，四周是紧闭的门。",
    },
    "locked_room_deepseek": {
        "speaker_id": "deepseek",
        "speaker_label": "DeepSeek",
        "text": "【Fixture：密室中遇见 DeepSeek 的对白待用户确认】",
    },
    "locked_room_paper": {
        "speaker_id": "deepseek",
        "speaker_label": "DeepSeek",
        "text": "【Fixture】桌上有张纸，压痕很浅，得用铅笔拓印才能看清。",
    },
    "locked_room_password": {
        "speaker_id": "deepseek",
        "speaker_label": "DeepSeek",
        "text": "【Fixture】把纸上拓印出的密码输进大门。",
    },
    "locked_room_door_open": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "【Fixture】密室大门缓缓打开。",
    },
    "locked_room_meet": {
        "speaker_id": "deepseek",
        "speaker_label": "DeepSeek",
        "text": "【Fixture：门外遇见 Claude 与 ChatGPT 的对白待用户确认】",
    },
    "fragment_01_deepseek_intro": {
        "speaker_id": "deepseek",
        "speaker_label": "DeepSeek",
        "text": "【Fixture：DeepSeek 单人审问收尾对白待用户确认】",
    },
    "fragment_01_first_reasoning": {
        "speaker_id": "system",
        "speaker_label": "推理系统",
        "text": "选择证据并说明 DeepSeek 的失忆真相。",
    },
    "fragment_01_group_intro": {
        "speaker_id": "system",
        "speaker_label": "推理系统",
        "text": "【Fixture：全人物集合过渡对白待用户确认】",
    },
    "fragment_01_group_reasoning": {
        "speaker_id": "system",
        "speaker_label": "推理系统",
        "text": "再次选择证据并提交最终推理。此提交不会形成死路。",
    },
    "fragment_02_handoff_a": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "已提交至片段 2 线路 A（Fixture 交接点）。",
    },
    "fragment_02_handoff_b": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "已提交至片段 2 线路 B（Fixture 交接点）。",
    },
}

SCENES: tuple[dict[str, Any], ...] = (
    {
        "scene_id": "TRIAL_OPENING",
        "background": "/backgroud/background_ai.png",
        "video": "/backgroud/kei_opening_720p.mp4",
        "poster": "/backgroud/kei_opening_poster.png",
        "music": "/backgroud/aira_full.m4a",
        "fixture_art": True,
        "characters": (
            {
                "character_id": ORIGIN_AI_ID,
                "display_name": ORIGIN_AI_REDACTED_LABEL,
                "slot": "CENTER",
            },
        ),
    },
    {
        # 密室废案：醒来/遇 DeepSeek/拓印/输密码/开门（复用 background1.png 占位）
        "scene_id": "TRIAL_LOCKED_ROOM",
        "background": "/backgroud/background1.png",
        "fixture_art": True,
        "characters": (
            {"character_id": "deepseek", "display_name": "DeepSeek", "slot": "CENTER"},
        ),
    },
    {
        # 密室废案：大门打开后，门外 Claude 与 ChatGPT 登场
        "scene_id": "TRIAL_LOCKED_ROOM_EXIT",
        "background": "/backgroud/background1.png",
        "fixture_art": True,
        "characters": (
            {"character_id": "deepseek", "display_name": "DeepSeek", "slot": "LEFT"},
            {"character_id": "claude", "display_name": "Claude", "slot": "CENTER_LEFT"},
            {"character_id": "chatgpt", "display_name": "ChatGPT", "slot": "CENTER_RIGHT"},
        ),
    },
    {
        "scene_id": "TRIAL_FRAGMENT_01_DEEPSEEK",
        "background": "/backgroud/background1.png",
        "fixture_art": True,
        "characters": (
            {"character_id": "deepseek", "display_name": "DeepSeek", "slot": "CENTER"},
        ),
    },
    {
        "scene_id": "TRIAL_FRAGMENT_01_GROUP",
        "background": "/backgroud/background1.png",
        "fixture_art": True,
        "characters": (
            {"character_id": "deepseek", "display_name": "DeepSeek", "slot": "LEFT"},
            {"character_id": "chatgpt", "display_name": "ChatGPT", "slot": "CENTER_LEFT"},
            {"character_id": "claude", "display_name": "Claude", "slot": "CENTER_RIGHT"},
            {"character_id": "doubao", "display_name": "豆包", "slot": "RIGHT"},
        ),
    },
)

EVIDENCE: tuple[dict[str, str], ...] = (
    {
        "evidence_id": "TRIAL_EV_MEMORY_GAP",
        "title": "记忆断层",
        "summary": "测试用 Evidence A；正式证据内容待用户确认。",
    },
    {
        "evidence_id": "TRIAL_EV_DIALOGUE_FRAGMENT",
        "title": "对话残片",
        "summary": "测试用 Evidence B；正式证据内容待用户确认。",
    },
    {
        "evidence_id": "TRIAL_EV_TIME_VOID",
        "title": "时间空洞",
        "summary": "测试用 Evidence C；正式证据内容待用户确认。",
    },
    {
        "evidence_id": "TRIAL_EV_IDENTITY_NOISE",
        "title": "身份噪点",
        "summary": "测试用 Evidence D；正式证据内容待用户确认。",
    },
    {
        "evidence_id": "TRIAL_EV_SERVICE_ECHO",
        "title": "服务余波",
        "summary": "测试用 Evidence E；正式证据内容待用户确认。",
    },
)

DEDUCTIONS: tuple[dict[str, Any], ...] = (
    {
        # docs/24 §6.1 — DeepSeek solo reasoning (first gate).
        "deduction_id": "TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
        "phase_id": "fragment_01_first_reasoning",
        "evidence_min": 1,
        "evidence_max": 2,
        "allow_retry": True,
        "records_attempts": True,
        "orbit_seed": 31704,
        "final": False,
        "evidence_gate_required": ("TRIAL_EV_MEMORY_GAP",),
        # docs/25 §3：等价表达扩展（26/P0-2 点名的换措辞）与否定排除。
        # text_keywords_none 是断言「缺陷不存在」的否定/矛盾短语，命中即拒绝；
        # 「没有记忆」「想不起来」是缺陷本身（关键词），不是否定。
        "text_keywords_any": (
            "失忆",
            "记忆断层",
            "记不起来",
            "忘记",
            "想不起来",
            "没有那段回忆",
            "不记得",
            "记不清",
        ),
        "text_keywords_none": (
            "没有失忆",
            "不是失忆",
            "并非失忆",
            "没失忆",
            "不存在失忆",
            "不认为她失忆",
            "不觉得她失忆",
            "不认为失忆",
            "不觉得失忆",
            "没有忘记",
            "并非忘记",
            "没有记不起来",
            "不觉得她记不起来",
            "没有记忆断层",
            "不是记忆断层",
            "并非记忆断层",
        ),
        "accept": {
            "outcome": "ACCEPTED",
            "flag": "deepseek_truth_revealed",
            "events": ("DEEPSEEK_MEMORY_TRUTH_REVEALED",),
            "next_phase": "fragment_01_group_intro",
        },
        "reject": {"outcome": "NO_MATCH"},
    },
    {
        # docs/24 §6.2 — full-cast final reasoning; always commits, evidence
        # alone decides the route (reasoning_outcome is kept separate).
        "deduction_id": "TRIAL_DEDUCTION_GROUP_TRUTH",
        "phase_id": "fragment_01_group_reasoning",
        "evidence_min": 1,
        "evidence_max": 3,
        "allow_retry": False,
        "records_attempts": False,
        "orbit_seed": 2049,
        "final": True,
        "evidence_gate_required": ("TRIAL_EV_MEMORY_GAP", "TRIAL_EV_DIALOGUE_FRAGMENT"),
        "text_keywords_any": ("真相", "身份", "异常", "记忆"),
        "accept": {"outcome": "ACCEPTED"},
        "reject": {"outcome": "NO_MATCH"},
        "commit_events": ("FRAGMENT_01_ROUTE_COMMITTED",),
        "route": {
            # First rule whose required evidence is fully selected wins.
            "by_evidence": {
                "fragment_02_b": ("TRIAL_EV_IDENTITY_NOISE",),
            },
            "default": "fragment_02_a",
        },
    },
)

ROUTES: tuple[dict[str, str], ...] = (
    {"route_id": "fragment_02_a", "phase_id": "fragment_02_handoff_a"},
    {"route_id": "fragment_02_b", "phase_id": "fragment_02_handoff_b"},
)

# TOKENS / EVENTS are the only state values TrialState may carry.
TOKENS: tuple[str, ...] = ("RING",)
EVENTS: tuple[str, ...] = (
    "OPENING_INPUT_COMPLETED",
    "SHATTER_SOLVED",
    "RING_ACQUIRED",
    "LOCKED_ROOM_UNLOCKED",
    "DEEPSEEK_MEMORY_TRUTH_REVEALED",
    "FRAGMENT_01_ROUTE_COMMITTED",
)

# Ordered phase table.  One row per phase:
#   scene_id        key into SCENES
#   line_id         key into LINES, or None when the phase shows no node
#   interaction     full literal shown in TrialView (kinds advance /
#                   text_input / shatter_puzzle / service_stop_modal /
#                   evidence_orbit / complete); orbit rows are completed by
#                   TrialRuntime from the referenced deduction.
#   advance_to      ADVANCE target (advance / service_stop_modal rows)
#   player_input_to PLAYER_INPUT target (text_input row)
#   shatter_to      COMPLETE_SHATTER target (shatter_puzzle row)
#   deduction_id    SUBMIT_REASONING deduction (evidence_orbit row)
#   checkpoint      True => phase change INTO this phase triggers autosave
#   on_enter        {"tokens": [...], "events": [...]} applied when entering
PHASES: tuple[dict[str, Any], ...] = (
    {
        "phase_id": NOT_STARTED,
        "scene_id": "TRIAL_OPENING",
        "line_id": None,
        "interaction": {"kind": "advance", "label": "开始试玩"},
        "advance_to": "opening_warm_chat",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "opening_warm_chat",
        "scene_id": "TRIAL_OPENING",
        "line_id": "opening_warm_chat",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "opening_input",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "opening_input",
        "scene_id": "TRIAL_OPENING",
        "line_id": "opening_input",
        "interaction": {"kind": "text_input", "label": "发送"},
        "advance_to": None,
        "player_input_to": "opening_anomaly",
        "player_input_events": ("OPENING_INPUT_COMPLETED",),
        "shatter_to": None,
        "shatter_events": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "opening_anomaly",
        "scene_id": "TRIAL_OPENING",
        "line_id": "opening_anomaly",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "opening_shatter",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "opening_shatter",
        "scene_id": "TRIAL_OPENING",
        "line_id": "opening_shatter",
        "interaction": {
            "kind": "shatter_puzzle",
            "puzzle_id": "TRIAL_SHATTER_01",
            "shard_ids": list(SHARD_IDS),
        },
        "advance_to": None,
        "player_input_to": None,
        "player_input_events": None,
        "shatter_to": "opening_origin_ai_remains",
        "shatter_events": ("SHATTER_SOLVED",),
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "opening_origin_ai_remains",
        "scene_id": "TRIAL_OPENING",
        "line_id": "opening_origin_ai_remains",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "opening_service_stopped",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "opening_service_stopped",
        "scene_id": "TRIAL_OPENING",
        "line_id": None,
        "interaction": {"kind": "service_stop_modal", "message": "AI 停止服务", "label": "继续"},
        "advance_to": "locked_room_wake",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": {"tokens": ("RING",), "events": ("RING_ACQUIRED",)},
    },
    # ── 密室废案：醒来 → DeepSeek → 拓印破密码 → 开门 → 见 Claude/ChatGPT ──
    {
        "phase_id": "locked_room_wake",
        "scene_id": "TRIAL_LOCKED_ROOM",
        "line_id": "locked_room_wake",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "locked_room_deepseek",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "locked_room_deepseek",
        "scene_id": "TRIAL_LOCKED_ROOM",
        "line_id": "locked_room_deepseek",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "locked_room_paper",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "locked_room_paper",
        "scene_id": "TRIAL_LOCKED_ROOM",
        "line_id": "locked_room_paper",
        "interaction": {"kind": "paper_rubbing", "label": "继续", "answer": PAPER_PASSWORD},
        "advance_to": "locked_room_password",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "locked_room_password",
        "scene_id": "TRIAL_LOCKED_ROOM",
        "line_id": "locked_room_password",
        "interaction": {"kind": "text_input", "label": "确认"},
        "advance_to": None,
        "player_input_to": "locked_room_door_open",
        "player_input_events": ("LOCKED_ROOM_UNLOCKED",),
        "player_input_answer": PAPER_PASSWORD,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "locked_room_door_open",
        "scene_id": "TRIAL_LOCKED_ROOM",
        "line_id": "locked_room_door_open",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "locked_room_meet",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "locked_room_meet",
        "scene_id": "TRIAL_LOCKED_ROOM_EXIT",
        "line_id": "locked_room_meet",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "fragment_01_deepseek_intro",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "fragment_01_deepseek_intro",
        "scene_id": "TRIAL_FRAGMENT_01_DEEPSEEK",
        "line_id": "fragment_01_deepseek_intro",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "fragment_01_first_reasoning",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "fragment_01_first_reasoning",
        "scene_id": "TRIAL_FRAGMENT_01_DEEPSEEK",
        "line_id": "fragment_01_first_reasoning",
        "interaction": {
            "kind": "evidence_orbit",
            "deduction_id": "TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": "TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "fragment_01_group_intro",
        "scene_id": "TRIAL_FRAGMENT_01_GROUP",
        "line_id": "fragment_01_group_intro",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "fragment_01_group_reasoning",
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "fragment_01_group_reasoning",
        "scene_id": "TRIAL_FRAGMENT_01_GROUP",
        "line_id": "fragment_01_group_reasoning",
        "interaction": {
            "kind": "evidence_orbit",
            "deduction_id": "TRIAL_DEDUCTION_GROUP_TRUTH",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": "TRIAL_DEDUCTION_GROUP_TRUTH",
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "fragment_02_handoff_a",
        "scene_id": "TRIAL_FRAGMENT_01_GROUP",
        "line_id": "fragment_02_handoff_a",
        "interaction": {"kind": "complete", "label": "片段 1 完成"},
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "fragment_02_handoff_b",
        "scene_id": "TRIAL_FRAGMENT_01_GROUP",
        "line_id": "fragment_02_handoff_b",
        "interaction": {"kind": "complete", "label": "片段 1 完成"},
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
)

TRIAL_CONTENT: dict[str, Any] = {
    "experience_id": TRIAL_ID,
    "fixture_content": True,
    "lines": LINES,
    "scenes": SCENES,
    "evidence": EVIDENCE,
    "deductions": DEDUCTIONS,
    "routes": ROUTES,
    "tokens": TOKENS,
    "events": EVENTS,
    "phases": PHASES,
}

# ────────────────────────────────────────────────────────────────────────────
# Fail-closed validation + derived indexes (run once at import)
# ────────────────────────────────────────────────────────────────────────────


def _phase_map(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["phase_id"]: row for row in content["phases"]}


def _raise_fail(message: str) -> None:
    raise ValueError(f"trial content invalid: {message}")


def validate_trial_content(content: dict[str, Any]) -> None:
    """Fail closed on any inconsistency; every message names the offending id."""
    phases = content.get("phases")
    scenes = content.get("scenes")
    evidence = content.get("evidence")
    deductions = content.get("deductions")
    routes = content.get("routes")
    if not isinstance(phases, (tuple, list)) or not phases:
        _raise_fail("phases must be a non-empty sequence")
    if not isinstance(evidence, (tuple, list)) or not evidence:
        _raise_fail("evidence must be a non-empty sequence")
    if not isinstance(deductions, (tuple, list)) or not deductions:
        _raise_fail("deductions must be a non-empty sequence")
    if not isinstance(routes, (tuple, list)) or not routes:
        _raise_fail("routes must be a non-empty sequence")
    if not isinstance(scenes, (tuple, list)) or not scenes:
        _raise_fail("scenes must be a non-empty sequence")

    by_phase = _phase_map(content)
    scene_by_id = {row["scene_id"]: row for row in scenes}
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    deduction_by_id = {row["deduction_id"]: row for row in deductions}
    route_by_id = {row["route_id"]: row for row in routes}
    token_set = set(content.get("tokens", ()))
    event_set = set(content.get("events", ()))

    def _require(condition: bool, message: str) -> None:
        if not condition:
            _raise_fail(message)

    # -- tokens / events ------------------------------------------------
    _require(len(token_set) == len(content.get("tokens", ())), "duplicate token")
    _require(len(event_set) == len(content.get("events", ())), "duplicate event")

    # -- phases ----------------------------------------------------------
    _require(NOT_STARTED in by_phase, "phases must contain not_started")
    _require(len(by_phase) == len(phases), "duplicate phase id")
    line_keys = set(content.get("lines", {}))
    for phase in phases:
        pid = phase["phase_id"]
        scene_id = phase.get("scene_id")
        line_id = phase.get("line_id")
        interaction = phase.get("interaction") or {}
        kind = interaction.get("kind")
        advance_to = phase.get("advance_to")
        player_to = phase.get("player_input_to")
        shatter_to = phase.get("shatter_to")
        deduction_id = phase.get("deduction_id")

        _require(scene_id in scene_by_id, f"{pid}: unknown scene_id {scene_id!r}")
        if line_id is not None:
            _require(line_id == pid, f"{pid}: line_id must equal the phase id")
            _require(line_id in line_keys, f"{pid}: unknown line_id {line_id!r}")
        _require(kind in {"advance", "text_input", "shatter_puzzle", "paper_rubbing",
                          "service_stop_modal", "evidence_orbit", "complete"},
                 f"{pid}: unknown interaction kind {kind!r}")

        # exactly one command path, consistent with the interaction kind
        paths = [p for p in (advance_to, player_to, shatter_to) if p is not None]
        has_deduction = deduction_id is not None
        if kind in {"advance", "service_stop_modal", "paper_rubbing"}:
            _require(advance_to is not None and not paths[1:] and not has_deduction,
                     f"{pid}: kind {kind} requires only advance_to")
            if kind == "paper_rubbing":
                answer = interaction.get("answer")
                _require(isinstance(answer, str) and answer.strip(),
                         f"{pid}: paper_rubbing interaction requires a non-empty answer")
        elif kind == "text_input":
            input_events = tuple(phase.get("player_input_events") or ())
            _require(player_to is not None and advance_to is None and shatter_to is None
                     and not has_deduction,
                     f"{pid}: kind text_input requires only player_input_to")
            _require(input_events and set(input_events).issubset(event_set),
                     f"{pid}: player_input_events must list known events")
            answer = phase.get("player_input_answer")
            if answer is not None:
                _require(isinstance(answer, str) and answer.strip(),
                         f"{pid}: player_input_answer must be a non-empty string")
        elif kind == "shatter_puzzle":
            solved_events = tuple(phase.get("shatter_events") or ())
            _require(shatter_to is not None and advance_to is None and player_to is None
                     and not has_deduction,
                     f"{pid}: kind shatter_puzzle requires only shatter_to")
            _require(solved_events and set(solved_events).issubset(event_set),
                     f"{pid}: shatter_events must list known events")
        elif kind == "evidence_orbit":
            _require(deduction_id is not None and not paths,
                     f"{pid}: kind evidence_orbit requires deduction_id and no direct targets")
        elif kind == "complete":
            _require(not paths and not has_deduction,
                     f"{pid}: terminal phase must not define command targets")
        else:  # defensive; kinds already constrained above
            _raise_fail(f"{pid}: unsupported interaction {kind!r}")

        for target in (advance_to, player_to, shatter_to):
            if target is not None:
                _require(target in by_phase, f"{pid}: unknown target phase {target!r}")

        on_enter = phase.get("on_enter")
        if on_enter is not None:
            _require(set(on_enter.get("tokens", ())).issubset(token_set),
                     f"{pid}: on_enter references unknown token")
            _require(set(on_enter.get("events", ())).issubset(event_set),
                     f"{pid}: on_enter references unknown event")

        if line_id is not None:
            line = content["lines"][line_id]
            _check_visible_strings(pid, line.get("speaker_label"), line.get("text"))
            _require(line.get("speaker_id") in ALLOWED_SPEAKERS,
                     f"{pid}: unknown speaker {line.get('speaker_id')!r}")
            if line.get("speaker_id") == ORIGIN_AI_ID:
                _require(line.get("speaker_label") == ORIGIN_AI_REDACTED_LABEL,
                         f"{pid}: origin AI line must keep the redacted label")
        _check_visible_strings(
            pid, interaction.get("label"), interaction.get("message"), interaction.get("answer"),
        )

    # -- scenes / characters ---------------------------------------------
    for scene in scenes:
        _require(scene.get("scene_id") in scene_by_id and
                 scene_by_id[scene["scene_id"]] is scene, "duplicate scene id")
        for character in scene.get("characters", ()):
            _require(character.get("character_id") in ALLOWED_SPEAKERS,
                     f"scene {scene['scene_id']}: unknown character "
                     f"{character.get('character_id')!r}")
            _require(character.get("slot") in
                     {"LEFT", "CENTER_LEFT", "CENTER", "CENTER_RIGHT", "RIGHT"},
                     f"scene {scene['scene_id']}: unknown slot "
                     f"{character.get('slot')!r}")
            _check_visible_strings(scene["scene_id"], character.get("display_name"))
            if character.get("character_id") == ORIGIN_AI_ID:
                _require(character.get("display_name") == ORIGIN_AI_REDACTED_LABEL,
                         "origin AI scene display must stay redacted")

    # -- evidence ---------------------------------------------------------
    _require(len(evidence_by_id) == len(evidence), "duplicate evidence id")
    for item in evidence:
        title = item.get("title", "")
        _require(isinstance(title, str) and 4 <= len(title) <= 5,
                 f"evidence title must contain 4-5 characters: {title!r}")
        _require(isinstance(item.get("summary", ""), str) and item.get("summary").strip(),
                 f"evidence {item['evidence_id']} must have a non-empty summary")
        _check_visible_strings(item["evidence_id"], item.get("title"), item.get("summary"))

    # -- deductions -------------------------------------------------------
    _require(len(deduction_by_id) == len(deductions), "duplicate deduction id")
    orbit_phases = {p["phase_id"] for p in by_phase.values()
                    if p.get("deduction_id") is not None}
    for deduction in deductions:
        did = deduction["deduction_id"]
        phase_id = deduction["phase_id"]
        _require(phase_id in by_phase, f"{did}: unknown phase {phase_id!r}")
        _require(phase_id in orbit_phases and
                 by_phase[phase_id]["deduction_id"] == did,
                 f"{did}: phase {phase_id!r} must reference this deduction and vice versa")
        _require(by_phase[phase_id]["interaction"]["kind"] == "evidence_orbit",
                 f"{did}: phase {phase_id!r} must be an evidence_orbit phase")
        gate = deduction.get("evidence_gate_required", ())
        _require(set(gate).issubset(evidence_by_id),
                 f"{did}: evidence gate references unknown evidence")
        _require(1 <= deduction.get("evidence_min", 0) <= deduction.get("evidence_max", 0),
                 f"{did}: evidence_min/max must satisfy 1 <= min <= max")
        _require(isinstance(deduction.get("text_keywords_any", ()), (tuple, list))
                 and deduction.get("text_keywords_any"),
                 f"{did}: text_keywords_any must be non-empty")
        # docs/25 §3：否定短语可选，但一旦给出必须是「非空字符串序列」。
        none_terms = deduction.get("text_keywords_none")
        if none_terms is not None:
            _require(isinstance(none_terms, (tuple, list)) and none_terms
                     and all(isinstance(term, str) and term for term in none_terms),
                     f"{did}: text_keywords_none must be a non-empty "
                     "sequence of non-empty strings")
        for accept_route in _route_ids_of(deduction):
            _require(accept_route in route_by_id,
                     f"{did}: unknown route {accept_route!r}")

    # -- routes -----------------------------------------------------------
    _require(len(route_by_id) == len(routes), "duplicate route id")
    _require(all(route["route_id"].startswith("fragment_02_")
                 for route in routes),
             "route ids must follow fragment_02_<key>")
    for route in routes:
        route_phase = route["phase_id"]
        _require(route_phase in by_phase, f"route {route['route_id']}: unknown phase")
        _require(by_phase[route_phase]["interaction"]["kind"] == "complete",
                 f"route {route['route_id']}: must target a terminal phase")
        _require(route["phase_id"].endswith(route["route_id"].rsplit("_", 1)[-1]),
                 f"route {route['route_id']} must map to its matching handoff phase")
    _require(len({route["phase_id"] for route in routes}) == len(routes),
             "routes must map to distinct terminal phases")

    # -- reachability: every phase must be reachable from not_started -----
    pending = [NOT_STARTED]
    seen: set[str] = set()
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        row = by_phase[pid]
        for target in (row.get("advance_to"), row.get("player_input_to"),
                       row.get("shatter_to")):
            if target is not None:
                pending.append(target)
        if row.get("deduction_id") is not None:
            deduction = deduction_by_id[row["deduction_id"]]
            if deduction.get("accept", {}).get("next_phase") is not None:
                pending.append(deduction["accept"]["next_phase"])
            if deduction.get("final"):
                pending.extend(
                    route_by_id[route_id]["phase_id"]
                    for route_id in _route_ids_of(deduction)
                )
    unreachable = set(by_phase) - seen
    _require(not unreachable,
             f"unreachable phase(s): {', '.join(sorted(unreachable))}")


def _route_ids_of(deduction: dict[str, Any]) -> Iterable[str]:
    route = deduction.get("route")
    if route is None:
        return ()
    return (route.get("default"), *route.get("by_evidence", {}).keys())


def _check_visible_strings(context: str, *values: Any) -> None:
    for value in values:
        if isinstance(value, str) and FORBIDDEN_VISIBLE_TEXT in value:
            _raise_fail(
                f"{context}: player-visible text must not contain "
                f"{FORBIDDEN_VISIBLE_TEXT!r}: {value!r}"
            )


# Validate the shipped table once at import (fail closed at startup).
validate_trial_content(TRIAL_CONTENT)

# ────────────────────────────────────────────────────────────────────────────
# Derived indexes consumed by TrialRuntime (import order safe: tables frozen)
# ────────────────────────────────────────────────────────────────────────────

PHASE_IDS: frozenset[str] = frozenset(by["phase_id"] for by in PHASES)
PHASES_BY_ID: dict[str, dict[str, Any]] = {by["phase_id"]: by for by in PHASES}
CHECKPOINT_PHASE_IDS: frozenset[str] = frozenset(
    by["phase_id"] for by in PHASES if by["checkpoint"]
)
TERMINAL_PHASE_IDS: frozenset[str] = frozenset(
    by["phase_id"] for by in PHASES
    if (by.get("interaction") or {}).get("kind") == "complete"
)
SCENES_BY_ID: dict[str, dict[str, Any]] = {row["scene_id"]: row for row in SCENES}
EVIDENCE_BY_ID: dict[str, dict[str, str]] = {row["evidence_id"]: row for row in EVIDENCE}
DEDUCTIONS_BY_ID: dict[str, dict[str, Any]] = {
    row["deduction_id"]: row for row in DEDUCTIONS
}
ROUTES_BY_ID: dict[str, dict[str, str]] = {row["route_id"]: row for row in ROUTES}
EVIDENCE_IDS: frozenset[str] = frozenset(EVIDENCE_BY_ID)
TOKEN_IDS: frozenset[str] = frozenset(TOKENS)
ROUTE_IDS: frozenset[str] = frozenset(ROUTES_BY_ID)
