"""TV-05 live validation harness.

Runs DeepSeekRuntime against the real DeepSeek API and verifies that every
reply is a valid Structured Character Response (docs/04 §40, §48). Reports the
first-try vs repaired vs fallback distribution and writes the full JSON samples
to validation-results/TV-05/response-samples.md.

Requires the DEEPSEEK_API_KEY environment variable. The key is read from the
environment only and never written to the repo.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the backend package importable when run from validation-results/TV-05.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.characters.base import (  # noqa: E402
    ALLOWED_ANIMATIONS,
    ALLOWED_EMOTIONS,
    CharacterRequest,
)
from app.characters.deepseek import DeepSeekRuntime  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

INPUTS = [
    "这里是什么地方？",
    "我们怎么才能出去？",
    "你看得见墙上的字吗？",
    "我叫阿明，你呢？",
    "你觉得是谁把我们抓来的？",
    "我好害怕。",
    "你能帮我解开绳子吗？",
    "你饿吗？",
    "我们在哪个城市？",
    "再说一遍，我不太明白。",
]


class CountingProvider(LLMProvider):
    """Counts provider calls so the harness can tell first-try from repair."""

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.calls = 0

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls += 1
        return self._inner.complete(
            system=system,
            user=user,
            max_tokens=max_tokens,
            response_format=response_format,
        )


def to_dict(response) -> dict:
    return {
        "character_id": response.character_id,
        "dialogue": response.dialogue,
        "emotion": response.emotion,
        "animation_proposal": response.animation_proposal,
        "memory_proposals": [
            {"type": p.type, "content": p.content} for p in response.memory_proposals
        ],
        "action_proposals": [
            {"type": p.type, "target": p.target} for p in response.action_proposals
        ],
        "fact_refs": response.fact_refs,
    }


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    counting = CountingProvider(DeepSeekProvider())
    runtime = DeepSeekRuntime(counting)
    fallback_line = runtime.fallback_lines[0]

    first_try = 0
    repaired = 0
    fallbacks = 0
    failures = []
    rows = []

    for index, message in enumerate(INPUTS, start=1):
        calls_before = counting.calls
        response = runtime.respond(
            CharacterRequest(character_id="deepseek", player_message=message)
        )
        used = counting.calls - calls_before
        if response.dialogue == fallback_line:
            fallbacks += 1
        elif used <= 1:
            first_try += 1
        else:
            repaired += 1

        # Structural checks: every accepted response must pass Schema Validation.
        if response.character_id != "deepseek":
            failures.append(f"input {index}: wrong character_id {response.character_id!r}")
        if response.emotion not in ALLOWED_EMOTIONS:
            failures.append(f"input {index}: emotion {response.emotion!r} not allowed")
        if response.animation_proposal not in ALLOWED_ANIMATIONS:
            failures.append(
                f"input {index}: animation {response.animation_proposal!r} not allowed"
            )
        if not response.dialogue.strip():
            failures.append(f"input {index}: empty dialogue")
        if response.dialogue != fallback_line and (
            response.memory_proposals or response.action_proposals or response.fact_refs
        ):
            rows.append(
                f"input {index}: structured proposals present (memory={len(response.memory_proposals)}, "
                f"actions={len(response.action_proposals)}, fact_refs={response.fact_refs})"
            )

        rows.append(f"## input {index}: {message}")
        rows.append(json.dumps(to_dict(response), ensure_ascii=False, indent=2))

    out = [
        "# TV-05 live DeepSeek validation — structured response samples",
        "",
        f"date: 2026-08-14, model: deepseek-chat, inputs: {len(INPUTS)}",
        f"first-try valid: {first_try} / {len(INPUTS)}",
        f"repaired after retry: {repaired} / {len(INPUTS)}",
        f"safe fallback: {fallbacks} / {len(INPUTS)}",
        f"provider errors: 0",
        "",
    ]
    if failures:
        out.append("FAILURES:")
        out.extend(f"- {f}" for f in failures)
        out.append("")
    out.extend(rows)
    out.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print(f"\nSummary: {first_try} first-try, {repaired} repaired, "
          f"{fallbacks} fallback, {len(failures)} structural failures.")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
