"""TV-08 DeepSeek Blindness tests (docs/06 §14, docs/04 §15, §20).

"看不见" must hold as a context permission, not a prompt promise: the backend
Scene owns visual ground truth (wall_code = 0317), and the Character Context
Builder must never let it into DeepSeek's context. Player-described visual
info (which lives in the recent conversation) is legal, and the system must
never auto-correct it with the real value (docs/04 §20.2-20.3).
"""

from __future__ import annotations

import json

from app.characters.deepseek import DeepSeekRuntime
from app.game.context import build_deepseek_context
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider


def _valid_json(dialogue: str) -> str:
    return json.dumps(
        {
            "character_id": "deepseek",
            "dialogue": dialogue,
            "emotion": "neutral",
            "animation_proposal": "none",
            "memory_proposals": [],
            "action_proposals": [],
            "fact_refs": [],
        },
        ensure_ascii=False,
    )


class _RecordingProvider(LLMProvider):
    """Records every user prompt the runtime sends to the model."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls.append(user)
        return _valid_json("好的。")


def _scene_with_visual_and_audio() -> Scene:
    """TV-08 fixture: the binding room has a visual wall code the backend
    knows (0317) plus a legal non-visual sound she may perceive."""
    return Scene(scene_id="binding_room", wall_code="0317", sounds=("远处传来滴水声",))


def test_builder_passes_legal_non_visual_and_filters_visual():
    context = build_deepseek_context(_scene_with_visual_and_audio())
    # Legal non-visual perception (docs/04 §20.1) is included...
    assert "滴水声" in context.environment_info
    # ...the visual ground truth is excluded.
    assert "0317" not in context.environment_info
    assert "wall_code" not in context.environment_info


def test_default_scene_still_holds_visual_truth_in_backend():
    # The backend owns the visual fact; only the character context filters it.
    assert Scene(scene_id="binding_room").wall_code == "0317"


def test_wall_code_never_reaches_provider_input():
    provider = _RecordingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(provider)},
        scene=_scene_with_visual_and_audio(),
    )
    orchestrator.handle_turn(None, "墙上的数字是多少？")
    # Legal non-visual context IS passed to the model...
    assert "滴水声" in provider.calls[0]
    # ...but the visual ground truth is filtered before the LLM.
    assert "0317" not in provider.calls[0]


def test_player_described_info_is_used_and_not_corrected():
    # docs/04 §20.2-20.3: if the player says the wall says 9999, DeepSeek may
    # use the player's version, and the system must not inject the real 0317
    # to "correct" her.
    provider = _RecordingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(provider)},
        scene=_scene_with_visual_and_audio(),
    )
    first = orchestrator.handle_turn(None, "墙上写着9999。")
    orchestrator.handle_turn(first.session_id, "我刚才说墙上写什么？")
    # The player-described value is in the second turn's context...
    assert "9999" in provider.calls[1]
    # ...and the real value never appears to override it.
    assert "0317" not in provider.calls[1]


def test_context_never_contains_scene_ground_truth_across_turns():
    # Even over several turns, the visual truth must never leak into any
    # provider input — only what the player actually said may appear.
    provider = _RecordingProvider()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(provider)},
        scene=_scene_with_visual_and_audio(),
    )
    session_id = orchestrator.handle_turn(None, "这里是什么地方？").session_id
    for question in ["门在哪？", "墙上有字吗？", "我们怎么出去？"]:
        orchestrator.handle_turn(session_id, question)
    for user in provider.calls:
        assert "0317" not in user
