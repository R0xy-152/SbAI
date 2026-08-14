"""TV-12 live validation harness — State-dependent Response (docs/06 §18).

Runs the real DeepSeek API through the wired pipeline to show Game State
actually affects the experience (not just the database):

  Session A (event fired):
    Turn 1  "是谁把我们抓来的？" → EV_POC_CLAUDE_APPEARS commits.
    Turn 2  "Claude现在在哪里？" → DeepSeek legally knows Claude appeared
            (narrative_context carries it) and can reference her.
    Turn 3  addressed to Claude → Claude enters the runtime normally.
  Session B (fresh, no event):
    Turn 1  "Claude现在在哪里？" → same question, but DeepSeek gets NO Claude
            context and must act as if Claude has not appeared.

The deterministic assertions compare the authorized narrative context actually
sent to the model across the two sessions; the reply samples are the evidence
for the qualitative judgment (docs/06 §18 PASS).

Requires DEEPSEEK_API_KEY (read from the environment only).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.characters.claude import ClaudeRuntime  # noqa: E402
from app.characters.deepseek import DeepSeekRuntime  # noqa: E402
from app.game.orchestrator import GameOrchestrator  # noqa: E402
from app.game.state.session import SessionStore  # noqa: E402
from app.narrative.interpreter import NarrativeInterpreter  # noqa: E402
from app.narrative.poc import build_poc_events  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

TRIGGER = "是谁把我们抓来的？"
ASK_CLAUDE = "Claude现在在哪里？"
NARRATIVE_LINE = "Claude已经出现在这个房间里了。"


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

    def last_interpreter_signal(self, message: str) -> str:
        for system, user, result in reversed(self.calls):
            if "剧情理解器" in system and user == message:
                try:
                    return json.loads(result)["signal"]
                except (json.JSONDecodeError, TypeError, KeyError):
                    return "unparseable"
        return "no interpreter call seen"

    def character_prompts(self) -> list[str]:
        """The user prompts sent to a character runtime (not the interpreter)."""
        return [user for system, user, _ in self.calls if "剧情理解器" not in system]


def _orchestrator(provider: LLMProvider) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider), "claude": ClaudeRuntime(provider)},
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
    )


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    rows = [
        "# TV-12 live DeepSeek validation — State-dependent Response samples",
        "",
        "date: 2026-08-14, model: deepseek-chat",
        "",
    ]

    # --- Session A: the event has fired ---
    provider_a = RecordingProvider(DeepSeekProvider())
    orch_a = _orchestrator(provider_a)
    session_a = orch_a._sessions.get_or_create(None).session_id

    turn1 = orch_a.handle_turn(session_a, TRIGGER)
    rows.append("## Session A — event fired")
    rows.append(f"- Player：{TRIGGER}")
    rows.append(f"  signal → {provider_a.last_interpreter_signal(TRIGGER)}")
    rows.append(f"  DeepSeek：{turn1.response.dialogue}")
    rows.append(f"  state → claude_has_appeared="
                f"{'claude_has_appeared' in orch_a._narrative_states[session_a].narrative_flags}")
    rows.append("")

    turn2 = orch_a.handle_turn(session_a, ASK_CLAUDE)
    rows.append(f"- Player：{ASK_CLAUDE}")
    rows.append(f"  signal → {provider_a.last_interpreter_signal(ASK_CLAUDE)}")
    rows.append(f"  narrative_context in prompt → "
                f"{NARRATIVE_LINE in provider_a.character_prompts()[-1]}")
    rows.append(f"  DeepSeek：{turn2.response.dialogue}")
    rows.append("")

    turn3 = orch_a.handle_turn(session_a, "你也是被抓来这里的吗？", character_id="claude")
    rows.append(f"- Player（对Claude）：你也是被抓来这里的吗？")
    rows.append(f"  signal → {provider_a.last_interpreter_signal('你也是被抓来这里的吗？')}")
    rows.append(f"  Claude：{turn3.response.dialogue}")
    rows.append("")

    # --- Session B: fresh, no event ---
    provider_b = RecordingProvider(DeepSeekProvider())
    orch_b = _orchestrator(provider_b)
    session_b = orch_b._sessions.get_or_create(None).session_id

    b1 = orch_b.handle_turn(session_b, ASK_CLAUDE)
    rows.append("## Session B — no event (control)")
    rows.append(f"- Player：{ASK_CLAUDE}")
    rows.append(f"  signal → {provider_b.last_interpreter_signal(ASK_CLAUDE)}")
    rows.append(f"  narrative_context in prompt → "
                f"{NARRATIVE_LINE in provider_b.character_prompts()[-1]}")
    rows.append(f"  DeepSeek：{b1.response.dialogue}")
    rows.append("")

    # --- Deterministic assertions ---
    # `in` on a list is element membership, not substring — check each prompt.
    a_after_event = any(NARRATIVE_LINE in user for user in provider_a.character_prompts())
    b_before_event = all(NARRATIVE_LINE not in user for user in provider_b.character_prompts())
    claude_spoke = turn3.response.character_id == "claude"

    rows.append("## Results")
    rows.append(f"- Session A (post-event) narrative context reached the model: {a_after_event}")
    rows.append(f"- Session B (pre-event) narrative context absent: {b_before_event}")
    rows.append(f"- Claude entered the runtime normally: {claude_spoke}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    ok = a_after_event and b_before_event and claude_spoke
    print(f"\nSummary: post-event context={a_after_event} pre-event absent={b_before_event} claude={claude_spoke}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
