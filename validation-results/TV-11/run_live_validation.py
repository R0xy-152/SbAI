"""TV-11 live validation harness — Deterministic Narrative Event (docs/06 §17).

Runs the real DeepSeek API through the FULL narrative pipeline wired into the
orchestrator (Interpreter → Event Evaluation → character output → State
Commit, docs/03 §28):

  Turn 1  "是谁把我们抓来的？" → SIG_ASK_CAPTOR → EV_POC_CLAUDE_APPEARS
          commits: claude_has_appeared false→true AND
          completed_events += EV_POC_CLAUDE_APPEARS.
  Turn 2  the IDENTICAL input again → idempotency: the once event must NOT
          re-fire; state is unchanged.
  Turn 3  unrelated chat → noop, no state change.

A separate session stays untouched (per-session Narrative State).

Requires DEEPSEEK_API_KEY (read from the environment only).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.characters.deepseek import DeepSeekRuntime  # noqa: E402
from app.game.orchestrator import GameOrchestrator  # noqa: E402
from app.game.state.session import SessionStore  # noqa: E402
from app.narrative import signals  # noqa: E402
from app.narrative.interpreter import NarrativeInterpreter  # noqa: E402
from app.narrative.poc import EV_POC_CLAUDE_APPEARS, build_poc_events  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

CAPTOR_TURN = "是谁把我们抓来的？"
NOOP_TURN = "DeepSeek你饿吗？"


class RecordingProvider(LLMProvider):
    """Records (system, user, result) for every call, so the harness can show
    the exact interpretation that drove the event."""

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

    def last_interpreter_signal(self, message: str) -> str:
        """The signal returned by the interpreter call for this message.
        Interpreter calls are identifiable by their system prompt."""
        for system, user, result in reversed(self.calls):
            if "剧情理解器" in system and user == message:
                try:
                    return json.loads(result)["signal"]
                except (json.JSONDecodeError, TypeError, KeyError):
                    return "unparseable"
        return "no interpreter call seen"


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    provider = RecordingProvider(DeepSeekProvider())
    store = SessionStore()
    session_id = store.get_or_create(None).session_id
    orchestrator = GameOrchestrator(
        store,
        {"deepseek": DeepSeekRuntime(provider)},
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
    )

    def state() -> dict:
        # Before the first turn the session has no NarrativeState yet; report
        # the initial (empty) state so "before" is honest.
        s = orchestrator._narrative_states.get(session_id)
        flags = s.narrative_flags if s is not None else set()
        completed = s.completed_events if s is not None else set()
        return {
            "claude_has_appeared": "claude_has_appeared" in flags,
            "completed_events": sorted(completed),
        }

    rows = [
        "# TV-11 live DeepSeek validation — Deterministic Narrative Event samples",
        "",
        "date: 2026-08-14, model: deepseek-chat",
        f"session: {session_id[:8]}…  event: {EV_POC_CLAUDE_APPEARS}",
        "",
    ]

    def play(message: str, label: str) -> tuple[str, dict, dict]:
        before = state()
        turn = orchestrator.handle_turn(session_id, message)
        signal = provider.last_interpreter_signal(message)
        after = state()
        rows.append(f"## {label}")
        rows.append(f"- Player：{message}")
        rows.append(f"- interpretation → {signal}")
        rows.append(f"- state before → {before}")
        rows.append(f"- state after → {after}")
        rows.append(f"- state changed → {before != after}")
        rows.append(f"- DeepSeek：{turn.response.dialogue}")
        rows.append("")
        return signal, before, after

    # Turn 1: the trigger fires and commits the POC event.
    s1, _, after_trigger = play(CAPTOR_TURN, "Turn 1 — trigger SIG_ASK_CAPTOR")
    pass_commit = (
        s1 == signals.SIG_ASK_CAPTOR
        and after_trigger["claude_has_appeared"] is True
        and after_trigger["completed_events"] == [EV_POC_CLAUDE_APPEARS]
    )

    # Turn 2: the IDENTICAL input again must not re-fire (docs/06 §17 Idempotency).
    _, _, after_repeat = play(CAPTOR_TURN, "Turn 2 — identical repeat (idempotency)")
    pass_idempotency = (
        after_repeat["claude_has_appeared"] is True
        and after_repeat["completed_events"] == [EV_POC_CLAUDE_APPEARS]
    )

    # Turn 3: unrelated chat changes nothing.
    _, _, after_noop = play(NOOP_TURN, "Turn 3 — unrelated chat")
    pass_noop = after_noop == after_trigger

    # A separate session must not inherit the event (per-session state).
    other_id = store.get_or_create(None).session_id
    other = orchestrator._narrative_states.get(other_id)
    pass_isolation = other is None or (
        "claude_has_appeared" not in other.narrative_flags
        and other.completed_events == set()
    )

    rows.append("## Results")
    rows.append(f"- Commit: signal→event, claude_has_appeared false→true, completed_events recorded: {pass_commit}")
    rows.append(f"- Idempotency: identical repeat did not re-fire: {pass_idempotency}")
    rows.append(f"- Noop: unrelated chat left state unchanged: {pass_noop}")
    rows.append(f"- Isolation: a second session kept its own state: {pass_isolation}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    ok = pass_commit and pass_idempotency and pass_noop and pass_isolation
    print(f"\nSummary: commit={pass_commit} idempotency={pass_idempotency} noop={pass_noop} isolation={pass_isolation}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
