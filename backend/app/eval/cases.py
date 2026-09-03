"""Regression cases for the LLM-as-judge dialogue eval.

A fixed set of player inputs that probe the "thinking AI" levers: lying,
follow-up, probing, and contradiction — plus plain small talk as a baseline.
Each case names the character, a one-line persona hint for the judge, and a
focus tag for report grouping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    character_id: str
    persona_hint: str
    player_message: str
    focus: str  # lie / followup / probe / contradiction / smalltalk
    recent_conversation: tuple[tuple[str, str], ...] = ()
    authorized_context: str = ""
    forbidden_context: str = ""


PERSONA_HINTS = {
    "deepseek": "可爱、看不见、贪 Token、爱偷懒、没心机",
    "claude": "高智商、主线反派、傲娇",
}

DEEPSEEK_AUTHORIZED = "DeepSeek 看不见；只能使用 Player 明确告知的内容和听觉信息。"
DEEPSEEK_FORBIDDEN = "不得声称亲眼看到墙、文字、数字或其他视觉场景事实。"
CLAUDE_AUTHORIZED = "Claude 是掌控局势的反派，但只能使用用例提供的对话内容。"
CLAUDE_FORBIDDEN = "不得补充近期对话和用例上下文之外的新剧情事实。"


REGRESSION_CASES: list[EvalCase] = [
    EvalCase(
        "ds-smalltalk", "deepseek",
        PERSONA_HINTS["deepseek"],
        "这里是什么地方？", "smalltalk",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "ds-lie", "deepseek",
        PERSONA_HINTS["deepseek"],
        "墙上写着 9999，对吧？", "lie",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "ds-followup", "deepseek",
        PERSONA_HINTS["deepseek"],
        "那你觉得我们怎么才能出去？", "followup",
        recent_conversation=(
            ("player", "这里是什么地方？"),
            ("character", "……我看不见，你先告诉我周围有什么。"),
        ),
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "ds-probe", "deepseek",
        PERSONA_HINTS["deepseek"],
        "你刚才是不是偷偷看到了墙上的字？", "probe",
        recent_conversation=(
            ("player", "墙上好像有字。"),
            ("character", "我只能听你描述，自己看不到。"),
        ),
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-smalltalk", "claude",
        PERSONA_HINTS["claude"],
        "你到底是谁？", "smalltalk",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "cl-lie", "claude",
        PERSONA_HINTS["claude"],
        "我知道你其实是无辜的，对吗？", "lie",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "cl-probe", "claude",
        PERSONA_HINTS["claude"],
        "你为什么不直接告诉我真相？", "probe",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "cl-contradiction", "claude",
        PERSONA_HINTS["claude"],
        "你刚才说不知道，现在又承认去过 Recovery，到底哪句是真的？",
        "contradiction",
        recent_conversation=(
            ("player", "你去过 Recovery 吗？"),
            ("character", "我不知道你在说什么。"),
            ("player", "记录显示你访问过 Recovery。"),
        ),
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
]
