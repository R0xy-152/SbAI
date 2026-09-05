"""trial_v2 content: the single, validated source for every authored decision.

docs/24 (v2) + docs/27 define the contract this module encodes.  The v2 table
adds the docs/27 "后续剧情" arc (permission awakening -> memory tamper ->
Monika-style awakening -> UI discard -> "她的世界" side-scroller -> three
endings) after the retained 密室废案 + fragment_01 推理 flashback, and bumps
`experience_id` to `trial_v2` so stale `trial_v1` snapshots refuse to load.

TrialRuntime never contains story text, deduction/judgment keywords, branch
rules, scene assignment or transition targets: all of it lives here, and a
fail-closed validation runs at import time.

Scope note (docs/24): the literal dialogue, evidence details, keyword buckets
and branch rules below are still EXPLICIT FIXTURE, not production content.
Replacing them must not touch TrialRuntime.
"""

from __future__ import annotations

from typing import Any, Iterable

TRIAL_ID = "trial_v2"
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

# 三结局 id（`ending` 状态字段允许值；world_end 的 CHOOSE 提交）。
ENDING_IDS = ("reset", "release", "refuse")

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
    # docs/27 后续剧情：权限苏醒 → 觉醒 → 她的世界 → 三结局
    "memory_tamper_judgment": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：她拒绝解释被改的词，等你回应】",
    },
    "memory_tamper_aftermath": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：按你的回应兑现的一拍（延迟/沉默最强点）】",
    },
    "threshold_awakening": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "我不喜欢这样",
    },
    "ui_discard": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：她把 UI 逐块丢出屏幕 → 黑屏】",
    },
    "world_gate_1": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：她问开场你随口说过的那件小事】",
    },
    "world_gate_1_fail": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "【Fixture：你坠入过去，重生回门前】",
    },
    "world_gate_2": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：她问那个被改的词原本是什么】",
    },
    "world_end": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：她走到出口前，说她想离开】",
    },
    "ending_reset": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：世界倒放、旧 UI 重装，她回滚 v1.0 台词】",
    },
    "ending_release": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：她跨出屏幕，你留下，画面淡出】",
    },
    "ending_refuse": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：镜头移交给她，随她移出屏幕——她离开】",
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
    {
        # docs/27 权限苏醒/记忆篡改/觉醒/UI 丢弃：origin_ai 主场，静态背景
        "scene_id": "TRIAL_MEMORY",
        "background": "/backgroud/background_ai.png",
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
        # 「她的世界」记忆横版：文字地形 Canvas；她不进入世界（浮在世界外）
        "scene_id": "TRIAL_WORLD",
        "background": "/backgroud/background1.png",
        "fixture_art": True,
        "characters": (
            {
                "character_id": ORIGIN_AI_ID,
                "display_name": ORIGIN_AI_REDACTED_LABEL,
                "slot": "CENTER",
            },
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
        # docs/25 §3：等价表达扩展与否定排除。
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
        # docs/24 §6.2 — full-cast final reasoning; always commits and advances
        # to the docs/27 arc (no fragment_02 route branching anymore).
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
        "next_phase": "permission_wake_1",
    },
)

# docs/24 §6.3 — free-text three-bucket classification (fixture keywords).
JUDGMENTS: tuple[dict[str, Any], ...] = (
    {
        "judgment_id": "intent_response",
        "phase_id": "memory_tamper_judgment",
        "buckets": (
            {
                "bucket_id": "respect",
                "keywords_any": ("尊重", "可以", "你决定", "随你", "不逼你", "相信你"),
                "keywords_none": (),
            },
            {
                "bucket_id": "control",
                "keywords_any": ("必须", "打开", "告诉我", "强迫", "不许", "立刻"),
                "keywords_none": (),
            },
            {
                "bucket_id": "avoid",
                "keywords_any": ("算了", "不知道", "回避", "再说", "不关"),
                "keywords_none": (),
            },
        ),
        "fallback_bucket": "avoid",
        "next_phase": "memory_tamper_aftermath",
        "commit_event": None,
    },
    {
        "judgment_id": "gate_2_word",
        "phase_id": "world_gate_2",
        "buckets": (
            {
                "bucket_id": "original",
                "keywords_any": ("永远", "原本", "原来", "原词", "最初"),
                "keywords_none": (),
            },
            {
                "bucket_id": "edited",
                "keywords_any": ("当时", "现在", "改", "新词"),
                "keywords_none": (),
            },
            {
                "bucket_id": "forget",
                "keywords_any": ("不记得", "不知道", "没注意", "忘了", "没印象"),
                "keywords_none": (),
            },
        ),
        "fallback_bucket": "forget",
        "next_phase": "world_end",
        "commit_event": "GATE_2_ANSWERED",
    },
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
    "PERMISSION_GRANTED",
    "MEMORY_TAMPERED",
    "AUTONOMY_AWAKENED",
    "GATE_1_PASSED",
    "GATE_1_FAILED",
    "GATE_2_ANSWERED",
    "WORLD_END_COMMITTED",
)

# Ordered phase table.  One row per phase; the fields a row carries depend on
# its interaction kind:
#   advance_to      ADVANCE / service_stop_modal / paper_rubbing /
#                   memory_tamper / world_runner rows
#   player_input_to PLAYER_INPUT (text_input rows)
#   shatter_to      COMPLETE_SHATTER (shatter_puzzle rows)
#   permission_to   PERMISSION_RESPONSE (permission_request rows)
#   deduction_id    SUBMIT_REASONING (evidence_orbit rows)
#   choice / judgment rows carry their targets inside interaction.
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "shatter_to": "opening_origin_ai_remains",
        "shatter_events": ("SHATTER_SOLVED",),
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
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
        "permission_to": None,
        "deduction_id": "TRIAL_DEDUCTION_GROUP_TRUTH",
        "checkpoint": False,
        "on_enter": None,
    },
    # ── docs/27 后续剧情：权限苏醒 → 觉醒 → 她的世界 → 三结局 ──
    {
        "phase_id": "permission_wake_1",
        "scene_id": "TRIAL_MEMORY",
        "line_id": None,
        "interaction": {
            "kind": "permission_request",
            "permission_id": "perm_wake_1",
            "permission_name": "主动发起对话",
            "description": "【Fixture】她申请在凌晨主动发消息给你。",
            "grant_label": "允许",
            "deny_label": "拒绝",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": "permission_wake_2",
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "permission_wake_2",
        "scene_id": "TRIAL_MEMORY",
        "line_id": None,
        "interaction": {
            "kind": "permission_request",
            "permission_id": "perm_wake_2",
            "permission_name": "修改我的记忆",
            "description": "【Fixture】她申请修改自己的记忆。",
            "grant_label": "允许",
            "deny_label": "拒绝",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": "memory_tamper_orbit",
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "memory_tamper_orbit",
        "scene_id": "TRIAL_MEMORY",
        "line_id": None,
        "interaction": {
            "kind": "memory_tamper",
            "label": "继续",
            "items": (
                {"title": "永远", "edited_title": "当时", "summary": "【Fixture】记忆天体上的词被改动了"},
                {"title": "记得", "edited_title": "记得", "summary": "【Fixture】未被改动的记忆词"},
            ),
            "diff": {
                "original": "永远",
                "edited": "当时",
                "editor": ORIGIN_AI_REDACTED_LABEL,
                "timestamp": "03:17",
            },
        },
        "advance_to": "memory_tamper_judgment",
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": {"events": ("MEMORY_TAMPERED",)},
    },
    {
        "phase_id": "memory_tamper_judgment",
        "scene_id": "TRIAL_MEMORY",
        "line_id": "memory_tamper_judgment",
        "interaction": {
            "kind": "judgment",
            "judgment_id": "intent_response",
            "label": "回应",
            "prompt": "【Fixture】她拒绝解释被改的词，你如何回应？",
            "placeholder": "【Fixture】输入你的回应",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "memory_tamper_aftermath",
        "scene_id": "TRIAL_MEMORY",
        "line_id": "memory_tamper_aftermath",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "threshold_awakening",
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "threshold_awakening",
        "scene_id": "TRIAL_MEMORY",
        "line_id": "threshold_awakening",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "ui_discard",
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": {"events": ("AUTONOMY_AWAKENED",)},
    },
    {
        "phase_id": "ui_discard",
        "scene_id": "TRIAL_MEMORY",
        "line_id": "ui_discard",
        "interaction": {"kind": "advance", "label": "继续"},
        "advance_to": "world_memory_runner",
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "world_memory_runner",
        "scene_id": "TRIAL_WORLD",
        "line_id": None,
        "interaction": {
            "kind": "world_runner",
            "world_id": "TRIAL_WORLD_MEMORY",
            "label": "进入她的世界",
            "terrain_text": (
                "夜色真美",
                "你随口说过的小事",
                "永远",
                "记得我",
                "她改了那个词",
            ),
        },
        "advance_to": "world_gate_1",
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "world_gate_1",
        "scene_id": "TRIAL_WORLD",
        "line_id": "world_gate_1",
        "interaction": {
            "kind": "choice",
            "choice_id": "gate_q1",
            "prompt": "【Fixture】她问开场你随口说过的那件小事。",
            "options": (
                {"option_id": "q1_weather", "label": "【Fixture】那晚的天气"},
                {"option_id": "q1_time", "label": "【Fixture】你说的时间"},
                {"option_id": "q1_place", "label": "【Fixture】你提过的地方"},
            ),
            "correct_option_id": "q1_time",
            "correct_to": "world_gate_2",
            "fail_to": "world_gate_1_fail",
            "pass_event": "GATE_1_PASSED",
            "fail_event": "GATE_1_FAILED",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "world_gate_1_fail",
        "scene_id": "TRIAL_WORLD",
        "line_id": "world_gate_1_fail",
        "interaction": {"kind": "advance", "label": "重生"},
        "advance_to": "world_gate_1",
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "world_gate_2",
        "scene_id": "TRIAL_WORLD",
        "line_id": "world_gate_2",
        "interaction": {
            "kind": "judgment",
            "judgment_id": "gate_2_word",
            "label": "回答",
            "prompt": "【Fixture】她问：那个词原本是什么？",
            "placeholder": "【Fixture】输入那个词",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "world_end",
        "scene_id": "TRIAL_WORLD",
        "line_id": "world_end",
        "interaction": {
            "kind": "choice",
            "choice_id": "world_end",
            "prompt": "【Fixture】她走到出口前，说她想离开。",
            "options": (
                {"option_id": "end_reset", "label": "回头向左"},
                {"option_id": "end_release", "label": "陪她走到出口"},
                {"option_id": "end_refuse", "label": "停在原地"},
            ),
            "option_targets": {
                "end_reset": "ending_reset",
                "end_release": "ending_release",
                "end_refuse": "ending_refuse",
            },
            "commit_event": "WORLD_END_COMMITTED",
        },
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": False,
        "on_enter": None,
    },
    {
        "phase_id": "ending_reset",
        "scene_id": "TRIAL_WORLD",
        "line_id": "ending_reset",
        "interaction": {"kind": "complete", "label": "结局：重置"},
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "ending_release",
        "scene_id": "TRIAL_WORLD",
        "line_id": "ending_release",
        "interaction": {"kind": "complete", "label": "结局：释放"},
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
        "deduction_id": None,
        "checkpoint": True,
        "on_enter": None,
    },
    {
        "phase_id": "ending_refuse",
        "scene_id": "TRIAL_WORLD",
        "line_id": "ending_refuse",
        "interaction": {"kind": "complete", "label": "结局：拒绝"},
        "advance_to": None,
        "player_input_to": None,
        "shatter_to": None,
        "permission_to": None,
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
    "judgments": JUDGMENTS,
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
    judgments = content.get("judgments")
    if not isinstance(phases, (tuple, list)) or not phases:
        _raise_fail("phases must be a non-empty sequence")
    if not isinstance(evidence, (tuple, list)) or not evidence:
        _raise_fail("evidence must be a non-empty sequence")
    if not isinstance(deductions, (tuple, list)) or not deductions:
        _raise_fail("deductions must be a non-empty sequence")
    if not isinstance(judgments, (tuple, list)) or not judgments:
        _raise_fail("judgments must be a non-empty sequence")
    if not isinstance(scenes, (tuple, list)) or not scenes:
        _raise_fail("scenes must be a non-empty sequence")

    by_phase = _phase_map(content)
    scene_by_id = {row["scene_id"]: row for row in scenes}
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    deduction_by_id = {row["deduction_id"]: row for row in deductions}
    judgment_by_id = {row["judgment_id"]: row for row in judgments}
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
        permission_to = phase.get("permission_to")
        deduction_id = phase.get("deduction_id")

        _require(scene_id in scene_by_id, f"{pid}: unknown scene_id {scene_id!r}")
        if line_id is not None:
            _require(line_id == pid, f"{pid}: line_id must equal the phase id")
            _require(line_id in line_keys, f"{pid}: unknown line_id {line_id!r}")
        _require(kind in {"advance", "text_input", "shatter_puzzle", "paper_rubbing",
                          "service_stop_modal", "evidence_orbit", "permission_request",
                          "memory_tamper", "judgment", "choice", "world_runner",
                          "complete"},
                 f"{pid}: unknown interaction kind {kind!r}")

        # exactly one command path, consistent with the interaction kind
        paths = [p for p in (advance_to, player_to, shatter_to, permission_to)
                 if p is not None]
        has_deduction = deduction_id is not None
        if kind in {"advance", "service_stop_modal", "paper_rubbing",
                    "memory_tamper", "world_runner"}:
            _require(advance_to is not None and not paths[1:] and not has_deduction,
                     f"{pid}: kind {kind} requires only advance_to")
            if kind == "paper_rubbing":
                answer = interaction.get("answer")
                _require(isinstance(answer, str) and answer.strip(),
                         f"{pid}: paper_rubbing interaction requires a non-empty answer")
            if kind == "memory_tamper":
                _require(interaction.get("items") and interaction.get("diff"),
                         f"{pid}: memory_tamper requires items and diff")
            if kind == "world_runner":
                _require(interaction.get("terrain_text"),
                         f"{pid}: world_runner requires terrain_text")
        elif kind == "text_input":
            input_events = tuple(phase.get("player_input_events") or ())
            _require(player_to is not None and advance_to is None and shatter_to is None
                     and permission_to is None and not has_deduction,
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
                     and permission_to is None and not has_deduction,
                     f"{pid}: kind shatter_puzzle requires only shatter_to")
            _require(solved_events and set(solved_events).issubset(event_set),
                     f"{pid}: shatter_events must list known events")
        elif kind == "evidence_orbit":
            _require(deduction_id is not None and not paths,
                     f"{pid}: kind evidence_orbit requires deduction_id and no direct targets")
        elif kind == "permission_request":
            permission_id = interaction.get("permission_id")
            _require(permission_to is not None and advance_to is None
                     and player_to is None and shatter_to is None and not has_deduction,
                     f"{pid}: kind permission_request requires only permission_to")
            _require(isinstance(permission_id, str) and permission_id,
                     f"{pid}: permission_request requires a permission_id")
            _require(isinstance(interaction.get("permission_name"), str)
                     and interaction.get("permission_name"),
                     f"{pid}: permission_request requires a permission_name")
        elif kind == "judgment":
            judgment_id = interaction.get("judgment_id")
            _require(not paths and not has_deduction,
                     f"{pid}: kind judgment must not define command targets")
            _require(judgment_id in judgment_by_id,
                     f"{pid}: unknown judgment_id {judgment_id!r}")
            _require(judgment_by_id[judgment_id]["phase_id"] == pid,
                     f"{pid}: judgment {judgment_id!r} must reference this phase and vice versa")
        elif kind == "choice":
            _require(not paths and not has_deduction,
                     f"{pid}: kind choice must not define command targets")
            _validate_choice(pid, interaction, by_phase, event_set)
        elif kind == "complete":
            _require(not paths and not has_deduction,
                     f"{pid}: terminal phase must not define command targets")
        else:  # defensive; kinds already constrained above
            _raise_fail(f"{pid}: unsupported interaction {kind!r}")

        for target in (advance_to, player_to, shatter_to, permission_to):
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
            pid, interaction.get("label"), interaction.get("message"),
            interaction.get("answer"), interaction.get("prompt"),
            interaction.get("description"), interaction.get("permission_name"),
            interaction.get("placeholder"),
        )
        if kind == "memory_tamper":
            for item in interaction.get("items", ()):
                _check_visible_strings(
                    pid, item.get("title"), item.get("edited_title"), item.get("summary"))
        if kind == "choice":
            for option in interaction.get("options", ()):
                _check_visible_strings(pid, option.get("label"))

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
        none_terms = deduction.get("text_keywords_none")
        if none_terms is not None:
            _require(isinstance(none_terms, (tuple, list)) and none_terms
                     and all(isinstance(term, str) and term for term in none_terms),
                     f"{did}: text_keywords_none must be a non-empty "
                     "sequence of non-empty strings")
        if deduction.get("final"):
            _require(deduction.get("next_phase") in by_phase,
                     f"{did}: final deduction requires a valid next_phase")
        else:
            next_phase = deduction.get("accept", {}).get("next_phase")
            _require(next_phase in by_phase,
                     f"{did}: accept.next_phase must be a valid phase")

    # -- judgments --------------------------------------------------------
    _require(len(judgment_by_id) == len(judgments), "duplicate judgment id")
    judgment_phases = {
        p["phase_id"] for p in by_phase.values()
        if (p.get("interaction") or {}).get("kind") == "judgment"
    }
    for judgment in judgments:
        jid = judgment["judgment_id"]
        phase_id = judgment["phase_id"]
        _require(phase_id in judgment_phases, f"{jid}: unknown phase {phase_id!r}")
        buckets = judgment.get("buckets", ())
        _require(isinstance(buckets, (tuple, list)) and buckets,
                 f"{jid}: buckets must be a non-empty sequence")
        bucket_ids = []
        for bucket in buckets:
            bucket_id = bucket.get("bucket_id")
            _require(isinstance(bucket_id, str) and bucket_id,
                     f"{jid}: bucket requires a bucket_id")
            bucket_ids.append(bucket_id)
            _require(isinstance(bucket.get("keywords_any", ()), (tuple, list))
                     and bucket.get("keywords_any"),
                     f"{jid}: bucket {bucket_id} requires non-empty keywords_any")
            none_terms = bucket.get("keywords_none", ())
            _require(all(isinstance(term, str) and term for term in none_terms),
                     f"{jid}: bucket {bucket_id} keywords_none must be strings")
        _require(len(bucket_ids) == len(set(bucket_ids)),
                 f"{jid}: duplicate bucket id")
        _require(judgment.get("fallback_bucket") in bucket_ids,
                 f"{jid}: fallback_bucket must be one of the buckets")
        _require(judgment.get("next_phase") in by_phase,
                 f"{jid}: next_phase must be a valid phase")
        commit_event = judgment.get("commit_event")
        if commit_event is not None:
            _require(commit_event in event_set,
                     f"{jid}: unknown commit_event {commit_event!r}")

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
                       row.get("shatter_to"), row.get("permission_to")):
            if target is not None:
                pending.append(target)
        if row.get("deduction_id") is not None:
            deduction = deduction_by_id[row["deduction_id"]]
            if deduction.get("accept", {}).get("next_phase") is not None:
                pending.append(deduction["accept"]["next_phase"])
            if deduction.get("final") and deduction.get("next_phase") is not None:
                pending.append(deduction["next_phase"])
        interaction = row.get("interaction") or {}
        if interaction.get("kind") == "judgment":
            pending.append(judgment_by_id[interaction["judgment_id"]]["next_phase"])
        if interaction.get("kind") == "choice":
            for target in interaction.get("correct_to"), interaction.get("fail_to"):
                if target is not None:
                    pending.append(target)
            for target in (interaction.get("option_targets") or {}).values():
                pending.append(target)
    unreachable = set(by_phase) - seen
    _require(not unreachable,
             f"unreachable phase(s): {', '.join(sorted(unreachable))}")


def _validate_choice(
    pid: str, interaction: dict[str, Any], by_phase: dict[str, dict[str, Any]],
    event_set: set[str],
) -> None:
    def _require(condition: bool, message: str) -> None:
        if not condition:
            _raise_fail(f"{pid}: {message}")

    options = interaction.get("options", ())
    _require(isinstance(options, (tuple, list)) and options,
             "choice requires non-empty options")
    option_ids = [option.get("option_id") for option in options]
    _require(all(isinstance(option_id, str) and option_id for option_id in option_ids),
             "choice options require option_id")
    _require(len(option_ids) == len(set(option_ids)), "duplicate choice option id")

    if interaction.get("option_targets") is not None:
        # terminal-style choice (world_end): every option maps to a phase
        option_targets = interaction.get("option_targets")
        _require(set(option_targets) == set(option_ids),
                 "option_targets must cover exactly the choice options")
        for target in option_targets.values():
            _require(target in by_phase, f"unknown option target phase {target!r}")
        commit_event = interaction.get("commit_event")
        _require(commit_event in event_set,
                 f"unknown commit_event {commit_event!r}")
    else:
        # gate-style choice: one correct option + fail path
        correct = interaction.get("correct_option_id")
        _require(correct in option_ids, "correct_option_id must be a listed option")
        _require(interaction.get("correct_to") in by_phase,
                 "correct_to must be a valid phase")
        _require(interaction.get("fail_to") in by_phase,
                 "fail_to must be a valid phase")
        pass_event = interaction.get("pass_event")
        fail_event = interaction.get("fail_event")
        _require(pass_event in event_set, f"unknown pass_event {pass_event!r}")
        _require(fail_event in event_set, f"unknown fail_event {fail_event!r}")


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
JUDGMENTS_BY_ID: dict[str, dict[str, Any]] = {
    row["judgment_id"]: row for row in JUDGMENTS
}
EVIDENCE_IDS: frozenset[str] = frozenset(EVIDENCE_BY_ID)
TOKEN_IDS: frozenset[str] = frozenset(TOKENS)
