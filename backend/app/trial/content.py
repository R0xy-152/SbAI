"""Temporary, explicitly non-production content for the trial_v1 runtime.

The user has approved the flow and mechanics but not the literal dialogue,
evidence answers, or branch mapping.  Keeping these fixtures in one module
lets the real content replace them without changing TrialRuntime.
"""

from __future__ import annotations

TRIAL_ID = "trial_v1"
ORIGIN_AI_ID = "origin_ai"
ORIGIN_AI_REDACTED_LABEL = "████"

TRIAL_EVIDENCE: tuple[dict, ...] = (
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

TRIAL_EVIDENCE_BY_ID = {item["evidence_id"]: item for item in TRIAL_EVIDENCE}

FIXTURE_LINES = {
    "opening_warm_chat": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：深夜闲聊正式对白待用户确认】",
    },
    "opening_input": {
        "speaker_id": "system",
        "speaker_label": "SYSTEM",
        "text": "【交互测试】输入任意一句话，完成自然语言输入引导。",
    },
    "opening_anomaly": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：察觉异常后的正式对白待用户确认】",
    },
    "opening_shatter": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：画面连接正在断裂】",
    },
    "opening_origin_ai_remains": {
        "speaker_id": ORIGIN_AI_ID,
        "speaker_label": ORIGIN_AI_REDACTED_LABEL,
        "text": "【Fixture：残存意识正式对白待用户确认】",
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

TRIAL_SCENES = {
    "opening": {
        "scene_id": "TRIAL_OPENING",
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
    "fragment_01_deepseek": {
        "scene_id": "TRIAL_FRAGMENT_01_DEEPSEEK",
        "background": "/backgroud/background1.png",
        "fixture_art": True,
        "characters": (
            {"character_id": "deepseek", "display_name": "DeepSeek", "slot": "CENTER"},
        ),
    },
    "fragment_01_group": {
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
}


def validate_fixture_content() -> None:
    ids = [item["evidence_id"] for item in TRIAL_EVIDENCE]
    if len(ids) != len(set(ids)):
        raise ValueError("trial fixture contains duplicate evidence ids")
    for item in TRIAL_EVIDENCE:
        title = item["title"]
        if not 4 <= len(title) <= 5:
            raise ValueError(f"trial evidence title must contain 4-5 characters: {title!r}")
    if "原初 AI" in str(FIXTURE_LINES):
        raise ValueError("origin AI's real label must not enter player-visible fixture lines")


validate_fixture_content()
