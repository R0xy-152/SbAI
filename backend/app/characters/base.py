"""Character Runtime interface and request/response types (docs/04 §4-5, §40)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.providers.base import LLMProvider

if TYPE_CHECKING:
    from app.narrative.inquiry import Inquiry


@dataclass
class CharacterRequest:
    """Logical input to a character runtime (docs/04 §5)."""

    character_id: str
    player_message: str
    recent_conversation: list[dict] = field(default_factory=list)
    # Authorized narrative context built by the character's Context Builder
    # (docs/04 §15-17): already filtered to what this character may know.
    environment_info: str = ""
    # Authorized Narrative Context (docs/04 §8): the minimal story context —
    # relevant flags/facts the character is entitled to for this turn
    # (docs/06 §18). Provided by the Narrative Runtime through the Context
    # Builder; the character never loads raw State itself.
    narrative_context: str = ""
    # Memory context (docs/04 §12): the historical interactions the character
    # may use this turn, selected by the Memory system (docs/05 §37-38). The
    # runtime consumes the result; it never decides storage or retrieval.
    memory_context: str = ""
    # Narrative Directive (docs/03 §24, docs/04 §14, §18.4): the per-turn
    # narrative goal the current reply must carry — 叙事目标 / 允许范围 /
    # 禁止提前透露 — authored by the Narrative Runtime and handed in only when
    # this turn carries story purpose. It never prescribes exact lines and
    # never mutates Game State. Empty on ordinary turns.
    narrative_directive: str = ""
    # Current Character State (docs/04 §9): the character's persistent mood this
    # turn, seeded by the CharacterStateService and injected into the prompt as
    # the "current character state" layer (docs/04 §18.3). None when the state
    # is not tracked (e.g. scripted lines, or no mood committed yet).
    mood: CharacterMood | None = None
    # The character's own reasoning from the previous turn, fed back so its
    # train of thought is continuous (docs/04 §9 CharacterState.last_reasoning).
    # Empty on the first turn or when the previous reply carried no reasoning.
    last_reasoning: str = ""
    # A bounded question proposal, never Ground Truth and never a state change.
    inquiry: Inquiry | None = None
    # Immutable evidence explicitly shown to this character; the player
    # inventory is intentionally not exposed here.
    presented_evidence: list[dict] = field(default_factory=list)


@dataclass
class MemoryProposal:
    """Something in this turn that may be worth remembering long-term (docs/04 §44)."""

    type: str
    content: str


@dataclass
class ActionProposal:
    """A game behavior the character would like to happen (docs/04 §45).

    A proposal only: it must be routed through the Narrative Runtime, never
    applied directly to Game State.
    """

    type: str
    target: str | None = None


# Named emotion / animation allow-lists (docs/04 §42-43). The model must pick
# from these; it must not emit rendering parameters. `surprised` was added for
# the Script DSL's deterministic reactions (docs/12 §19); the small_jump /
# slide_in_* animations are the CharacterStage's recommended named set
# (docs/12 §11).
# docs/16 §0 问题4 固定译文对齐；jealous/nervous 于 docs/16 之后的
# 差分立绘规范化任务加入（chatgpt_chicu→jealous、deepseek_jinzhang→nervous）。
ALLOWED_EMOTIONS = frozenset(
    {"neutral", "happy", "annoyed", "angry", "embarrassed", "serious", "surprised", "jealous", "nervous", "sad"}
)
ALLOWED_ANIMATIONS = frozenset({"none", "shake", "strong_shake", "fade_in", "fade_out", "small_jump", "slide_in_left", "slide_in_right"})


@dataclass
class CharacterMood:
    """Per-character persistent two-axis mood (docs/04 §9: `character_state`).

    ``positive`` (积极值) and ``excitement`` (激动值) are each in [-1, 1]. Unlike
    the named ``emotion`` — a per-turn presentation label that selects a sprite
    (docs/04 §42) — the mood is an *internal* state that evolves turn over turn
    and is fed back into the next prompt to remove the "AI 人机感" (the reference
    template's core trick). It never reaches the Frontend.
    """

    positive: float = 0.0
    excitement: float = 0.0

    @staticmethod
    def _clamp(value: float) -> float:
        return max(-1.0, min(1.0, value))

    def clamped(self) -> "CharacterMood":
        return CharacterMood(
            positive=self._clamp(self.positive),
            excitement=self._clamp(self.excitement),
        )

    @staticmethod
    def from_dict(data) -> "CharacterMood | None":
        """Parse the model's `mood` output, clamping to [-1, 1].

        Returns None when the value is absent or not two numbers, so a bad mood
        never rejects the whole reply — the caller simply keeps the previous
        mood (tolerant schema, docs/04 §48).
        """
        if not isinstance(data, dict):
            return None
        try:
            positive = float(data.get("positive"))
            excitement = float(data.get("excitement"))
        except (TypeError, ValueError):
            return None
        return CharacterMood(positive=positive, excitement=excitement).clamped()


@dataclass
class CharacterState:
    """Per-character persistent runtime state (docs/04 §9).

    Grows from the first concrete field (the two-axis mood) into the richer
    internal state a "thinking" character needs. ``last_reasoning`` is the
    character's own "why I replied this way" from the previous turn, fed back
    so its train of thought stays continuous instead of resetting every turn.
    Like ``mood``, it is internal only and never reaches the Frontend.
    """

    mood: CharacterMood | None = None
    last_reasoning: str = ""


@dataclass
class CharacterResponse:
    """Validated output every runtime must produce (docs/04 §40).

    TV-05 makes the response structured: beyond the spoken dialogue it carries
    a named emotion, an animation proposal, and long-term memory / game-action
    proposals. Everything here is validated before it is accepted (docs/04 §48).
    """

    character_id: str
    dialogue: str
    emotion: str = "neutral"
    animation_proposal: str = "none"
    memory_proposals: list[MemoryProposal] = field(default_factory=list)
    action_proposals: list[ActionProposal] = field(default_factory=list)
    fact_refs: list[str] = field(default_factory=list)
    # Evidence deliberately selected to frame this response. The Backend
    # validates it against what was presented to the speaker.
    evidence_refs: list[str] = field(default_factory=list)
    # Doubao keeps what she observed separate from how she interpreted it.
    observed_fact_refs: list[str] = field(default_factory=list)
    interpretation: str | None = None
    claim_refs: list[str] = field(default_factory=list)
    # The model's own "why I replied this way" (docs/04 §47, the reference
    # template's "逻辑链拷打" reason field). Internal only: it is never copied
    # into the API response or history, so the player never sees it.
    reasoning: str = ""
    # The model's updated mood after this turn (docs/04 §9). Committed to the
    # CharacterStateService only when the reply passes validation. None = keep
    # the previous mood (the model did not output a valid mood).
    next_mood: CharacterMood | None = None


class CharacterResponseValidationError(Exception):
    """The model's raw output failed Schema Validation (docs/04 §48)."""


def parse_character_response(raw: str, expected_character_id: str) -> CharacterResponse:
    """Schema Validation (docs/04 §48): parse the model's raw text into a
    CharacterResponse.

    Checks: required fields present, correct types, character_id matches the
    expected character, emotion/animation in the allow-lists, and proposal
    structure. Raises CharacterResponseValidationError on any violation, so
    invalid content can be rejected / repaired / fallen back instead of being
    presented to the player.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CharacterResponseValidationError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CharacterResponseValidationError("response must be a JSON object")

    character_id = data.get("character_id")
    if not isinstance(character_id, str) or not character_id:
        raise CharacterResponseValidationError("character_id must be a non-empty string")
    if character_id != expected_character_id:
        raise CharacterResponseValidationError(
            f"character_id {character_id!r} does not match expected {expected_character_id!r}"
        )

    dialogue = data.get("dialogue")
    if not isinstance(dialogue, str) or not dialogue.strip():
        raise CharacterResponseValidationError("dialogue must be a non-empty string")

    emotion = data.get("emotion")
    if not isinstance(emotion, str) or emotion not in ALLOWED_EMOTIONS:
        raise CharacterResponseValidationError(f"emotion {emotion!r} is not in the allowed set")

    animation = data.get("animation_proposal")
    if not isinstance(animation, str) or animation not in ALLOWED_ANIMATIONS:
        raise CharacterResponseValidationError(
            f"animation_proposal {animation!r} is not in the allowed set"
        )

    return CharacterResponse(
        character_id=character_id,
        dialogue=dialogue.strip(),
        emotion=emotion,
        animation_proposal=animation,
        memory_proposals=_parse_memory_proposals(data.get("memory_proposals")),
        action_proposals=_parse_action_proposals(data.get("action_proposals")),
        fact_refs=_parse_fact_refs(data.get("fact_refs")),
        evidence_refs=_parse_evidence_refs(data.get("evidence_refs")),
        observed_fact_refs=_parse_observed_fact_refs(data.get("observed_fact_refs")),
        interpretation=_parse_interpretation(data.get("interpretation")),
        claim_refs=_parse_claim_refs(data.get("claim_refs")),
        reasoning=_parse_reasoning(data.get("reasoning")),
        next_mood=CharacterMood.from_dict(data.get("mood")),
    )


def _parse_reasoning(value) -> str:
    """The optional reasoning text; absent or non-string becomes "". Tolerant:
    a missing reasoning never rejects the reply (docs/04 §48)."""
    return value.strip() if isinstance(value, str) else ""


def _parse_memory_proposals(value) -> list[MemoryProposal]:
    if value is None:
        raise CharacterResponseValidationError("memory_proposals is required")
    if not isinstance(value, list):
        raise CharacterResponseValidationError("memory_proposals must be a list")
    proposals = []
    for item in value:
        if not isinstance(item, dict):
            raise CharacterResponseValidationError("each memory_proposal must be an object")
        proposal_type = item.get("type")
        content = item.get("content")
        if not isinstance(proposal_type, str) or not proposal_type:
            raise CharacterResponseValidationError(
                "memory_proposal.type must be a non-empty string"
            )
        if not isinstance(content, str) or not content:
            raise CharacterResponseValidationError(
                "memory_proposal.content must be a non-empty string"
            )
        proposals.append(MemoryProposal(type=proposal_type, content=content))
    return proposals


def _parse_action_proposals(value) -> list[ActionProposal]:
    if value is None:
        raise CharacterResponseValidationError("action_proposals is required")
    if not isinstance(value, list):
        raise CharacterResponseValidationError("action_proposals must be a list")
    proposals = []
    for item in value:
        if not isinstance(item, dict):
            raise CharacterResponseValidationError("each action_proposal must be an object")
        proposal_type = item.get("type")
        if not isinstance(proposal_type, str) or not proposal_type:
            raise CharacterResponseValidationError(
                "action_proposal.type must be a non-empty string"
            )
        target = item.get("target")
        if target is not None and not isinstance(target, str):
            raise CharacterResponseValidationError("action_proposal.target must be a string")
        proposals.append(ActionProposal(type=proposal_type, target=target))
    return proposals


def _parse_fact_refs(value) -> list[str]:
    if value is None:
        raise CharacterResponseValidationError("fact_refs is required")
    if not isinstance(value, list) or not all(isinstance(ref, str) for ref in value):
        raise CharacterResponseValidationError("fact_refs must be a list of strings")
    return list(value)


def _parse_evidence_refs(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(ref, str) for ref in value):
        raise CharacterResponseValidationError("evidence_refs must be a list of strings")
    if len(set(value)) != len(value):
        raise CharacterResponseValidationError("evidence_refs must not contain duplicates")
    return list(value)


def _parse_observed_fact_refs(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(ref, str) for ref in value):
        raise CharacterResponseValidationError("observed_fact_refs must be a list of strings")
    return list(value)


def _parse_interpretation(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CharacterResponseValidationError("interpretation must be a non-empty string")
    return value.strip()


def _parse_claim_refs(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(ref, str) for ref in value):
        raise CharacterResponseValidationError("claim_refs must be a list of strings")
    return list(value)


class CharacterRuntime(ABC):
    character_id: str = ""

    @abstractmethod
    def respond(self, request: CharacterRequest) -> CharacterResponse:
        """Produce the character's reply for this request."""

    def safe_fallback(self) -> CharacterResponse:
        """A story-neutral reply used when a produced reply cannot be
        presented (docs/04 §54). Generative runtimes override this with
        per-character lines; the base returns a minimal neutral line."""
        return CharacterResponse(character_id=self.character_id, dialogue="……")


STRUCTURED_OUTPUT_INSTRUCTIONS = (
    "\n\n输出格式（必须严格遵守）：\n"
    "你只能输出一个 JSON 对象，不要包含任何其他文字、解释、前缀，"
    "也不要使用 markdown 代码块标记。\n"
    "JSON 结构示例：\n"
    '{"character_id": "deepseek", "dialogue": "你要说的话", "emotion": "neutral", '
    '"animation_proposal": "none", "memory_proposals": [], "action_proposals": [], '
    '"fact_refs": [], "reasoning": "你为什么要这样回复", '
    '"mood": {"positive": 0.0, "excitement": 0.0}}\n'
    "字段要求：\n"
    "- dialogue：你要说的话本身，保持你的口癖，是完整的自然句子。\n"
    "- emotion：必须且只能是 neutral、happy、annoyed、angry、embarrassed、serious、surprised、jealous、nervous、sad 之一。\n"
    "- animation_proposal：必须且只能是 none、shake、strong_shake、fade_in、fade_out 之一。\n"
    "- memory_proposals：只有 Player 明确提到值得长期记住的信息"
    "（如名字、喜好、害怕的事物）时才填入，否则为空数组。\n"
    "  元素必须是 {\"type\": \"类别\", \"content\": \"一句话说明\"}，"
    "例如 {\"type\": \"player_name\", \"content\": \"Player说自己叫阿明\"}；"
    "content 必须是一句完整的话，不要使用 value 等其它字段名。\n"
    "- action_proposals：当前阶段通常为空数组。\n"
    "- fact_refs：当前阶段为空数组。\n"
    "- reasoning：用 1-2 句说明你为什么要这样回复（结合你的人设、当前语境和你此刻的心情）。"
    "玩家看不到这段话，它只用来让你先想清楚再开口。\n"
    "- mood：你回复完之后的新心情，是一个 {\"positive\": 数值, \"excitement\": 数值} 对象，"
    "两个数值都在 -1 到 1 之间（positive=积极值，excitement=激动值），"
    "要让心情随对话自然变化。\n"
    "9 个字段都必须出现。"
)


# Shared dialogue-style rules appended to every generative character's system
# prompt (docs/04 §18.1 Global Runtime Rules). The goal is to make a reply read
# like a person with their own intent and knowledge blind spots, not an
# omniscient, even-tempered assistant: no template politeness, a reason to be
# talking, admitted uncertainty, recall of what was already said, and short
# human-length turns.
CONVERSATION_STYLE_RULES = (
    "\n\n对话风格（每一句回复都必须遵守）：\n"
    "1. 禁止助手腔：不要出现“作为AI”“很高兴为你”“当然可以”“请问还有什么需要帮助”"
    "之类的客套；像有自己情绪和想法的人一样说话，而不是客服。\n"
    "2. 你有自己的目的，不是在答题：你可以追问、转移话题、拒绝回答、"
    "只透露一部分，也可以反问“那你呢”；不要有问必答、问什么答什么。\n"
    "3. 不确定就承认：不知道、没听清、想不起来的事，就表现出犹豫或不确定，"
    "不要装作全知全能。\n"
    "4. 记得并引用：如果玩家之前说过的话和现在相关，自然地提起它（比如“你刚才说……”）。\n"
    "5. 一次只说 1–3 句，像真人对话一样短促、留白，不要长篇大论。\n"
)


def format_conversation(recent: list[dict]) -> str:
    """Render the recent messages into the transcript the model sees
    (docs/05 §7: player messages, character messages, and (later) audible
    messages from other characters)."""
    lines = []
    for message in recent:
        role = message.get("role")
        content = message.get("content", "")
        if role == "player":
            lines.append(f"Player：{content}")
        elif role == "character":
            speaker = message.get("character_id", "DeepSeek")
            lines.append(f"{speaker}：{content}")
    return "\n".join(lines)


class GenerativeRuntime(CharacterRuntime):
    """Shared respond flow for generative characters (docs/04 §48-55).

    Every generative character answers as a Structured Character Response;
    the raw output goes through Schema Validation, on failure the runtime
    repairs once with the specific error (docs/04 §53) and then falls back to
    a safe, story-neutral line (docs/04 §54). A provider failure (timeout /
    HTTP / empty) is a recoverable error and is propagated, not masked by a
    fabricated reply (docs/04 §55).

    Subclasses set `character_id`, `persona_system` and their own `fallback_lines`
    (docs/04 §62.1: the public design must not be limited to two characters).
    """

    character_id: str = ""
    persona_system: str = ""
    fallback_lines: list[str] = []

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def _system_prompt(self) -> str:
        return self.persona_system + CONVERSATION_STYLE_RULES + STRUCTURED_OUTPUT_INSTRUCTIONS

    def _build_user_message(self, request: CharacterRequest) -> str:
        """Compose the user turn: the authorized narrative context (docs/04 §8),
        authorized environment context (docs/04 §20), selected memories
        (docs/04 §12), the recent conversation (docs/05 §7), and the current
        player message."""
        if (
            not request.narrative_context
            and not request.environment_info
            and not request.memory_context
            and not request.narrative_directive
            and not request.recent_conversation
            and request.mood is None
            and not request.last_reasoning
        ):
            return request.player_message
        parts: list[str] = []
        if request.mood is not None:
            # docs/04 §18.3: current character state is the first dynamic layer —
            # the model's own persistent mood, so the reply stays emotionally
            # continuous instead of resetting each turn.
            parts.append(
                "你当前的心情：积极"
                f"{request.mood.positive:.1f} / 激动{request.mood.excitement:.1f}"
                "（范围都是 -1 到 1）。请让你的语气与你当前的心情一致。"
            )
        if request.last_reasoning:
            # docs/04 §9: the character's own previous train of thought, so the
            # reply continues a running inner monologue instead of resetting.
            parts.append(
                "你上一轮心里想的是："
                + request.last_reasoning
                + "。请延续这个想法，不要每轮都像重新开始。\n"
            )
        if request.narrative_context:
            parts.append("当前剧情：\n" + request.narrative_context)
        if request.environment_info:
            parts.append("当前环境：\n" + request.environment_info)
        if request.memory_context:
            parts.append("回忆：\n" + request.memory_context)
        if request.narrative_directive:
            # docs/04 §18: the directive sits after the authorized context and
            # before the conversation — it states this turn's story goal, not
            # lines to say.
            parts.append("本轮叙事指令：\n" + request.narrative_directive)
        if request.recent_conversation:
            parts.append("近期对话：\n" + format_conversation(request.recent_conversation))
        parts.append(f"Player 现在说：{request.player_message}")
        return "\n\n".join(parts)

    def _call(self, user: str) -> str:
        return self._provider.complete(
            system=self._system_prompt(),
            user=user,
            # Thinking mode stays on (DeepSeek default) so the model reasons
            # before answering — the reference template's "逻辑链拷打". The
            # model's explicit reason is also captured in the structured
            # output's `reasoning` field, and the `max_tokens` budget is raised
            # so the reasoning budget does not eat into the reply.
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

    def safe_fallback(self) -> CharacterResponse:
        return CharacterResponse(
            character_id=self.character_id,
            dialogue=self.fallback_lines[0],
        )

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        user = self._build_user_message(request)
        raw = self._call(user)
        try:
            return parse_character_response(raw, self.character_id)
        except CharacterResponseValidationError as exc:
            # docs/04 §53: first failure → one targeted repair attempt that
            # tells the model exactly what failed, then safe fallback.
            repair_user = (
                f"{user}\n\n[系统提示] 你上一次的输出没有通过格式校验：{exc}。"
                "请重新输出：只输出一个符合全部字段要求的 JSON 对象，不要有任何多余文字。"
            )
        raw = self._call(repair_user)
        try:
            return parse_character_response(raw, self.character_id)
        except CharacterResponseValidationError:
            return self.safe_fallback()
