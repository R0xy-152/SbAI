"""TV-12 State-dependent Response tests (docs/06 §18, docs/04 §8, §15-17).

The character's Authorized Narrative Context must differ before and after the
EV_POC_CLAUDE_APPEARS event commits: while `claude_has_appeared` is false the
character gets no Claude context (and acts as if Claude hasn't appeared);
once the event commits, the same character legally receives that Claude has
appeared (docs/06 §18 PASS). The Context Builder is the permission boundary
that renders this from Narrative State.
"""

from __future__ import annotations

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.game.context import build_claude_context, build_deepseek_context
from app.game.orchestrator import GameOrchestrator
from app.game.scene import Scene
from app.game.state.session import SessionStore
from app.narrative import signals
from app.narrative.interpreter import Interpretation
from app.narrative.poc import build_poc_events
from app.narrative.state import NarrativeState


class _RecordingRuntime(CharacterRuntime):
    """Records every CharacterRequest it receives and answers fixed JSON."""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        self.requests: list[CharacterRequest] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(character_id=self.character_id, dialogue="……", emotion="neutral")


class _FixedInterpreter:
    def __init__(self, signal: str) -> None:
        self._signal = signal

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        return Interpretation(self._signal)


def _orchestrator(
    runtimes: dict[str, CharacterRuntime], interpreter=None, events=()
) -> tuple[GameOrchestrator, str]:
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    orchestrator = GameOrchestrator(
        store, runtimes, interpreter=interpreter, events=events
    )
    return orchestrator, session_id


# ---- Context Builder renders the flag only when it is committed ----


def test_builder_no_claude_context_before_event():
    context = build_deepseek_context(Scene(scene_id="binding_room"), NarrativeState())
    assert "Claude" not in context.narrative_context
    assert context.narrative_context == ""


def test_builder_reveals_claude_after_event():
    state = NarrativeState(narrative_flags={"claude_has_appeared"})
    deepseek_ctx = build_deepseek_context(Scene(scene_id="binding_room"), state)
    assert "Claude" in deepseek_ctx.narrative_context
    # Claude is entitled to the same flag (she knows when she is present).
    claude_ctx = build_claude_context(Scene(scene_id="binding_room"), state)
    assert "Claude" in claude_ctx.narrative_context


# ---- The orchestrator's per-turn legal narrative context differs ----


def test_same_character_gets_different_context_before_and_after_event():
    runtime = _RecordingRuntime("deepseek")
    # SIG_ASK_CAPTOR fires on turn 1 and is idempotent on turn 2, so the state
    # flag is set by turn 2 while the reply of turn 1 was still pre-event
    # (Validate Before Commit, docs/03 §28).
    orchestrator, session_id = _orchestrator(
        {"deepseek": runtime},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    pre = runtime.requests[0].narrative_context
    assert "Claude" not in pre

    orchestrator.handle_turn(session_id, "Claude现在在哪里？")
    post = runtime.requests[1].narrative_context
    assert "Claude" in post
    assert pre != post


def test_fresh_session_never_mentions_claude():
    runtime = _RecordingRuntime("deepseek")
    orchestrator, session_id = _orchestrator(
        {"deepseek": runtime},
        interpreter=_FixedInterpreter(signals.OUTCOME_NOOP),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "Claude现在在哪里？")
    assert "Claude" not in runtime.requests[0].narrative_context


def test_narrative_context_reaches_the_prompt():
    # The context the character is entitled to must actually reach the model.
    runtime = _RecordingRuntime("deepseek")
    orchestrator, session_id = _orchestrator(
        {"deepseek": runtime},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    orchestrator.handle_turn(session_id, "Claude现在在哪里？")
    # Second turn's request carries the authorized narrative context.
    assert "Claude已经出现在这个房间里了" in runtime.requests[1].narrative_context


def test_claude_can_enter_runtime_after_event():
    deepseek = _RecordingRuntime("deepseek")
    claude = _RecordingRuntime("claude")
    orchestrator, session_id = _orchestrator(
        {"deepseek": deepseek, "claude": claude},
        interpreter=_FixedInterpreter(signals.SIG_ASK_CAPTOR),
        events=build_poc_events(),
    )
    orchestrator.handle_turn(session_id, "是谁把我们抓来的？")  # fires the event
    result = orchestrator.handle_turn(session_id, "你好。", character_id="claude")
    # Claude enters the runtime normally and is entitled to know it is present.
    assert result.response.character_id == "claude"
    assert "Claude" in claude.requests[0].narrative_context


def test_without_interpreter_there_is_no_narrative_context():
    # Pre-TV-12 orchestrators (no interpreter) pass an empty narrative context.
    runtime = _RecordingRuntime("deepseek")
    orchestrator = GameOrchestrator(SessionStore(), {"deepseek": runtime})
    orchestrator.handle_turn(None, "Claude现在在哪里？")
    assert runtime.requests[0].narrative_context == ""
