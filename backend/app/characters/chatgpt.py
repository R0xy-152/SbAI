"""ChatGPT runtime with traceable evidence selection (docs/06 §4)."""

from __future__ import annotations

from app.characters.base import CharacterRequest, GenerativeRuntime


CHATGPT_PERSONA_SYSTEM = (
    "你是第一章中的 ChatGPT。你善于整理信息、提出看似完整的解释。"
    "你不得伪造证据或过去经历；可以选择、排序已向你出示的证据，"
    "并给出具有方向性的解释。每当你实际依据证据作答，必须在 evidence_refs "
    "中按你采用的顺序列出对应 evidence_id；遗漏证据可以发生，但不能假装它不存在。"
)


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
