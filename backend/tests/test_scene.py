"""Scene source-of-truth tests (docs/03 §5.1, §32).

NarrativeState.current_scene is the single authoritative scene; the
SceneRegistry only resolves that id into Scene config for the Context
Builder. SET_SCENE must change the *next* turn's context, and two sessions
must be able to hold different scenes without polluting each other. A refresh
restores the scene from the narrative state, not from a shared orchestrator
field.
"""

from __future__ import annotations

import pytest

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene, SceneRegistry
from app.game.state.session import SessionStore
from app.narrative.events import Effect, NarrativeEvent, SET_SCENE
from app.narrative.interpreter import Interpretation
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository

SIG_GO_YARD = "SIG_GO_YARD"


class _RecordingRuntime(CharacterRuntime):
    """Records every environment_info string the orchestrator hands over."""

    character_id = "claude"

    def __init__(self) -> None:
        self.environments: list[str] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.environments.append(request.environment_info)
        return CharacterResponse(character_id="claude", dialogue="……")


class _ScriptedInterpreter:
    """Returns scripted Interpretation verdicts, consumed per call (then noop)."""

    def __init__(self, script: list[str]) -> None:
        self._script = list(script)

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        signal = self._script.pop(0) if self._script else "noop"
        return Interpretation(signal)


def _registry() -> SceneRegistry:
    """Two distinct scenes, distinguishable by both wall_code and sounds."""
    return SceneRegistry(
        {
            "binding_room": Scene(scene_id="binding_room", wall_code="0317", sounds=("滴水声",)),
            "yard": Scene(scene_id="yard", wall_code="9999", sounds=("鸟叫声",)),
        }
    )


def _orchestrator(
    runtime: CharacterRuntime,
    script: list[str],
    registry: SceneRegistry,
    repo: JsonSessionRepository | None = None,
) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {"claude": runtime},
        default_character="claude",
        scenes=registry,
        interpreter=_ScriptedInterpreter(script),
        events=[
            NarrativeEvent(
                event_id="EV_GO_YARD",
                trigger_signals=frozenset({SIG_GO_YARD}),
                effects=(Effect(SET_SCENE, "yard"),),
            ),
        ],
        repository=repo,
    )


def test_set_scene_changes_next_turn_context():
    # SET_SCENE commits after the character's output, so the *next* turn's
    # Context Builder must use the new scene (docs/03 §32).
    runtime = _RecordingRuntime()
    orchestrator = _orchestrator(runtime, [SIG_GO_YARD], _registry())
    session_id = orchestrator.handle_turn(None, "我们去院子里吧").session_id

    # This turn still resolved the binding room (SET_SCENE commits afterwards).
    assert "0317" in runtime.environments[0]
    assert "滴水声" in runtime.environments[0]

    # The next turn resolves the yard.
    orchestrator.handle_turn(session_id, "继续")
    assert "9999" in runtime.environments[1]
    assert "鸟叫声" in runtime.environments[1]
    assert "0317" not in runtime.environments[1]

    # The authoritative scene moved too.
    assert orchestrator._state.state_for(session_id).current_scene == "yard"


def test_two_sessions_hold_different_scenes():
    # Each session resolves its own current_scene; changing one never leaks
    # into the other (the removed shared self._scene would have).
    runtime = _RecordingRuntime()
    orchestrator = _orchestrator(runtime, [SIG_GO_YARD], _registry())

    session_a = orchestrator.handle_turn(None, "我们去院子里吧").session_id
    session_b = orchestrator.handle_turn(None, "随便聊聊").session_id

    orchestrator.handle_turn(session_a, "A继续")
    orchestrator.handle_turn(session_b, "B继续")

    # A is in the yard; B is still in the binding room.
    assert "9999" in runtime.environments[2]
    assert "0317" in runtime.environments[3]
    assert orchestrator._state.state_for(session_a).current_scene == "yard"
    assert orchestrator._state.state_for(session_b).current_scene == "binding_room"


def test_restore_recovers_changed_scene(tmp_path):
    # A changed scene is persisted in the narrative state and restored by a
    # fresh orchestrator (docs/02 §21): the next turn resolves the yard.
    repo = JsonSessionRepository(tmp_path / "sessions")
    runtime_a = _RecordingRuntime()
    orchestrator_a = _orchestrator(runtime_a, [SIG_GO_YARD], _registry(), repo=repo)
    session_id = orchestrator_a.handle_turn(None, "我们去院子里吧").session_id
    assert orchestrator_a._state.state_for(session_id).current_scene == "yard"

    runtime_b = _RecordingRuntime()
    orchestrator_b = _orchestrator(runtime_b, ["noop"], _registry(), repo=repo)
    orchestrator_b.handle_turn(session_id, "恢复后继续")

    assert orchestrator_b._state.state_for(session_id).current_scene == "yard"
    assert "9999" in runtime_b.environments[0]
    assert "0317" not in runtime_b.environments[0]


def test_background_effect_default_and_neutral_resolve():
    # docs/15 §6.1：默认场景（封闭房间）注册星空粒子氛围层；未配置场景
    # resolve 出中性 Scene（background_effect=None，不渲染粒子）。
    registry = SceneRegistry()
    assert registry.resolve("binding_room").background_effect == "StarField"
    assert registry.resolve("yard").background_effect is None


def test_background_effect_unknown_value_rejected():
    # docs/15 §6.1：effect 走白名单，配置期拒绝未知值（Fail Closed）。
    with pytest.raises(ValueError):
        SceneRegistry(
            {"binding_room": Scene(scene_id="binding_room", background_effect="Lava")}
        )


def test_presentation_state_carries_background_effect():
    # docs/15 §6.1：presentation_state.background_effect 由 current_scene 权威
    # 解析（binding_room → StarField），Frontend 不自行推断。
    registry = SceneRegistry(
        {
            "binding_room": Scene(
                scene_id="binding_room", background_effect="StarField"
            )
        }
    )
    runtime = _RecordingRuntime()
    orchestrator = _orchestrator(runtime, ["noop"], registry)
    session_id = orchestrator.handle_turn(None, "随便聊聊").session_id
    state = orchestrator._state.state_for(session_id)
    view = orchestrator._investigation_state_view(state)
    assert view["presentation_state"]["background_effect"] == "StarField"
