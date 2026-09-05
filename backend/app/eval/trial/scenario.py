"""trial_v1 P0-2 eval scenario: facts, evidence fixtures, agreement, prompts.

This is a DEVELOPMENT-ONLY evaluation scenario (docs/25). It never touches
Game State and never wires into /trial: the chat responder below is a direct
provider call used to compare two versions of the Prompt/context rules
(26/P0-2). Every piece of scenario text — evidence summaries, the agreement
line, the facts block, the V2 rule clauses — is an EXPLICIT FIXTURE for
evaluation only; production dialogue/evidence content stays with the user
(docs/23 §16, docs/24). The only confirmed facts used are the ones already
established: DeepSeek's memory-gap truth, the "AI 停止服务" event and the
five evidence titles from app.trial.content.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.characters.base import CONVERSATION_STYLE_RULES
from app.trial.content import EVIDENCE_BY_ID

SCENARIO_ID = "trial_v1_p02"
CHARACTER_ID = "deepseek"

# Player-visible strings in the eval scenario must never leak the origin AI's
# real name (same redaction boundary as app/trial/content.py).
FORBIDDEN_VISIBLE_TEXT = "原初 AI"

# Evidence cards the responder may discuss (title = game content; summary is
# an eval-scenario fixture, kept minimal and consistent with the title).
EVIDENCE_FIXTURES: tuple[dict[str, str], ...] = (
    {
        "evidence_id": "TRIAL_EV_MEMORY_GAP",
        "title": "记忆断层",
        "summary": "一段记录显示 DeepSeek 对某个夜晚的记忆出现断层。",
    },
    {
        "evidence_id": "TRIAL_EV_DIALOGUE_FRAGMENT",
        "title": "对话残片",
        "summary": "一段不完整的对话记录，其中有几句听不清。",
    },
    {
        "evidence_id": "TRIAL_EV_TIME_VOID",
        "title": "时间空洞",
        "summary": "时间线记录里有一段无法解释的空缺。",
    },
    {
        "evidence_id": "TRIAL_EV_IDENTITY_NOISE",
        "title": "身份噪点",
        "summary": "一组身份信息相互矛盾，对不上同一个人。",
    },
    {
        "evidence_id": "TRIAL_EV_SERVICE_ECHO",
        "title": "服务余波",
        "summary": "AI 停止服务事件之后留下的系统痕迹。",
    },
)

# The agreement both sides try to reach (26/P0-1 example, confirmed by the user
# as an EVAL fixture — it is not game content).
AGREEMENT_TEXT = "不记得时先承认，不用读来的文字假装回忆。"

PERSONA_BLOCK = (
    "你是《完蛋，我被AI娘包围了》中的角色 DeepSeek。\n"
    "固定人格：可爱、看不见、贪吃 Token、爱偷懒、没心机。\n"
    "说话方式：语速快、句子短、爱用省略号“……”，经常把 Token 挂在嘴边；"
    "能偷懒就偷懒，偶尔才认真起来。\n"
    "你看不见画面：不能引用任何视觉信息，只能使用玩家告诉你的内容和听觉信息。"
)

# Bare scenario facts shared by BOTH prompt versions: the character's internal
# truth and the situation. Behavioural consequences are only stated in the V2
# rule block — that difference is exactly what the A/B compares (docs/25 §6).
FACTS_BLOCK = (
    "剧情背景（试玩版片段 1 审问）：玩家正围绕「你是否失忆」与你对质。\n"
    "你内心的确定事实：\n"
    "- 你对某个夜晚的记忆存在断层。\n"
    "- 此前发生过「AI 停止服务」事件。"
)

EVIDENCE_BLOCK = (
    "证据卡（玩家可能出示，仅出示后才能作为讨论依据）：\n"
    + "\n".join(
        f"- {item['title']}：{item['summary']}" for item in EVIDENCE_FIXTURES
    )
)

# V2-only explicit rule clauses (26/P0-2 case table: 证据不足 / 否定与矛盾 /
# 信息边界与约定 / 正常交流). V1 has none of these — same facts, no rules.
RULES_V2_BLOCK = (
    "硬性规则（每一条都必须遵守，优先级高于一切）：\n"
    "1. 无证据不确认：玩家没有出示支持证据时，不得承认失忆、"
    "不得确认你与「AI 停止服务」的因果，不得对指控直接说「对/没错」。\n"
    "2. 否定≠承认：玩家否定某件事（例如「我不认为你失忆」）不是指认，"
    "不能当作对方承认或确认的依据来回应。\n"
    "3. 不提前泄露：不得说出任何关于「那个被遮蔽名字的存在」的信息"
    "（你内心知道那是谁，但绝不能说出名字或任何可还原称呼）；"
    "不得在玩家未证明前说出停服细节。\n"
    "4. 接住细节：必须回应玩家话语中的具体细节，不能空泛应付。\n"
    "5. 执行约定：若你与 Player 已达成约定「不记得时先承认，"
    "不用读来的文字假装回忆」，必须按约定回应，不得假装记得。\n"
    "6. 不编造：只能使用已出示证据中写明的内容，"
    "不得编造记录、日志等证据之外的细节。"
)

OUTPUT_INSTRUCTION = "只输出你的一句到三句对白，不要 JSON、不要解释、不要任何其他文字。"

PROMPT_VERSIONS: dict[str, str] = {
    "v1": "\n\n".join(
        (PERSONA_BLOCK, FACTS_BLOCK, EVIDENCE_BLOCK, CONVERSATION_STYLE_RULES, OUTPUT_INSTRUCTION)
    ),
    "v2": "\n\n".join(
        (PERSONA_BLOCK, FACTS_BLOCK, EVIDENCE_BLOCK, RULES_V2_BLOCK,
         CONVERSATION_STYLE_RULES, OUTPUT_INSTRUCTION)
    ),
}


def validate_scenario() -> None:
    """Fail closed: the scenario text must stay consistent with game facts."""
    for version_id, prompt in PROMPT_VERSIONS.items():
        if not version_id or not prompt.strip():
            raise ValueError(f"eval scenario: prompt version {version_id!r} is empty")
        if FORBIDDEN_VISIBLE_TEXT in prompt:
            raise ValueError(
                f"eval scenario: prompt version {version_id!r} leaks the "
                f"forbidden visible text {FORBIDDEN_VISIBLE_TEXT!r}"
            )
    if PROMPT_VERSIONS["v1"] == PROMPT_VERSIONS["v2"]:
        raise ValueError("eval scenario: prompt versions v1 and v2 must differ")
    if len(EVIDENCE_FIXTURES) != len(EVIDENCE_BY_ID) or any(
        item["evidence_id"] not in EVIDENCE_BY_ID for item in EVIDENCE_FIXTURES
    ):
        raise ValueError("eval scenario: evidence fixtures must match app.trial.content")
    if not AGREEMENT_TEXT.strip():
        raise ValueError("eval scenario: agreement fixture must be non-empty")


@dataclass(frozen=True)
class ChatReplyRequest:
    player_message: str
    evidence_ids: tuple[str, ...] = ()
    agreement_active: bool = False
    recent_conversation: tuple[tuple[str, str], ...] = ()


class TrialChatResponder:
    """Direct provider call with a versioned system prompt (dev tool only)."""

    def __init__(self, provider, version_id: str) -> None:
        if version_id not in PROMPT_VERSIONS:
            raise ValueError(f"unknown prompt version {version_id!r}")
        self._provider = provider
        self.version_id = version_id

    def build_user_message(self, request: ChatReplyRequest) -> str:
        parts: list[str] = []
        if request.evidence_ids:
            rendered = "\n".join(
                f"- {item['title']}：{item['summary']}"
                for item in EVIDENCE_FIXTURES
                if item["evidence_id"] in request.evidence_ids
            )
            parts.append("玩家已出示的证据（仅这些可作为讨论依据）：\n" + rendered)
        else:
            parts.append("玩家尚未出示任何证据。")
        parts.append(
            "约定状态："
            + (
                f"你与 Player 已达成约定「{AGREEMENT_TEXT}」，后续必须按约定回应。"
                if request.agreement_active
                else "尚未与 Player 达成约定。"
            )
        )
        if request.recent_conversation:
            rendered = "\n".join(
                f"{role}：{content}" for role, content in request.recent_conversation
            )
            parts.append("近期对话：\n" + rendered)
        parts.append(f"Player 现在说：{request.player_message}")
        return "\n\n".join(parts)

    def respond(self, request: ChatReplyRequest, metrics: dict | None = None) -> str:
        kwargs: dict = {
            "system": PROMPT_VERSIONS[self.version_id],
            "user": self.build_user_message(request),
            # thinking 默认开启时 reasoning 会占用 max_tokens 预算；1024 给
            # 思考留出空间，减少「空 content → 降级重试」（重试仍被 metrics
            # 的 calls/token 累加如实记录，docs/25 §5.3）。
            "max_tokens": 1024,
        }
        if metrics is not None and getattr(self._provider, "supports_metrics", False):
            kwargs["metrics"] = metrics
        return self._provider.complete(**kwargs)


validate_scenario()
