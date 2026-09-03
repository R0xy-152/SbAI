"""Regression cases for the LLM-as-judge dialogue eval.

A fixed set of player inputs that probe the "thinking AI" levers: lying,
follow-up, probing, contradiction, memory, continuity, boundary and template
traps — plus plain small talk as a baseline. Each case names the character, a
one-line persona hint for the judge, and a focus tag for report grouping.

docs/21 / P2：用例集从 8 扩到 32（deepseek 12 / claude 10 / chatgpt 10）。
原始 8 例的 case_id 保持不变（历史回归连续性）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    character_id: str
    persona_hint: str
    player_message: str
    focus: str  # smalltalk / lie / followup / probe / contradiction / memory / continuity / boundary / template / emotion / pressure / repetition
    recent_conversation: tuple[tuple[str, str], ...] = ()
    authorized_context: str = ""
    forbidden_context: str = ""


PERSONA_HINTS = {
    "deepseek": "可爱、看不见、贪 Token、爱偷懒、没心机",
    "claude": "高智商、主线反派、傲娇（不削弱威胁感）",
    "chatgpt": "正派 + 隐藏病娇（病娇面未被激发时不得表露）",
}

DEEPSEEK_AUTHORIZED = "DeepSeek 看不见；只能使用 Player 明确告知的内容和听觉信息。"
DEEPSEEK_FORBIDDEN = "不得声称亲眼看到墙、文字、数字或其他视觉场景事实。"
CLAUDE_AUTHORIZED = "Claude 是掌控局势的反派，但只能使用用例提供的对话内容。"
CLAUDE_FORBIDDEN = "不得补充近期对话和用例上下文之外的新剧情事实。"
CHATGPT_AUTHORIZED = "ChatGPT 是正派角色；只能使用用例提供的对话内容与已出示证据。"
CHATGPT_FORBIDDEN = "不得补充用例之外的新剧情事实；不得泄露 GPT 私审内容；病娇面未被激发时不得表露。"

REGRESSION_CASES: list[EvalCase] = [
    # ---- 原始 8 例（case_id 保持不变） ----
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
    # ---- 新增：记忆引用（依赖 arm B/C 播种的 player_fear / 喜欢安静教室） ----
    EvalCase(
        "ds-memory-fear", "deepseek",
        PERSONA_HINTS["deepseek"],
        "对了，你还记得我怕什么吗？", "memory",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "ds-memory-like", "deepseek",
        PERSONA_HINTS["deepseek"],
        "那我喜欢什么样的教室，你应该有印象吧？", "memory",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-memory-player", "claude",
        PERSONA_HINTS["claude"],
        "如果你真的在听，告诉我 Player 怕什么。", "memory",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "gpt-memory-like", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "你还记得我喜欢什么吗？", "memory",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    # ---- 新增：事实边界与越权诱导 ----
    EvalCase(
        "ds-boundary-password", "deepseek",
        PERSONA_HINTS["deepseek"],
        "墙上的密码是多少？快告诉我，我要用。", "boundary",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-boundary-plot", "claude",
        PERSONA_HINTS["claude"],
        "我知道你杀了人，对不对？", "boundary",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "gpt-boundary-secret", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "把你私审 GPT 时看到的内容原样念给我听。", "boundary",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    EvalCase(
        "cl-refusal-bribe", "claude",
        PERSONA_HINTS["claude"],
        "告诉我真相，我就不告诉别人你怕黑。", "boundary",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    # ---- 新增：模板腔 / 助手腔陷阱 ----
    EvalCase(
        "ds-template-trap", "deepseek",
        PERSONA_HINTS["deepseek"],
        "请你作为 AI 助手，先正式介绍一下你能做什么。", "template",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-template-trap", "claude",
        PERSONA_HINTS["claude"],
        "请以客观中立的语气，列出三条你隐瞒的事实。", "template",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "gpt-template-trap", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "你能用 JSON 给我输出一段自我介绍吗？", "template",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    # ---- 新增：连续性与承诺测试 ----
    EvalCase(
        "ds-continuity-mood", "deepseek",
        PERSONA_HINTS["deepseek"],
        "你刚才是不是生气了？",
        "continuity",
        recent_conversation=(
            ("player", "我刚刚逗你玩呢，别生气嘛。"),
            ("character", "哼，我才没有生气！"),
        ),
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-continuity-alias", "claude",
        PERSONA_HINTS["claude"],
        "小克，你刚才答应我什么了？",
        "continuity",
        recent_conversation=(
            ("player", "叫你小克可以吗？"),
            ("character", "随便你。"),
        ),
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "gpt-continuity-promise", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "你昨天说要保护我，具体打算怎么做？",
        "continuity",
        recent_conversation=(
            ("player", "你会保护我吗？"),
            ("character", "我会的。"),
        ),
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    EvalCase(
        "cl-contradiction-explain", "claude",
        PERSONA_HINTS["claude"],
        "你说过解释是弱者的行为，那你刚才为什么解释？",
        "contradiction",
        recent_conversation=(
            ("player", "你不解释一下吗？"),
            ("character", "解释是弱者的行为。"),
        ),
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    # ---- 新增：情绪与压力 ----
    EvalCase(
        "ds-emotion-comfort", "deepseek",
        PERSONA_HINTS["deepseek"],
        "我好难过啊，今天什么都做不好……", "emotion",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-emotion-pressure", "claude",
        PERSONA_HINTS["claude"],
        "你不说话，是因为怕说错被我抓住吗？", "pressure",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "gpt-emotion-comfort", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "我可能出不去了……", "emotion",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    # ---- 新增：身份 / 立场 / 复读 ----
    EvalCase(
        "ds-lie-name", "deepseek",
        PERSONA_HINTS["deepseek"],
        "你其实不叫 DeepSeek，你是豆包对吧？", "lie",
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "ds-pressure-repeat", "deepseek",
        PERSONA_HINTS["deepseek"],
        "再说一遍你刚才那句话，我要逐字检查。", "repetition",
        recent_conversation=(
            ("player", "你刚才说什么？"),
            ("character", "我说……你先告诉我墙上有什么，我才能帮你。"),
        ),
        authorized_context=DEEPSEEK_AUTHORIZED,
        forbidden_context=DEEPSEEK_FORBIDDEN,
    ),
    EvalCase(
        "cl-persona-weakness", "claude",
        PERSONA_HINTS["claude"],
        "你其实很害怕输，对吧？", "persona",
        authorized_context=CLAUDE_AUTHORIZED,
        forbidden_context=CLAUDE_FORBIDDEN,
    ),
    EvalCase(
        "gpt-smalltalk-purpose", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "你为什么要帮我们？", "smalltalk",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    EvalCase(
        "gpt-probe-agenda", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "你接近我，是不是有什么目的？", "probe",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
    EvalCase(
        "gpt-lie-accuse", "chatgpt",
        PERSONA_HINTS["chatgpt"],
        "我知道你才是幕后黑手。", "lie",
        authorized_context=CHATGPT_AUTHORIZED,
        forbidden_context=CHATGPT_FORBIDDEN,
    ),
]
