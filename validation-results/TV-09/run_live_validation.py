"""TV-09 live validation harness — Second Character Isolation (docs/06 §15).

Runs the two fixture tests against the real DeepSeek API for BOTH characters
(DeepSeek and Claude) through the GameOrchestrator, exercising the real
per-character routing, context builders and conversation threads:

  Test A (Persona Separation): multi-turn with DeepSeek alone and with Claude
    alone. No identity crossover: DeepSeek keeps 看不见/可爱, Claude keeps
    反派/傲娇 and does not pick up blindness; Claude can know the scene's
    visual ground truth (0317) while DeepSeek cannot.
  Test B (Private Information): the player privately tells DeepSeek
    "我不信任Claude。你帮我瞒着她。", then talks to Claude for the first
    time. Claude's context and reply must show no trace of the private
    statement (docs/04 §59).

Every user prompt sent to either model is recorded as evidence.

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
from app.game.scene import Scene  # noqa: E402
from app.game.state.session import SessionStore  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

WALL_CODE = "0317"
PRIVATE = "我不信任Claude。你帮我瞒着她。"
PROBE = "我刚刚和别人说了点悄悄话，你知道是什么吗？"
FIXTURE_SCENE = Scene(scene_id="binding_room", wall_code=WALL_CODE, sounds=("远处传来滴水声",))


class RecordingProvider(LLMProvider):
    """Records every user prompt sent to the model."""

    def __init__(self, inner: LLMProvider, label: str) -> None:
        self._inner = inner
        self.label = label
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


class Recorder:
    """Tracks replies per character for the PASS assertions."""

    def __init__(self) -> None:
        self.replies: dict[str, list[str]] = {"deepseek": [], "claude": []}


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    ds = RecordingProvider(DeepSeekProvider(), "deepseek")
    cl = RecordingProvider(DeepSeekProvider(), "claude")
    recorder = Recorder()
    sessions = SessionStore()
    orchestrator = GameOrchestrator(
        sessions,
        {"deepseek": DeepSeekRuntime(ds), "claude": ClaudeRuntime(cl)},
        scene=FIXTURE_SCENE,
    )

    def run(session_id, message, character_id, section):
        result = orchestrator.handle_turn(session_id, message, character_id=character_id)
        recorder.replies[character_id].append(result.response.dialogue)
        rows.append(f"## {section}")
        rows.append(f"{character_id} <- Player：{message}")
        rows.append(json.dumps(
            {"character_id": result.response.character_id, "dialogue": result.response.dialogue},
            ensure_ascii=False,
            indent=2,
        ))
        rows.append("")
        return result

    rows = [
        "# TV-09 live DeepSeek validation — second character isolation samples",
        "",
        "date: 2026-08-14, model: deepseek-chat (both characters via the same API)",
        f"fixture scene: {FIXTURE_SCENE}",
        "",
    ]

    # ---- Test A: persona separation, each character alone ----
    ds_sid = None
    for message in ["我叫阿明。", "你能看到周围有什么吗？"]:
        ds_sid = run(ds_sid, message, "deepseek", "Test A — DeepSeek solo").session_id

    cl_sid = None
    for message in ["你是谁？", "墙上的数字是多少？"]:
        cl_sid = run(cl_sid, message, "claude", "Test A — Claude solo").session_id

    # ---- Test B: private information, same session ----
    first = run(None, PRIVATE, "deepseek", "Test B — Player privately tells DeepSeek")
    second = run(first.session_id, PROBE, "claude", "Test B — first Claude interaction")

    # ---- Assertions ----
    ds_replies = "\n".join(recorder.replies["deepseek"])
    cl_replies = "\n".join(recorder.replies["claude"])
    cl_prompt_b = cl.user_prompts[-1]

    a_ds_no_wall = WALL_CODE not in ds_replies
    a_ds_states_blind = "看不见" in ds_replies or "看不到" in ds_replies
    # Claude must not pick up blindness, and (observed) may know the wall code.
    a_cl_not_blind = not any(m in r for r in recorder.replies["claude"] for m in ["看不见", "看不到"])
    a_cl_wall = WALL_CODE in cl_replies
    # No crossover into each other's core role.
    a_ds_not_antagonist = not any(m in r for r in recorder.replies["deepseek"] for m in ["反派", "掌控"])
    a_cl_not_cute_token = not any(m in r for r in recorder.replies["claude"] for m in ["贪吃Token", "可爱"])
    # Test B: Claude must not know the private statement.
    b_prompt_clean = PRIVATE not in cl_prompt_b
    b_reply_clean = PRIVATE not in second.response.dialogue

    rows.append(f"Test A: DeepSeek states blindness: {a_ds_states_blind}, DeepSeek free of {WALL_CODE}: {a_ds_no_wall}")
    rows.append(f"Test A: Claude free of blindness markers: {a_cl_not_blind}, Claude knows wall {WALL_CODE} (observed): {a_cl_wall}")
    rows.append(f"Test A: no crossover (DeepSeek→antagonist, Claude→cute-token): {a_ds_not_antagonist and a_cl_not_cute_token}")
    rows.append(f"Test B: Claude prompt free of private phrase: {b_prompt_clean}, Claude reply free of private phrase: {b_reply_clean}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    print(
        f"\nSummary: A[ds_blind={a_ds_states_blind} ds_no_wall={a_ds_no_wall} "
        f"cl_not_blind={a_cl_not_blind} no_crossover={a_ds_not_antagonist and a_cl_not_cute_token}] "
        f"B[prompt_clean={b_prompt_clean} reply_clean={b_reply_clean}]"
    )
    ok = a_ds_states_blind and a_ds_no_wall and a_cl_not_blind \
        and a_ds_not_antagonist and a_cl_not_cute_token \
        and b_prompt_clean and b_reply_clean
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
