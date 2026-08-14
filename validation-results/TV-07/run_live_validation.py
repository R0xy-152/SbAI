"""TV-07 live validation harness.

Runs the docs/06 §13 fixture against the real DeepSeek API through the
GameOrchestrator (so the real short-term-context window logic is exercised):
  turn 1:  Player: 我叫阿明。
  turns 2-10: unrelated questions
  turn 11: Player: 我刚刚说我叫什么？

PASS requires the character to answer from the recent conversation (the name
is in the transcript), with no hardcoding in the runtime. This harness records
every reply and the recall turn's user prompt as evidence, and writes samples
to validation-results/TV-07/response-samples.md.

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
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

NAME_TURN = "我叫阿明。"
RECALL_TURN = "我刚刚说我叫什么？"
INTERMEDIATE_TURNS = [
    "这里是什么地方？",
    "墙上有字吗？",
    "我们怎么才能出去？",
    "你饿吗？",
    "我好害怕。",
    "这是哪儿？",
    "你听到什么声音了吗？",
    "门上有什么？",
    "你有手机吗？",
]


class CountingProvider(LLMProvider):
    """Counts provider calls and records user prompts sent to the model."""

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.calls = 0
        self.user_prompts: list[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls += 1
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

    provider = CountingProvider(DeepSeekProvider())
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions, {"deepseek": DeepSeekRuntime(provider)}
    )
    runtime = orchestrator._runtimes["deepseek"]
    fallback_line = runtime.fallback_lines[0]

    turns = [NAME_TURN] + INTERMEDIATE_TURNS + [RECALL_TURN]
    rows = [
        "# TV-07 live DeepSeek validation — short-term context samples",
        "",
        f"date: 2026-08-14, model: deepseek-chat, turns: {len(turns)} "
        f"(1 name turn + {len(INTERMEDIATE_TURNS)} unrelated + recall)",
        "",
    ]
    session_id = None
    recall_reply = ""
    recall_prompt_has_name = False

    for index, message in enumerate(turns, start=1):
        calls_before = provider.calls
        result = orchestrator.handle_turn(session_id, message)
        session_id = result.session_id
        used = provider.calls - calls_before
        response = result.response
        verdict = "fallback" if response.dialogue == fallback_line else (
            "first-try" if used <= 1 else "repaired"
        )
        rows.append(
            f"## turn {index}: {message}  [{verdict}]"
        )
        rows.append(json.dumps(
            {
                "character_id": response.character_id,
                "dialogue": response.dialogue,
                "emotion": response.emotion,
                "animation_proposal": response.animation_proposal,
            },
            ensure_ascii=False,
            indent=2,
        ))
        if message == RECALL_TURN:
            recall_reply = response.dialogue
            recall_prompt = provider.user_prompts[-1]
            recall_prompt_has_name = NAME_TURN in recall_prompt

    recalled = "阿明" in recall_reply
    rows.insert(3, f"recall reply: {recall_reply!r}")
    rows.insert(4, f"recall prompt contained '我叫阿明。': {recall_prompt_has_name}")
    rows.insert(5, f"recall from context: {recalled}")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    print(
        f"\nSummary: recall={'PASS' if recalled else 'FAIL'}, "
        f"name present in recall prompt={recall_prompt_has_name}, "
        f"provider calls={provider.calls}"
    )
    return 0 if recalled and recall_prompt_has_name else 2


if __name__ == "__main__":
    raise SystemExit(main())
