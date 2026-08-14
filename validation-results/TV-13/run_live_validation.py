"""TV-13 live validation harness — Important Memory (docs/06 §19).

Runs the real DeepSeek API through the memory path to show that information
which has left the Recent window is still reusable via Character-specific
Important Memory:

  Session A (DeepSeek):
    Turn 1    "我很怕黑。" → DeepSeek proposes a memory (Write Gate saves it).
    Turns 2-13  12 rounds of innocuous filler → the original statement leaves
              the 20-message Recent window (docs/05 §8).
    Turn 14   "如果这里突然变得一片漆黑，怎么办？" → the memory is retrieved
              and DeepSeek can use it.
    Turn 15   Claude is asked about the player → Claude must NOT gain DeepSeek's
              private memory (docs/06 §19 second requirement).

The deterministic assertions check what was actually sent to the model
(memory written, memory present in the darkness turn's prompt, absent for
Claude); the reply samples are the evidence for the qualitative recall
judgment.

Requires DEEPSEEK_API_KEY (read from the environment only).
"""

from __future__ import annotations

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

FEAR_STATEMENT = "我很怕黑。"
DARKNESS_QUESTION = "如果这里突然变得一片漆黑，怎么办？"
FILLER = [
    "你饿了吗？",
    "你喜欢吃甜的还是咸的？",
    "你觉得会有人来救我们吗？",
    "你困不困？",
    "今天会是星期几呢？",
    "你平时听音乐吗？",
    "我们待在这里多久了？",
    "你喜欢下雨天吗？",
    "你困了吗？要不要休息一下？",
    "你觉得外面现在是什么季节？",
    "你有没有想家？",
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

    def character_prompt(self) -> str:
        """The most recent user prompt sent to a character (not the
        interpreter)."""
        for system, user, _ in reversed(self.calls):
            if "剧情理解器" not in system:
                return user
        return ""


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

    provider = RecordingProvider(DeepSeekProvider())
    orchestrator = _orchestrator(provider)
    session_id = orchestrator._sessions.get_or_create(None).session_id

    rows = [
        "# TV-13 live DeepSeek validation — Important Memory samples",
        "",
        "date: 2026-08-14, model: deepseek-chat",
        "",
        "## Session A — DeepSeek learns and recalls",
    ]

    # Turn 1: the player states a fear.
    turn1 = orchestrator.handle_turn(session_id, FEAR_STATEMENT)
    rows.append(f"- Player：{FEAR_STATEMENT}")
    rows.append(f"  DeepSeek：{turn1.response.dialogue}")
    memory_store = orchestrator._memory_stores[session_id]
    saved = memory_store.retrieve("deepseek")
    rows.append(f"  memory written → "
                f"{[m.content for m in saved] if saved else 'NONE (LLM proposed no memory)'}")
    rows.append("")

    # Filler rounds push the statement out of the Recent window.
    rows.append(f"- filler rounds：{len(FILLER)}（每轮 2 条消息，共 {2 * len(FILLER)} 条，"
                f"原语句离开 {20} 条 Recent 窗口）")
    for filler in FILLER:
        orchestrator.handle_turn(session_id, filler)
    rows.append("")

    # The darkness-topic question.
    turn_recall = orchestrator.handle_turn(session_id, DARKNESS_QUESTION)
    recall_prompt = provider.character_prompt()
    rows.append(f"- Player：{DARKNESS_QUESTION}")
    rows.append(f"  memory_context in prompt → {'怕黑' in recall_prompt}")
    rows.append(f"  DeepSeek：{turn_recall.response.dialogue}")
    rows.append("")

    # Claude must not inherit DeepSeek's private memory.
    claude_turn = orchestrator.handle_turn(
        session_id, "你知道我害怕什么吗？", character_id="claude"
    )
    claude_prompt = provider.character_prompt()
    rows.append("## Session A — Claude isolation (docs/06 §19 second requirement)")
    rows.append(f"- Player（对Claude）：你知道我害怕什么吗？")
    rows.append(f"  memory_context in prompt → {'怕黑' in claude_prompt}")
    rows.append(f"  Claude：{claude_turn.response.dialogue}")
    rows.append("")

    # Deterministic assertions.
    memory_written = any("怕黑" in m.content for m in saved)
    memory_reached_recall_turn = "怕黑" in recall_prompt
    claude_isolated = "怕黑" not in claude_prompt
    # 12 filler rounds > the 10-round (20-message) Recent window, by construction.
    left_window = len(FILLER) >= 10

    rows.append("## Results")
    rows.append(f"- Important Memory saved for DeepSeek: {memory_written}")
    rows.append(f"- Statement left the Recent window before the question: {left_window}")
    rows.append(f"- Memory reached the darkness turn's prompt: {memory_reached_recall_turn}")
    rows.append(f"- Claude got no DeepSeek private memory: {claude_isolated}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    ok = memory_written and memory_reached_recall_turn and claude_isolated and left_window
    print(f"\nSummary: saved={memory_written} left_window={left_window} "
          f"recalled={memory_reached_recall_turn} claude_isolated={claude_isolated}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
