"""Chapter-one inquiry interpretation (docs/03-自然语言询问与事实边界)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider

ASK_OBSERVATION_SOURCE = "ASK_OBSERVATION_SOURCE"
ASK_EVENT_TIME = "ASK_EVENT_TIME"
ASK_CHARACTER_KNOWLEDGE = "ASK_CHARACTER_KNOWLEDGE"
ASK_CHARACTER_SUSPICION = "ASK_CHARACTER_SUSPICION"
NOOP = "noop"
AMBIGUOUS = "ambiguous"

INTENTS = frozenset(
    {
        ASK_OBSERVATION_SOURCE,
        ASK_EVENT_TIME,
        ASK_CHARACTER_KNOWLEDGE,
        ASK_CHARACTER_SUSPICION,
    }
)
OUTCOMES = frozenset({NOOP, AMBIGUOUS})
TOPICS = frozenset({"door_open", "timestamp_0317", "admin_session", "evidence"})


@dataclass(frozen=True)
class Inquiry:
    """A non-mutating, finite proposal for a character response."""

    intent: str
    target: str | None = None
    subject: str | None = None
    topic: str | None = None


def _system_prompt(available_characters: set[str], acquired_evidence: set[str]) -> str:
    return (
        "你是第一章调查询问的语义解释器。只把玩家的本句输入映射为受限 JSON，"
        "不回答问题、不创作事实、不推进剧情。\n"
        f"可询问角色：{', '.join(sorted(available_characters)) or '无'}。\n"
        f"玩家已获得证据 ID：{', '.join(sorted(acquired_evidence)) or '无'}。\n"
        "可用 intent：\n"
        "- ASK_OBSERVATION_SOURCE：询问某角色信息来自亲眼观察、记录或推测。\n"
        "- ASK_EVENT_TIME：询问 03:17 或事件发生时间。\n"
        "- ASK_CHARACTER_KNOWLEDGE：询问某角色知道什么、为何知道。\n"
        "- ASK_CHARACTER_SUSPICION：询问某角色是否隐瞒或怀疑什么。\n"
        "只输出一个 JSON：{\"intent\": \"...\", \"target\": null|角色ID, "
        "\"subject\": null|角色ID, \"topic\": null|door_open|timestamp_0317|admin_session|evidence}。\n"
        "普通闲聊输出 {\"intent\": \"noop\"}；语义不清输出 {\"intent\": \"ambiguous\"}。\n"
        "注意：即使产生内部推理也必须极短；JSON 对象必须是输出的最后内容，绝不能为空"
        "（DeepSeek JSON Output 已知概率性空 content 问题的 prompt 侧缓解）。"
    )


class Chapter1InquiryInterpreter:
    """Map free wording to a bounded inquiry without accessing Ground Truth."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def interpret(self, state: NarrativeState, player_message: str) -> Inquiry:
        chapter = state.chapter1
        raw = self._provider.complete(
            system=_system_prompt(chapter.available_characters, chapter.acquired_evidence),
            user=player_message,
            # 512：给 reasoning 留余量，降低空 content 概率（真机 503 复盘）
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        parsed = self._parse(raw, chapter.available_characters)
        if parsed.intent != NOOP:
            return parsed
        return self._mock_safe_fallback(player_message, chapter.available_characters)

    @staticmethod
    def _mock_safe_fallback(player_message: str, available_characters: set[str]) -> Inquiry:
        """Small deterministic fallback for required chapter-one questions.

        MockProvider deliberately does not implement a second LLM persona for
        inquiry classification. These patterns keep the authored Claude
        investigation path playable without an API key; unmatched language
        remains fail-closed as ``noop``.
        """
        normalized = player_message.lower().replace(" ", "")
        if "claude" not in available_characters:
            return Inquiry(NOOP)
        if "亲眼" in normalized or "消息来源" in normalized or "没看到" in normalized:
            return Inquiry(ASK_OBSERVATION_SOURCE, target="claude", subject="deepseek", topic="door_open")
        if "recovery" in normalized or "恢复接口" in normalized:
            return Inquiry(ASK_CHARACTER_KNOWLEDGE, target="claude", topic="evidence")
        if ("谁打开" in normalized or "谁开的" in normalized) and ("门" in normalized or "c-02" in normalized):
            return Inquiry(ASK_CHARACTER_KNOWLEDGE, target="claude", subject="deepseek", topic="door_open")
        if "doubao" in available_characters and "gpt" in normalized and ("早就在" in normalized or "什么时候出现" in normalized):
            return Inquiry(ASK_CHARACTER_SUSPICION, target="doubao", subject="chatgpt", topic="evidence")
        return Inquiry(NOOP)

    @staticmethod
    def _parse(raw: str, available_characters: set[str]) -> Inquiry:
        try:
            data = json.loads(raw)
            intent = data["intent"]
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            return Inquiry(NOOP)
        if not isinstance(intent, str):
            return Inquiry(NOOP)
        if intent in OUTCOMES:
            return Inquiry(intent)
        if intent not in INTENTS:
            return Inquiry(NOOP)

        target = data.get("target")
        subject = data.get("subject")
        topic = data.get("topic")
        if target is not None and (not isinstance(target, str) or target not in available_characters):
            return Inquiry(NOOP)
        if subject is not None and (not isinstance(subject, str) or subject not in available_characters):
            return Inquiry(NOOP)
        if topic is not None and (not isinstance(topic, str) or topic not in TOPICS):
            return Inquiry(NOOP)
        return Inquiry(intent, target=target, subject=subject, topic=topic)
