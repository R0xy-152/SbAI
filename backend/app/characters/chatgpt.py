"""ChatGPT runtime with traceable evidence selection (docs/06 §4)."""

from __future__ import annotations

from app.characters.base import CharacterRequest, GenerativeRuntime
from app.characters.personas import CHATGPT_PERSONA_SYSTEM


class ChatGPTRuntime(GenerativeRuntime):
    character_id = "chatgpt"
    persona_system = CHATGPT_PERSONA_SYSTEM
    fallback_lines = ["我暂时无法整理出可靠的结论。先把已经确认的证据放在一起。"]

    def _build_user_message(self, request: CharacterRequest) -> str:
        message = super()._build_user_message(request)
        if not request.presented_evidence:
            return message + "\n\n目前没有向你出示的证据；evidence_refs 必须为空。"
        rendered = "\n".join(
            f"- {item['evidence_id']}：{item['summary']}"
            for item in request.presented_evidence
        )
        return (
            message
            + "\n\n玩家已向你出示的证据（只能引用这些 ID）：\n"
            + rendered
            + "\n如选择证据，evidence_refs 必须记录你实际采用的 ID 与顺序。"
        )
