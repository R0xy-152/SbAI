"""Claude Truth / Disclosure runtime tests (docs/03, docs/06)."""

import json

from app.characters.base import CharacterRequest
from app.characters.claude import ClaudeRuntime
from app.characters.claude_truth import CLAUDE_TRUTH_CONTRACT
from app.game.context import build_claude_context
from app.game.scene import Scene
from app.narrative.inquiry import ASK_CHARACTER_KNOWLEDGE, ASK_OBSERVATION_SOURCE, Inquiry
from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider, ProviderError


class _FailingProvider(LLMProvider):
    def complete(self, **kwargs):
        raise ProviderError("injected failure")


class _RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.user = ""

    def complete(self, *, system, user, max_tokens=256, response_format=None, thinking=None):
        self.user = user
        return json.dumps(
            {
                "character_id": "claude",
                "dialogue": "我只会讨论这项证据直接能说明的内容。",
                "emotion": "serious",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


def test_claude_never_claims_to_have_visually_seen_deepseek():
    response = ClaudeRuntime(_FailingProvider()).respond(
        CharacterRequest(
            character_id="claude",
            player_message="你亲眼看到 DeepSeek 开门了吗？",
            inquiry=Inquiry(
                ASK_OBSERVATION_SOURCE,
                target="claude",
                subject="deepseek",
                topic="door_open",
            ),
        )
    )

    assert response.dialogue == "没有。我看到的是记录，不是她本人。"
    assert "CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK" in CLAUDE_TRUTH_CONTRACT.known_facts


def test_claude_public_claims_are_separate_and_deterministic():
    runtime = ClaudeRuntime(_FailingProvider())
    attribution = runtime.respond(
        CharacterRequest(
            character_id="claude",
            player_message="是谁打开 C-02 的门？",
            inquiry=Inquiry(ASK_CHARACTER_KNOWLEDGE, target="claude", topic="door_open"),
        )
    )
    source = runtime.respond(
        CharacterRequest(
            character_id="claude",
            player_message="你亲眼看见了吗？",
            inquiry=Inquiry(ASK_OBSERVATION_SOURCE, target="claude", topic="door_open"),
        )
    )

    assert attribution.claim_refs == ["CL_CLAUDE_01"]
    assert source.claim_refs == ["CL_CLAUDE_02"]


def test_claude_recovery_disclosure_requires_its_authorized_context_flag():
    state = NarrativeState()
    state.narrative_flags.add("claude_recovery_disclosure_open")
    response = ClaudeRuntime(_FailingProvider()).respond(
        CharacterRequest(
            character_id="claude",
            player_message="你访问过 Recovery Interface 吗？",
            inquiry=Inquiry(ASK_CHARACTER_KNOWLEDGE, target="claude", topic="evidence"),
            narrative_context=build_claude_context(
                Scene(scene_id="ROOM_A", wall_code=""), state
            ).narrative_context,
        )
    )

    assert response.claim_refs == ["CL_CLAUDE_05"]


def test_claude_prompt_uses_contract_and_only_presented_evidence():
    provider = _RecordingProvider()
    runtime = ClaudeRuntime(provider)
    runtime.respond(
        CharacterRequest(
            character_id="claude",
            player_message="说说这项证据。",
            inquiry=Inquiry("UNHANDLED", target="claude"),
            presented_evidence=[
                {"evidence_id": "EV_NOTE_V03", "summary": "纸条压痕显示：03:17。"}
            ],
        )
    )

    assert "CLAUDE_HAS_PREVIOUS_LOOP_KNOWLEDGE" in provider.user
    assert "CURRENT_ADMIN_HOLDER" in provider.user
    assert "EV_NOTE_V03" in provider.user
    assert "EV_ADMIN_LOG_0317" not in provider.user
