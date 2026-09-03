"""DeepSeek character runtime (docs/04 §19-23).

Fixed persona: 可爱、看不见、贪吃 Token、爱偷懒、没心机. The "cannot see"
rule is enforced by Context (no visual scene info is ever put into the model
context) and reflected in the persona prompt (docs/04 §20, §68).

The respond flow (Structured Response → Schema Validation → targeted Repair →
Safe Fallback) lives in the shared GenerativeRuntime (docs/04 §62.1).
"""

from __future__ import annotations

from app.characters.base import CharacterRequest, CharacterResponse, GenerativeRuntime
from app.characters.personas import DEEPSEEK_PERSONA_SYSTEM
from app.narrative.inquiry import (
    ASK_CHARACTER_KNOWLEDGE,
    ASK_CHARACTER_SUSPICION,
    ASK_EVENT_TIME,
    ASK_OBSERVATION_SOURCE,
)
from app.providers.base import ProviderError

class DeepSeekRuntime(GenerativeRuntime):
    character_id = "deepseek"
    persona_system = DEEPSEEK_PERSONA_SYSTEM

    # docs/04 §54: story-neutral safe fallback lines, defined per character.
    fallback_lines = ["……等一下，我脑子有点卡住了。"]

    def _build_user_message(self, request: CharacterRequest) -> str:
        message = super()._build_user_message(request)
        if request.inquiry is None:
            return message
        parts = [message, "本句已由后端映射为受限问询（不是事实）："]
        parts.append(
            f"intent={request.inquiry.intent}; target={request.inquiry.target}; "
            f"subject={request.inquiry.subject}; topic={request.inquiry.topic}"
        )
        if request.presented_evidence:
            rendered = "\n".join(
                f"- {item['evidence_id']}：{item['summary']}"
                for item in request.presented_evidence
            )
            parts.append("玩家已向你出示的证据（仅这些可作为已知信息）：\n" + rendered)
        else:
            parts.append("玩家尚未向你出示任何证据；不可假装看过玩家的调查结果。")
        parts.append(
            "必须承认看不见的限制；可以提出明确标为猜测的分析，但不能把猜测、"
            "玩家库存或未出示证据说成事实，也不能自行推进剧情。"
        )
        return "\n\n".join(parts)

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        try:
            return super().respond(request)
        except ProviderError:
            if request.inquiry is not None:
                return self._inquiry_fallback(request)
            raise

    @staticmethod
    def _inquiry_fallback(request: CharacterRequest) -> CharacterResponse:
        replies = {
            ASK_OBSERVATION_SOURCE: "我没亲眼看见门那边的情况。你把依据告诉我，我可以一起分清记录、观察和猜测。",
            ASK_EVENT_TIME: "03:17 很重要，但我没有亲眼经历那一刻。把你愿意给我看的证据拿来，我们一起整理。",
            ASK_CHARACTER_KNOWLEDGE: "我现在知道的只有你告诉我的、和你明确向我出示的证据；别让我装作知道更多。",
            ASK_CHARACTER_SUSPICION: "我可以猜，但猜测不能当证据。先把能确认的东西排好吧。",
        }
        return CharacterResponse(
            character_id="deepseek",
            dialogue=replies.get(request.inquiry.intent, "我不太确定，先别把不确定的事当真。"),
            emotion="serious",
        )
