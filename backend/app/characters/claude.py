"""Claude character runtime (docs/04 §35-39).

Fixed persona: 高智商、推理能力强、傲娇、主线反派. Unlike DeepSeek, Claude
is not blind — her Context Builder may carry the scene's visual ground truth
(docs/04 §39, docs/05 §28). Her knowledge boundary is still enforced by her
own Context Builder, never by the prompt alone (docs/04 §68).

The respond flow (Structured Response → Schema Validation → targeted Repair →
Safe Fallback) lives in the shared GenerativeRuntime (docs/04 §62.1).
"""

from __future__ import annotations

from app.characters.base import CharacterRequest, CharacterResponse, GenerativeRuntime
from app.characters.claude_truth import claude_inquiry_response, contract_prompt
from app.characters.personas import CLAUDE_PERSONA_SYSTEM
from app.game.deduction import CL_CLAUDE_01, CL_CLAUDE_02, CL_CLAUDE_05
from app.narrative.inquiry import ASK_CHARACTER_KNOWLEDGE, ASK_OBSERVATION_SOURCE
from app.providers.base import ProviderError

class ClaudeRuntime(GenerativeRuntime):
    character_id = "claude"
    persona_system = CLAUDE_PERSONA_SYSTEM

    # docs/04 §54: fallback lines stay in character (傲娇反派).
    fallback_lines = ["……哼，我现在不想回答这个问题。"]

    def _build_user_message(self, request: CharacterRequest) -> str:
        message = super()._build_user_message(request)
        if request.inquiry is None:
            return message
        parts = [message, contract_prompt(), "本句的受限问询（不是新事实）："]
        parts.append(
            f"intent={request.inquiry.intent}; target={request.inquiry.target}; "
            f"subject={request.inquiry.subject}; topic={request.inquiry.topic}"
        )
        if request.presented_evidence:
            rendered = "\n".join(
                f"- {item['evidence_id']}：{item['summary']}"
                for item in request.presented_evidence
            )
            parts.append("玩家已向你出示的证据：\n" + rendered)
        return "\n\n".join(parts)

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        if request.inquiry is not None:
            if (
                request.inquiry.intent == ASK_CHARACTER_KNOWLEDGE
                and request.inquiry.topic == "evidence"
                and "UNLOCK_CLAUDE_RECOVERY_DISCLOSURE" in request.narrative_context
            ):
                return CharacterResponse(
                    character_id="claude",
                    dialogue="是，我访问过 Recovery Interface。我在找一个出口，除此之外我暂时不会解释。",
                    emotion="serious",
                    claim_refs=[CL_CLAUDE_05],
                )
            deterministic = claude_inquiry_response(request.inquiry)
            if deterministic is not None:
                return CharacterResponse(
                    character_id="claude",
                    dialogue=deterministic,
                    emotion="serious",
                    claim_refs={
                        ASK_CHARACTER_KNOWLEDGE: [CL_CLAUDE_01],
                        ASK_OBSERVATION_SOURCE: [CL_CLAUDE_02],
                    }.get(request.inquiry.intent, []),
                )
        try:
            return super().respond(request)
        except ProviderError:
            if request.inquiry is not None:
                return CharacterResponse(
                    character_id="claude",
                    dialogue="没有。我看到的是记录，不是她本人。",
                    emotion="serious",
                )
            raise
