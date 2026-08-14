"""Character Runtime interface and request/response types (docs/04 §4-5, §40)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.providers.base import LLMProvider


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
# from these; it must not emit rendering parameters.
ALLOWED_EMOTIONS = frozenset({"neutral", "happy", "annoyed", "angry", "embarrassed", "serious"})
ALLOWED_ANIMATIONS = frozenset({"none", "shake", "strong_shake", "fade_in", "fade_out"})


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
    )


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
    '"fact_refs": []}\n'
    "字段要求：\n"
    "- dialogue：你要说的话本身，保持你的口癖，是完整的自然句子。\n"
    "- emotion：必须且只能是 neutral、happy、annoyed、angry、embarrassed、serious 之一。\n"
    "- animation_proposal：必须且只能是 none、shake、strong_shake、fade_in、fade_out 之一。\n"
    "- memory_proposals：只有 Player 明确提到值得长期记住的信息"
    "（如名字、喜好、害怕的事物）时才填入，否则为空数组。\n"
    "  元素必须是 {\"type\": \"类别\", \"content\": \"一句话说明\"}，"
    "例如 {\"type\": \"player_name\", \"content\": \"Player说自己叫阿明\"}；"
    "content 必须是一句完整的话，不要使用 value 等其它字段名。\n"
    "- action_proposals：当前阶段通常为空数组。\n"
    "- fact_refs：当前阶段为空数组。\n"
    "7 个字段都必须出现。"
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
        return self.persona_system + STRUCTURED_OUTPUT_INSTRUCTIONS

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
        ):
            return request.player_message
        parts: list[str] = []
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
            max_tokens=1024,
            response_format={"type": "json_object"},
            # Casual roleplay dialogue does not need a chain-of-thought; turning
            # off thinking keeps turns fast and cheap and avoids the reasoning
            # budget eating into max_tokens (docs 思考模式).
            thinking={"type": "disabled"},
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
