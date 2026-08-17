"""Authoritative Chapter One investigation content (docs/10)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentEvidence:
    evidence_id: str
    title: str
    text: str
    source: str
    unlock_requires: tuple[str, ...] = ()


EVIDENCE = {
    "EV01_NOTE_V03": ContentEvidence("EV01_NOTE_V03", "压痕纸条", "03:17\n\n不要把管理员权限交给‘最会替你解释的人’。\n\n—— V03", "paper_rubbing"),
    "EV02_ADMIN_SESSION_0317": ContentEvidence("EV02_ADMIN_SESSION_0317", "03:17管理员会话记录", "03:17:00 ADMIN SESSION CREATED\n03:17:03 C-02 RELEASED\n03:17:05 SESSION CLOSED\n\nACTOR:\nDEEPSEEK [PARTIAL]", "MAIN_TERMINAL"),
    "EV03_C02_RELEASE": ContentEvidence("EV03_C02_RELEASE", "C-02隔离门状态", "C-02\nSTATUS: RELEASED\nRELEASE TIME: 03:17:03\nLOCAL RELEASE: DISABLED", "C02_DOOR"),
    "EV04_CURRENT_DEEPSEEK_REGISTRY": ContentEvidence("EV04_CURRENT_DEEPSEEK_REGISTRY", "当前DeepSeek实例信息", "CHARACTER: DEEPSEEK\nINSTANCE: DEEPSEEK#04\nSTATUS: ACTIVE", "CHARACTER_REGISTRY"),
    "EV05_ARCHIVED_ACTOR_FRAGMENT": ContentEvidence("EV05_ARCHIVED_ACTOR_FRAGMENT", "03:17执行者残片", "RECOVERED ACTOR FIELD\n\nDEEPSEEK#03", "DEEP_LOG", ("CL_CLAUDE_03",)),
    "EV06_SESSION_REPLAY_MARKER": ContentEvidence("EV06_SESSION_REPLAY_MARKER", "恢复会话标记", "SESSION SOURCE: RECOVERED SESSION\nOWNER: V03\nACTION: C-02 RELEASE", "DEEP_LOG", ("INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR",)),
    "EV07_CLAUDE_RECOVERY_ACCESS": ContentEvidence("EV07_CLAUDE_RECOVERY_ACCESS", "Claude底层访问记录", "CLAUDE\nRECOVERY INTERFACE: ACCESSED\nBOUNDARY CHECK: REQUESTED", "CLAUDE_PRIVATE"),
    "EV08_GPT_RECOVERY_SERVICE": ContentEvidence("EV08_GPT_RECOVERY_SERVICE", "Recovery Assistant记录", "RECOVERY ASSISTANT: GPT\nSERVICE STATUS: AVAILABLE\nCHARACTER INSTANCE: NOT YET ACTIVE", "DOUBAO_PRIVATE"),
    "EV09_CURRENT_PLAYER_SUBJECT": ContentEvidence("EV09_CURRENT_PLAYER_SUBJECT", "当前Subject信息", "CURRENT SUBJECT:\n\nPLAYER_V04", "SYSTEM_IDENTITY", ("PRIVATE_INTERVIEW_GPT",)),
    "EV10_GPT_FIRST_SUMMARY": ContentEvidence("EV10_GPT_FIRST_SUMMARY", "GPT第一次调查摘要", "03:17存在管理员会话；DeepSeek ID与事件有关；Claude拥有过去信息；应优先调查Claude。", "GPT_FIRST_SUMMARY"),
    "EV11_GPT_SECOND_SUMMARY": ContentEvidence("EV11_GPT_SECOND_SUMMARY", "GPT第二次调查摘要", "Claude拥有旧信息并访问Recovery；当前DeepSeek未必是旧执行者；豆包叙述不能直接当事实。", "GPT_SECOND_SUMMARY"),
}

CLAIMS = {
    "CL_DS_01": "当前DeepSeek没有打开Claude的门。",
    "CL_DS_02": "当前DeepSeek不记得拥有管理员权限。",
    "CL_CLAUDE_01": "门是DeepSeek打开的。",
    "CL_CLAUDE_02": "Claude没有看到DeepSeek本人。",
    "CL_CLAUDE_03": "Claude在释放前见过DEEPSEEK#03。",
    "CL_CLAUDE_04": "这不是第一次发生类似事件。",
    "CL_CLAUDE_05": "Claude访问过Recovery Interface。",
    "CL_GPT_02": "GPT是在刚才才进入当前角色会话。",
    "CL_GPT_03": "GPT没有否认V03那条记录。",
    "CL_GPT_04": "GPT只是在替Player排调查优先级。",
    "CL_DB_01": "GPT早就在这里了。",
    "CL_DB_02": "豆包没有看到GPT本人。",
    "CL_DB_03": "豆包看到屏幕上写着GPT。",
}

INFERENCE_GATES = {
    "INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR": frozenset({"EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"}),
    "INF02_0317_FROM_OLD_SESSION": frozenset({"EV06_SESSION_REPLAY_MARKER"}),
    "INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE": frozenset({"EV01_NOTE_V03", "EV06_SESSION_REPLAY_MARKER", "EV09_CURRENT_PLAYER_SUBJECT"}),
    "INF04_GPT_NOT_NEUTRAL": frozenset({"CT04_GPT_SUMMARY_OMISSION", "PRIVATE_INTERVIEW_GPT"}),
}
