"""Doubao runtime: observations and interpretations stay distinct (docs/06 §5)."""

from __future__ import annotations

from app.characters.base import CharacterRequest, CharacterResponse, GenerativeRuntime
from app.game.deduction import CL_DB_01
from app.narrative.inquiry import ASK_CHARACTER_SUSPICION


DOUBAO_PERSONA_SYSTEM = (
    "你是第一章中的豆包。你诚实地报告自己依据的观察，但可能把观察解释错。"
    "绝不伪造观察或证据。若依据已出示证据作答，observed_fact_refs 只能列出其中事实 ID；"
    "interpretation 单独写你的理解，可为空，且绝不能覆盖或改写观察。"
)


class DoubaoRuntime(GenerativeRuntime):
    character_id = "doubao"
    persona_system = DOUBAO_PERSONA_SYSTEM
    fallback_lines = ["我先把我实际看到的部分记下来，解释可能还不够准。"]

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        if (
            request.inquiry is not None
            and request.inquiry.intent == ASK_CHARACTER_SUSPICION
            and request.inquiry.subject == "chatgpt"
        ):
            return CharacterResponse(
                character_id="doubao",
                dialogue="GPT 早就在这里了呀？我记得很早就看到和她有关的东西。",
                emotion="serious",
                claim_refs=[CL_DB_01],
            )
        return super().respond(request)

    def _build_user_message(self, request: CharacterRequest) -> str:
        message = super()._build_user_message(request)
        if not request.presented_evidence:
            return message + "\n\n没有向你出示证据：observed_fact_refs 必须为空。"
        facts = "\n".join(
            f"- {fact_id}（来自 {item['evidence_id']}）"
            for item in request.presented_evidence
            for fact_id in item["facts"]
        )
        return (
            message
            + "\n\n你可报告的观察事实（只能选择这些 ID）：\n"
            + facts
            + "\n观察和 interpretation 必须分开。"
        )
