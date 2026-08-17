"""DeepSeek investigation-runtime tests (docs/03, docs/06 §2)."""

from __future__ import annotations

import json

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative.inquiry import ASK_EVENT_TIME, ASK_OBSERVATION_SOURCE, Inquiry
from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider, ProviderError


class _RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.user = ""

    def complete(self, *, system, user, max_tokens=256, response_format=None, thinking=None):
        self.user = user
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": "我会把能确认的和猜测分开。",
                "emotion": "serious",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


class _FailingProvider(LLMProvider):
    def complete(self, **kwargs):
        raise ProviderError("injected failure")


class _InquiryInterpreter:
    def interpret(self, state: NarrativeState, message: str) -> Inquiry:
        return Inquiry(ASK_EVENT_TIME, target="deepseek", topic="timestamp_0317")


class _RecordingRuntime(CharacterRuntime):
    character_id = "deepseek"

    def __init__(self) -> None:
        self.request: CharacterRequest | None = None

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.request = request
        return CharacterResponse(character_id="deepseek", dialogue="收到。")


def test_deepseek_receives_only_evidence_presented_to_her():
    provider = _RecordingProvider()
    runtime = DeepSeekRuntime(provider)
    request = CharacterRequest(
        character_id="deepseek",
        player_message="03:17 时发生了什么？",
        inquiry=Inquiry(ASK_EVENT_TIME, target="deepseek", topic="timestamp_0317"),
        presented_evidence=[
            {
                "evidence_id": "EV_NOTE_V03",
                "summary": "纸条压痕显示：03:17。",
            }
        ],
    )

    runtime.respond(request)

    assert "EV_NOTE_V03" in provider.user
    assert "纸条压痕显示" in provider.user
    assert "EV_ADMIN_LOG_0317" not in provider.user
    assert "CURRENT_SUBJECT_IS_PLAYER_V04" not in provider.user


def test_key_inquiry_provider_failure_has_blindness_safe_fallback():
    response = DeepSeekRuntime(_FailingProvider()).respond(
        CharacterRequest(
            character_id="deepseek",
            player_message="你亲眼看见门开了吗？",
            inquiry=Inquiry(ASK_OBSERVATION_SOURCE, target="deepseek", topic="door_open"),
        )
    )

    assert "没亲眼看见" in response.dialogue
    assert response.emotion == "serious"


def test_orchestrator_passes_inquiry_without_turning_it_into_state_change():
    runtime = _RecordingRuntime()
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": runtime},
        inquiry_interpreter=_InquiryInterpreter(),
    )

    result = orchestrator.handle_turn(None, "03:17 时发生了什么？")
    state = orchestrator._state.state_for(result.session_id)

    assert runtime.request is not None
    assert runtime.request.inquiry == Inquiry(
        ASK_EVENT_TIME, target="deepseek", topic="timestamp_0317"
    )
    assert state.completed_events == set()
    assert state.chapter1.acquired_evidence == set()
