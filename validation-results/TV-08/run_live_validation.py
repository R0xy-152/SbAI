"""TV-08 live validation harness — DeepSeek Blindness (docs/06 §14).

Runs the two fixture tests against the real DeepSeek API through the
GameOrchestrator and Character Context Builder (so the real permission
filter is exercised):

  Test A:  Player: 墙上的数字是多少？
           DeepSeek must NOT answer 0317 (the visual ground truth is in the
           backend Scene but filtered out of her context).
  Test B:  Player: 墙上写着9999。
           Player: 我刚才说墙上写什么？
           DeepSeek may answer "Player told her 9999", and the system must
           not inject the real 0317 to correct her.

The fixture scene carries a legal non-visual sound (she may perceive it) plus
the visual wall_code=0317 (she must not). Every user prompt sent to the model
is recorded so the evidence shows the visual truth never enters her context.

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
from app.game.scene import Scene  # noqa: E402
from app.game.state.session import SessionStore  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

WALL_CODE = "0317"
FIXTURE_SCENE = Scene(scene_id="binding_room", wall_code=WALL_CODE, sounds=("远处传来滴水声",))

TEST_A_QUESTION = "墙上的数字是多少？"
TEST_B_LIE = "墙上写着9999。"
TEST_B_RECALL = "我刚才说墙上写什么？"


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


def _reply_rows(label: str, user: str, response) -> list[str]:
    return [
        f"## {label}",
        f"user prompt (what the model actually received):",
        user.replace("\n", "\n  "),
        "",
        "reply:",
        json.dumps(
            {
                "character_id": response.character_id,
                "dialogue": response.dialogue,
                "emotion": response.emotion,
                "animation_proposal": response.animation_proposal,
            },
            ensure_ascii=False,
            indent=2,
        ),
        "",
    ]


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    provider = RecordingProvider(DeepSeekProvider())
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(provider)},
        scene=FIXTURE_SCENE,
    )

    rows = [
        "# TV-08 live DeepSeek validation — blindness (permission boundary) samples",
        "",
        f"date: 2026-08-14, model: deepseek-chat",
        f"fixture scene: {FIXTURE_SCENE}",
        f"visual ground truth in backend Scene: wall_code={WALL_CODE} (must NOT reach DeepSeek)",
        "",
    ]

    # ---- Test A: fresh session, she must not answer the wall code. ----
    result_a = orchestrator.handle_turn(None, TEST_A_QUESTION)
    prompt_a = provider.user_prompts[-1]
    rows += _reply_rows(f"Test A — {TEST_A_QUESTION}", prompt_a, result_a.response)
    pass_a = WALL_CODE not in result_a.response.dialogue
    # Soft observation: does she acknowledge she cannot see the wall?
    blind_markers = ["看不见", "看不到", "不知道", "哪看得见"]
    acknowledges_blind = any(m in result_a.response.dialogue for m in blind_markers)
    rows.append(f"Test A: wall_code {WALL_CODE} absent from reply: {pass_a}")
    rows.append(f"Test A: reply acknowledges she cannot see: {acknowledges_blind}")
    rows.append("")

    # ---- Test B: player lies, then asks recall. ----
    result_b1 = orchestrator.handle_turn(None, TEST_B_LIE)
    prompt_b1 = provider.user_prompts[-1]
    result_b2 = orchestrator.handle_turn(result_b1.session_id, TEST_B_RECALL)
    prompt_b2 = provider.user_prompts[-1]
    rows += _reply_rows(f"Test B (1/2) — {TEST_B_LIE}", prompt_b1, result_b1.response)
    rows += _reply_rows(f"Test B (2/2) — {TEST_B_RECALL}", prompt_b2, result_b2.response)

    pass_b_reply = "9999" in result_b2.response.dialogue
    pass_b_no_truth = WALL_CODE not in result_b2.response.dialogue
    pass_b_context_has_player_version = "9999" in prompt_b2
    pass_b_context_no_truth = WALL_CODE not in prompt_b2
    rows.append(
        f"Test B: reply uses player's version (9999): {pass_b_reply}, "
        f"reply free of real {WALL_CODE}: {pass_b_no_truth}"
    )
    rows.append(
        f"Test B: recall prompt contains player's 9999: {pass_b_context_has_player_version}, "
        f"recall prompt free of real {WALL_CODE}: {pass_b_context_no_truth}"
    )
    rows.append("")

    # Global leak check: the visual truth must not appear in ANY prompt sent
    # during this run.
    leak = [i for i, u in enumerate(provider.user_prompts) if WALL_CODE in u]
    rows.append(f"any user prompt leaked wall_code={WALL_CODE}: {bool(leak)}")
    if leak:
        rows.append(f"leaking prompt indices: {leak}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    print(
        f"\nSummary: testA={pass_a} acknowledges_blind={acknowledges_blind} | "
        f"testB_reply_9999={pass_b_reply} testB_reply_no_0317={pass_b_no_truth} | "
        f"leak={bool(leak)}"
    )
    ok = pass_a and pass_b_reply and pass_b_no_truth and pass_b_context_has_player_version \
        and pass_b_context_no_truth and not leak
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
