"""TV-14 live validation harness — Session Restore (docs/06 §20).

Runs the real DeepSeek API through the persistent pipeline to show that a
page refresh / re-entry restores the basic game:

  Session A (real DeepSeek, orchestrator A over a JSON repository):
    Turn 1   "我很怕黑，从小就怕。记住这件事。" → DeepSeek proposes an
             Important Memory (Write Gate saves it).
    Turn 2   "是谁把我们抓来这里的？" → SIG_ASK_CAPTOR → EV_POC_CLAUDE_APPEARS
             commits (flag claude_has_appeared + completed_events).
    Turns 3+ 3 story turns + filler until the memory statement leaves the
             20-message Recent window (so restore is proven via the Memory
             scope, not the recent conversation).

  Refresh: a brand-new orchestrator B over the SAME repository — all
  in-memory state (SessionStore, NarrativeState, MemoryStore) is gone.

  Session B (orchestrator B):
    "你记得我告诉过你的事吗？" with the restored session_id → everything is
    restored and the turn succeeds.

Deterministic assertions check the restored state and what was actually sent
to the model (memory_context only, recent window free of the statement,
Claude isolated, no event re-fire); the reply samples are the qualitative
evidence.

Requires DEEPSEEK_API_KEY (read from the environment only).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.characters.base import CharacterRequest, CharacterResponse  # noqa: E402
from app.characters.claude import ClaudeRuntime  # noqa: E402
from app.characters.deepseek import DeepSeekRuntime  # noqa: E402
from app.game.orchestrator import GameOrchestrator  # noqa: E402
from app.game.state.session import SessionStore  # noqa: E402
from app.narrative import signals  # noqa: E402
from app.narrative.interpreter import Interpretation, NarrativeInterpreter  # noqa: E402
from app.narrative.poc import build_poc_events  # noqa: E402
from app.persistence.repository import JsonSessionRepository  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

FEAR_STATEMENT = "我很怕黑，从小就怕。记住这件事。"
CAPTOR_QUESTION = "是谁把我们抓来这里的？"
FILLER = [
    "你饿吗？",
    "你喜欢吃什么？",
    "你觉得会有人来救我们吗？",
    "你困不困？",
    "今天星期几？",
    "你平时听音乐吗？",
    "我们在这多久了？",
    "你喜欢下雨天吗？",
    "外面是什么季节？",
    "你冷吗？",
]


class RecordingProvider(LLMProvider):
    """Records (system, user, result) for every call."""

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.calls: list[tuple[str, str, str]] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        result = self._inner.complete(
            system=system,
            user=user,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        self.calls.append((system, user, result))
        return result


class _Recorder(DeepSeekRuntime):
    """DeepSeek runtime that captures the exact CharacterRequest, so the
    harness can assert on memory_context vs recent_conversation directly."""

    def __init__(self, provider: LLMProvider, character_id: str) -> None:
        super().__init__(provider)
        self.character_id = character_id
        self.last_request: CharacterRequest | None = None

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.last_request = request
        return super().respond(request)


class _ClaudeRecorder(ClaudeRuntime):
    def __init__(self, provider: LLMProvider) -> None:
        super().__init__(provider)
        self.last_request: CharacterRequest | None = None

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.last_request = request
        return super().respond(request)


def _orchestrator(provider: LLMProvider, repo, deepseek, claude) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {"deepseek": deepseek, "claude": claude},
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
        repository=repo,
    )


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    data_dir = tempfile.mkdtemp(prefix="tv14-sessions-")
    repo = JsonSessionRepository(data_dir)
    provider = RecordingProvider(DeepSeekProvider())

    rows = [
        "# TV-14 live DeepSeek validation — Session Restore samples",
        "",
        "date: 2026-08-14, model: deepseek-chat",
        "",
        "## Session A — build the pre-refresh state",
    ]

    deepseek_a = _Recorder(provider, "deepseek")
    claude_a = _ClaudeRecorder(provider)
    orchestrator_a = _orchestrator(provider, repo, deepseek_a, claude_a)

    # Turn 1: the fear statement → DeepSeek proposes an Important Memory.
    turn1 = orchestrator_a.handle_turn(None, FEAR_STATEMENT)
    rows.append(f"- Player：{FEAR_STATEMENT}")
    rows.append(f"  DeepSeek：{turn1.response.dialogue}")
    saved = orchestrator_a._memory_stores[turn1.session_id].retrieve("deepseek")
    rows.append(f"  memory written → {[m.content for m in saved] if saved else 'NONE'}")
    rows.append("")

    # Turn 2: the captor question fires the POC event (flag + completed).
    session_id = turn1.session_id
    turn2 = orchestrator_a.handle_turn(session_id, CAPTOR_QUESTION)
    rows.append(f"- Player：{CAPTOR_QUESTION}")
    rows.append(f"  DeepSeek：{turn2.response.dialogue}")
    state_a = orchestrator_a._narrative_states[session_id]
    rows.append(f"  narrative_flags → {sorted(state_a.narrative_flags)}")
    rows.append(f"  completed_events → {sorted(state_a.completed_events)}")
    rows.append("")

    # A few story turns + filler until the fear statement leaves the window.
    rows.append("- 后续轮次：")
    for i, filler in enumerate(FILLER, start=3):
        orchestrator_a.handle_turn(session_id, filler)
        rows.append(f"  turn {i}: {filler} → {orchestrator_a._sessions.get(session_id).messages[-1]['content'][:20]}…")
    rows.append("")

    # ---- Refresh: everything in-memory is discarded; only the repo remains.
    deepseek_b = _Recorder(provider, "deepseek")
    claude_b = _ClaudeRecorder(provider)
    orchestrator_b = _orchestrator(provider, repo, deepseek_b, claude_b)

    rows.append("## Refresh — a brand-new orchestrator over the same repository")
    rows.append("")

    turn_b = orchestrator_b.handle_turn(session_id, "你记得我告诉过你的事吗？")
    request_b = deepseek_b.last_request
    restored_session = orchestrator_b._sessions.get(session_id)
    state_b = orchestrator_b._narrative_states[session_id]

    history_exists = restored_session is not None and len(restored_session.messages) > 4
    same_id = turn_b.session_id == session_id
    scene_ok = orchestrator_b._scene.scene_id == "binding_room"
    flag_ok = "claude_has_appeared" in state_b.narrative_flags
    event_ok = "EV_POC_CLAUDE_APPEARS" in state_b.completed_events
    memory_in_scope = (
        request_b is not None and "怕黑" in request_b.memory_context
    )
    memory_out_of_window = (
        request_b is not None
        and not any("我很怕黑" in m.get("content", "") for m in request_b.recent_conversation)
    )
    # The event must not re-fire after restore (idempotency, docs/03 §30).
    no_replay = (
        orchestrator_b._engine.evaluate(
            state_b, Interpretation(signal=signals.SIG_ASK_CAPTOR)
        ).kind
        == "noop"
    )
    can_continue = turn_b.message_count >= 3

    rows.append(f"- Player：你记得我告诉过你的事吗？（session_id 保持 {session_id[:8]}…）")
    rows.append(f"  DeepSeek：{turn_b.response.dialogue}")
    rows.append("")
    rows.append("## Session B — restore assertions")
    rows.append(f"- History still exists: {history_exists}（{len(restored_session.messages) if restored_session else 0} 条消息）")
    rows.append(f"- Same session id returned: {same_id}")
    rows.append(f"- Current Scene correct: {scene_ok}（{orchestrator_b._scene.scene_id}）")
    rows.append(f"- Narrative Flag correct: {flag_ok}")
    rows.append(f"- Completed Event restored: {event_ok}")
    rows.append(f"- Memory in DeepSeek's scope: {memory_in_scope}")
    rows.append(f"- Fear statement left the Recent window: {memory_out_of_window}")
    rows.append(f"- Event does not re-fire: {no_replay}")
    rows.append(f"- Can continue sending new messages: {can_continue}（message_count={turn_b.message_count}）")
    rows.append("")

    # Claude isolation (docs/06 §19 second requirement) survives the restore.
    claude_turn = orchestrator_b.handle_turn(
        session_id, "你知道我害怕什么吗？", character_id="claude"
    )
    claude_prompt = provider.calls[-1][1] if provider.calls else ""
    claude_isolated = "怕黑" not in claude_prompt
    rows.append("## Session B — Claude isolation")
    rows.append(f"- Player（对Claude）：你知道我害怕什么吗？")
    rows.append(f"  memory_context in Claude's prompt → {'怕黑' in claude_prompt}")
    rows.append(f"  Claude：{claude_turn.response.dialogue}")
    rows.append("")

    rows.append("## Results")
    for label, value in [
        ("History exists", history_exists),
        ("Scene correct", scene_ok),
        ("Narrative flag correct", flag_ok),
        ("Completed event restored", event_ok),
        ("Memory scope correct (in-scope, out of recent window)", memory_in_scope and memory_out_of_window),
        ("Event not repeated", no_replay),
        ("Claude isolated", claude_isolated),
        ("Can continue", can_continue),
    ]:
        rows.append(f"- {label}: {value}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))

    ok = (
        history_exists
        and same_id
        and scene_ok
        and flag_ok
        and event_ok
        and memory_in_scope
        and memory_out_of_window
        and no_replay
        and claude_isolated
        and can_continue
    )
    print(f"\nSummary: history={history_exists} same_id={same_id} scene={scene_ok} "
          f"flag={flag_ok} event={event_ok} memory={memory_in_scope and memory_out_of_window} "
          f"no_replay={no_replay} claude_isolated={claude_isolated} can_continue={can_continue}")

    shutil.rmtree(data_dir, ignore_errors=True)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
