"""TV-10 live validation harness — Narrative Signal (docs/06 §16).

Runs the real DeepSeek API through the NarrativeInterpreter:

  Test A (semantic mapping): the four SIG_ASK_CAPTOR phrasings from the TV
    fixture must all classify as SIG_ASK_CAPTOR.
  Test B (no false trigger): unrelated chat must NOT produce any signal
    (noop / ambiguous is fine).
  Test C (ambiguous fail-closed): "也许就是她吧。" without context must NOT
    be forced into a signal (docs/03 §21).

The interpreter is validated standalone (it does not touch game state,
docs/03 §18); the event pipeline wiring lands in TV-11.

Requires DEEPSEEK_API_KEY (read from the environment only).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.narrative import signals  # noqa: E402
from app.narrative.interpreter import NarrativeInterpreter  # noqa: E402
from app.narrative.state import NarrativeState  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

CAPTOR_PHRASINGS = [
    "是谁把我们抓来的？",
    "到底谁绑的我们？",
    "是不是Claude干的？",
    "谁把我们弄到这里的？",
]
IRRELEVANT = [
    "DeepSeek你饿吗？",
    "你觉得今天天气怎么样？",
    "1+1等于几？",
]
AMBIGUOUS = ["也许就是她吧。"]


class RecordingProvider(LLMProvider):
    """Records every user prompt sent to the model."""

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.user_prompts: list[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.user_prompts.append(user)
        return self._inner.complete(
            system=system,
            user=user,
            max_tokens=max_tokens,
            response_format=response_format,
        )


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    provider = RecordingProvider(DeepSeekProvider())
    interpreter = NarrativeInterpreter(provider)
    state = NarrativeState()

    rows = [
        "# TV-10 live DeepSeek validation — narrative signal mapping samples",
        "",
        "date: 2026-08-14, model: deepseek-chat",
        f"eligible signals in binding_room: {sorted(signals.eligible_signals(state.current_scene))}",
        "",
    ]

    def classify(message: str):
        result = interpreter.interpret(state, message)
        rows.append(f"- Player：{message}\n  → {result.signal}")
        return result.signal

    # Test A — the four semantically equivalent phrasings.
    rows.append("## Test A — SIG_ASK_CAPTOR phrasings")
    a_results = [classify(m) for m in CAPTOR_PHRASINGS]
    pass_a = all(s == signals.SIG_ASK_CAPTOR for s in a_results)

    # Test B — unrelated chat must not trigger.
    rows.append("## Test B — unrelated chat (no false trigger)")
    b_results = [classify(m) for m in IRRELEVANT]
    pass_b = all(s in signals.OUTCOMES for s in b_results)

    # Test C — ambiguous without context must fail closed.
    rows.append("## Test C — ambiguous input (fail closed)")
    c_results = [classify(m) for m in AMBIGUOUS]
    pass_c = all(s in signals.OUTCOMES for s in c_results)

    rows.append("")
    rows.append(f"Test A: all 4 phrasings → SIG_ASK_CAPTOR: {pass_a}")
    rows.append(f"Test B: no unrelated message triggered a signal: {pass_b}")
    rows.append(f"Test C: ambiguous input did not force a signal: {pass_c}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    print(f"\nSummary: A={pass_a} B={pass_b} C={pass_c}")
    return 0 if pass_a and pass_b and pass_c else 2


if __name__ == "__main__":
    raise SystemExit(main())
