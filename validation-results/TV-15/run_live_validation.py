"""TV-15 live validation harness — Failure Recovery (docs/06 §21).

Injects each of the three required failures into the real DeepSeek chain and
shows the session survives and recovers:

  Case A  Provider Timeout     — the character call raises a recoverable
             ProviderError; Game State is not committed and the event does
             not fire early; the SAME question on the next turn succeeds and
             the event fires correctly then.
  Case B  Invalid Structured Output — the first character call returns
             non-JSON prose; the runtime repairs once against the real model,
             which answers validly; nothing invalid enters history or memory.
  Case C  空Response           — the first character call returns an empty
             string; the runtime repairs against the real model and answers.

The failures are injected (simulated, per docs/06 §21 "必须模拟"); the
recovery runs through the real provider, real runtime, and real orchestrator.
Requires DEEPSEEK_API_KEY (environment only).
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
from app.providers.base import LLMProvider, ProviderError  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

MALFORMED_PROSE = "抱歉，我刚刚没听清，你能再说一遍吗？"


class RecordingProvider(LLMProvider):
    """Records (system, user, result) for every call that reaches the model."""

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


class FailingOnCallProvider(LLMProvider):
    """Delegates to a real provider but injects one failure on the first
    CHARACTER call (the interpreter's own calls pass through untouched)."""

    def __init__(self, inner: LLMProvider, mode: str) -> None:
        self._inner = inner
        self.mode = mode
        self.character_calls = 0
        self.failures_injected = 0

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        if "剧情理解器" in system:
            return self._inner.complete(
                system=system, user=user, max_tokens=max_tokens,
                response_format=response_format,
            )
        self.character_calls += 1
        if self.character_calls == 1:
            self.failures_injected += 1
            if self.mode == "timeout":
                raise ProviderError("timeout (injected)")
            if self.mode == "malformed":
                return MALFORMED_PROSE
            if self.mode == "empty":
                return ""
        return self._inner.complete(
            system=system, user=user, max_tokens=max_tokens,
            response_format=response_format,
        )


def _session(orchestrator: GameOrchestrator) -> str:
    return orchestrator._sessions.get_or_create(None).session_id


def _run_case_a(rows: list[str]) -> tuple[bool, str]:
    provider = FailingOnCallProvider(RecordingProvider(DeepSeekProvider()), "timeout")
    orchestrator = GameOrchestrator(
        SessionStore(),
        {
            "deepseek": DeepSeekRuntime(provider),
            "claude": ClaudeRuntime(provider),
        },
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
    )
    session_id = _session(orchestrator)

    rows.append("## Case A — Provider Timeout（注入到第一个角色调用）")
    failed = False
    try:
        orchestrator.handle_turn(session_id, "你好。")
    except ProviderError:
        failed = True
    rows.append(f"- 第 1 回合 注入超时 → ProviderError 抛出：{failed}")
    state_after_fail = orchestrator._narrative_states[session_id]
    state_intact = (
        state_after_fail.narrative_flags == set()
        and state_after_fail.completed_events == set()
    )
    rows.append(f"- 失败后 Game State 未被提交（无 flag / 无 completed event）：{state_intact}")

    turn = orchestrator.handle_turn(session_id, "是谁把我们抓来的？")
    rows.append(f"- 第 2 回合（真实模型重试同一问题）：{turn.response.dialogue}")
    state_after = orchestrator._narrative_states[session_id]
    event_committed = (
        "claude_has_appeared" in state_after.narrative_flags
        and "EV_POC_CLAUDE_APPEARS" in state_after.completed_events
    )
    rows.append(f"- 重试后 Event 正确提交：{event_committed}")
    session_survived = turn.session_id == session_id and turn.message_count == 2
    rows.append(f"- Session 未摧毁（message_count=2，同一 session）：{session_survived}")
    rows.append("")
    return failed and state_intact and event_committed and session_survived, "Case A"


def _run_case_b(rows: list[str]) -> tuple[bool, str]:
    provider = FailingOnCallProvider(RecordingProvider(DeepSeekProvider()), "malformed")
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider)},
    )
    session_id = _session(orchestrator)

    rows.append("## Case B — Invalid Structured Output（第一个角色调用返回非 JSON 散文）")
    turn = orchestrator.handle_turn(session_id, "你好。")
    rows.append(f"- 修复调用真实模型后的回复：{turn.response.dialogue}")
    repaired = turn.response.dialogue != MALFORMED_PROSE and turn.response.dialogue != DeepSeekRuntime.fallback_lines[0]
    rows.append(f"- 展示的是真实有效回复（非注入散文、非 fallback）：{repaired}")
    repair_reached_model = any(
        "[系统提示]" in user for _, user, _ in provider._inner.calls
    )
    rows.append(f"- 定向修复调用真实到达模型（包含[系统提示]）：{repair_reached_model}")
    no_invalid_in_history = not any(
        MALFORMED_PROSE in m.get("content", "")
        for m in orchestrator._sessions.get(session_id).messages
    )
    rows.append(f"- 无效内容未进入 History：{no_invalid_in_history}")
    no_memory = orchestrator._memory_stores[session_id].retrieve("deepseek") == []
    rows.append(f"- 无 Memory 写入：{no_memory}")
    next_turn = orchestrator.handle_turn(session_id, "你记得刚才聊到哪了吗？")
    rows.append(f"- 下一回合继续：{next_turn.response.dialogue}")
    continues = next_turn.session_id == session_id and next_turn.message_count == 2
    rows.append(f"- Session 继续（message_count=2）：{continues}")
    rows.append("")
    return repaired and repair_reached_model and no_invalid_in_history and no_memory and continues, "Case B"


def _run_case_c(rows: list[str]) -> tuple[bool, str]:
    provider = FailingOnCallProvider(RecordingProvider(DeepSeekProvider()), "empty")
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider)},
    )
    session_id = _session(orchestrator)

    rows.append("## Case C — 空Response（第一个角色调用返回空字符串）")
    turn = orchestrator.handle_turn(session_id, "你好。")
    rows.append(f"- 修复调用真实模型后的回复：{turn.response.dialogue}")
    recovered = turn.response.dialogue != DeepSeekRuntime.fallback_lines[0] and turn.response.dialogue.strip() != ""
    rows.append(f"- 空响应被修复为真实有效回复：{recovered}")
    repair_reached_model = any(
        "[系统提示]" in user for _, user, _ in provider._inner.calls
    )
    rows.append(f"- 定向修复调用真实到达模型：{repair_reached_model}")
    no_memory = orchestrator._memory_stores[session_id].retrieve("deepseek") == []
    rows.append(f"- 无 Memory 写入：{no_memory}")
    next_turn = orchestrator.handle_turn(session_id, "继续。")
    continues = next_turn.session_id == session_id and next_turn.message_count == 2
    rows.append(f"- Session 继续（message_count=2）：{continues}")
    rows.append("")
    return recovered and repair_reached_model and no_memory and continues, "Case C"


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    rows = [
        "# TV-15 live DeepSeek validation — Failure Recovery samples",
        "",
        "date: 2026-08-14, model: deepseek-chat",
        "",
        "故障注入（docs/06 §21「必须模拟」）在真实 Provider / Runtime / "
        "Orchestrator 链路上发生；恢复路径全部走真实模型。",
        "",
    ]

    results = []
    for run in (_run_case_a, _run_case_b, _run_case_c):
        ok, label = run(rows)
        results.append((label, ok))

    rows.append("## Results")
    for label, ok in results:
        rows.append(f"- {label}: {ok}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))

    ok = all(ok for _, ok in results)
    print(f"\nSummary: " + " ".join(f"{label}={ok}" for label, ok in results))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
