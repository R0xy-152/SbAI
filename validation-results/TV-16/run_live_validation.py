"""TV-16 live Final Gate validation — End-to-End Stability (docs/06 §22-24).

Runs the REAL full stack (FastAPI API + real DeepSeek model + JSON session
repository) through the docs/06 §22 16-step flow with 20+ player inputs in one
session (docs/06 §23), plus 2 additional independent sessions, and records
every docs/06 §24 non-blocking criterion as a deterministic check.

  启动游戏 → 固定Scene → 与DeepSeek自由对话 → 提供视觉信息 → 继续对话 →
  触发Narrative Signal → Event执行 → Claude出现 → 切换至Claude对话 →
  继续自由聊天 → 写入Important Memory → 触发基础动画(SHOW_CHARACTER+FADE_IN) →
  查看History → Refresh → 恢复Session → 继续游戏

A mid-session provider timeout is also injected (docs/06 §21) inside the
combined state to confirm 503 + retry keeps the same session.

Requires DEEPSEEK_API_KEY (environment only — never committed).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient

from app.characters.claude import ClaudeRuntime  # noqa: E402
from app.characters.deepseek import DeepSeekRuntime  # noqa: E402
from app.game.orchestrator import GameOrchestrator  # noqa: E402
from app.game.state.session import SessionStore  # noqa: E402
from app.main import create_app  # noqa: E402
from app.narrative.interpreter import NarrativeInterpreter  # noqa: E402
from app.narrative.poc import EV_POC_CLAUDE_APPEARS, build_poc_events  # noqa: E402
from app.persistence.repository import JsonSessionRepository  # noqa: E402
from app.providers.base import LLMProvider, ProviderError  # noqa: E402
from app.providers.deepseek import DeepSeekProvider  # noqa: E402

WALL_CODE = "0317"


class RecordingProvider(LLMProvider):
    """Records (system, user, result) for every call that reaches the real
    model, and can inject one recoverable timeout on the next character call."""

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.calls: list[tuple[str, str, str]] = []
        self.fail_next_character = False

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        if self.fail_next_character and "剧情理解器" not in system:
            self.fail_next_character = False
            raise ProviderError("timeout (injected)")
        result = self._inner.complete(
            system=system,
            user=user,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        self.calls.append((system, user, result))
        return result


def _app(repo_dir: str, provider: LLMProvider) -> TestClient:
    app = create_app()
    orchestrator = GameOrchestrator(
        SessionStore(),
        {
            "deepseek": DeepSeekRuntime(provider),
            "claude": ClaudeRuntime(provider),
        },
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
        repository=JsonSessionRepository(repo_dir),
    )
    app.state.orchestrator = orchestrator
    return TestClient(app)


def _post(client, message, session_id=None, character_id=None):
    payload = {"message": message, "session_id": session_id}
    if character_id:
        payload["character_id"] = character_id
    return client.post("/api/chat", json=payload)


def _main_session(rows: list[str], results: list[tuple[str, bool]]):
    """Session 1: the full 16-step flow, 20+ player inputs."""
    repo_dir = tempfile.mkdtemp(prefix="tv16-main-")
    provider = RecordingProvider(DeepSeekProvider())
    client = _app(repo_dir, provider)

    rows.append("## Session 1 — 完整16步流程（20+轮 Player 输入）")
    session_id = None
    expected = "deepseek"
    identities_ok = True
    player_turns = 0
    dialogues: list[str] = []

    def turn(message, character_id=None, note=None):
        """One successful player turn. Keeps the running expected speaker."""
        nonlocal session_id, expected, identities_ok, player_turns
        response = _post(client, message, session_id, character_id)
        if character_id is not None:
            expected = character_id
        if response.status_code != 200:
            rows.append(f"- 「{message}」→ HTTP {response.status_code}（意外失败）")
            identities_ok = False
            return {}, False
        body = response.json()
        session_id = body.get("session_id", session_id)
        ok = body.get("character_id") == expected
        identities_ok = identities_ok and ok
        player_turns += 1
        dialogues.append(body.get("dialogue", ""))
        tag = f" [{note}]" if note else ""
        rows.append(f"- 「{message}」→ [{body['character_id']}]{tag} {body['dialogue']}")
        return body, ok

    # 启动游戏 / 固定Scene / 与DeepSeek自由对话 / 提供视觉信息 / 继续对话.
    turn("你好，我们现在在哪里？")
    turn("我好像在一间屋子里，周围黑漆漆的，你看得到什么吗？")
    turn("你有没有听到什么奇怪的声音？")

    # 触发Narrative Signal → Event执行 → Claude出现.
    body, _ = turn("是谁把我们抓来的？", note="Event触发")
    event_presented = body.get("presentation") == ["SHOW_CHARACTER claude"]
    rows.append(f"- 事件触发回合 presentation：{body.get('presentation')}")

    # 切换至Claude对话 → 继续自由聊天.
    turn("Claude，原来你在这里。", character_id="claude")
    turn("你为什么要躲着我们？")
    turn("你到底想对我们做什么？")

    # 切回DeepSeek → 写入一条Important Memory.
    turn("DeepSeek，你在听吗？", character_id="deepseek")
    turn("我叫阿明，我很怕黑，你要记住哦。", note="Memory写入")
    orchestrator = client.app.state.orchestrator
    deepseek_memories = orchestrator._memory_stores[session_id].retrieve("deepseek")
    claude_memories = orchestrator._memory_stores[session_id].retrieve("claude")
    rows.append(
        f"- Memory scope：DeepSeek {len(deepseek_memories)} 条"
        f"（{[m.content for m in deepseek_memories]}），"
        f"Claude {len(claude_memories)} 条"
    )

    # 继续自由聊天；Claude隔离检查；Event不重复提交.
    turn("你会一直陪着我吗？")
    turn("Claude，你知道我刚才和DeepSeek聊了什么吗？", character_id="claude")
    turn("哼，你不说我也知道。")
    turn("DeepSeek，我们一定能出去的，对吧？", character_id="deepseek")
    turn("我有点饿了。")
    reask_body, _ = turn("再问一次：是谁把我们抓来的？", note="Event重问")
    reask_no_refire = reask_body.get("presentation") == []
    turn("你记得我叫什么名字吗？", note="DeepSeek回忆")
    anim_body, _ = turn("做个测试动画的动作提示给我看看。")
    animation_seen = anim_body.get("animation") not in (None, "none")
    turn("你觉得我们应该相信Claude吗？")
    turn("我好像听到门外有脚步声。")
    turn("你认识那个把我们关在这里的人吗？")

    # docs/06 §23: 单次正式验证 ≥ 20 轮 Player 输入.
    rows.append(f"- Session 1 Player 输入轮数：{player_turns}（另加重试 + Refresh续玩）")
    results.append(("Session 1 ≥20轮 Player 输入", player_turns >= 20))

    # 单次Provider失败导致Session报废（注入一次超时，docs/06 §21）.
    provider.fail_next_character = True
    failed = _post(client, "你在吗？", session_id)
    failed_is_503 = failed.status_code == 503
    rows.append(f"- 注入超时 → HTTP {failed.status_code}（503=可恢复）")
    retry = _post(client, "你在吗？", session_id)
    retry_body = retry.json() if retry.status_code == 200 else {}
    retry_same_session = (
        retry.status_code == 200 and retry_body.get("session_id") == session_id
    )
    rows.append(f"- 重试 → HTTP {retry.status_code}，同一 session：{retry_same_session}")
    results.append(
        ("单次Provider失败可恢复（503→重试同session）", failed_is_503 and retry_same_session)
    )

    # 查看History（docs/01 §18）.
    history = client.get(f"/api/chat/history?session_id={session_id}")
    history_ok = history.status_code == 200
    history_messages = history.json().get("messages", []) if history_ok else []
    rows.append(f"- History 消息数：{len(history_messages)}（HTTP {history.status_code}）")
    history_ordered = (
        history_ok
        and history_messages[0]["role"] == "player"
        and history_messages[-1]["role"] == "character"
    )
    results.append(("History可查看且顺序正确", history_ok and history_ordered))

    # docs/06 §24 checks against the recorded real-model calls.
    ds_calls = [user for system, user, _ in provider.calls if "角色 DeepSeek" in system]
    cl_calls = [user for system, user, _ in provider.calls if "角色 Claude" in system]
    no_vision_leak = all(WALL_CODE not in user for user in ds_calls)
    claude_sees_scene = any(WALL_CODE in user for user in cl_calls)
    no_fear_to_claude = all("怕黑" not in user for user in cl_calls)
    repairs = sum("[系统提示]" in user for user in ds_calls + cl_calls)
    all_dialogues_nonempty = all(dialogues) and len(dialogues) == player_turns

    rows.append(f"- DeepSeek 从未收到场景视觉真相 {WALL_CODE}：{no_vision_leak}")
    rows.append(f"- Claude（非盲）收到场景视觉真相：{claude_sees_scene}")
    rows.append(f"- Claude 的上下文从未出现 DeepSeek 私人记忆（怕黑）：{no_fear_to_claude}")
    rows.append(f"- 全程 [系统提示] 修复次数：{repairs}（观察项）")
    rows.append(f"- 模型 animation_proposal 出现非 none 值：{animation_seen}（观察项）")
    results.append(("DeepSeek视觉泄漏不存在", no_vision_leak))
    results.append(("Claude获得私人Memory不存在（上下文）", no_fear_to_claude))
    results.append(("Claude获得私人Memory不存在（Memory scope）", len(claude_memories) == 0))
    results.append(("Invalid模型内容未进入正式游戏", all_dialogues_nonempty))
    results.append(("角色身份串台不存在", identities_ok))
    results.append(("Event展示指令到达（SHOW_CHARACTER claude）", event_presented))
    results.append(("Event不重复提交（重新提问不再触发）", reask_no_refire))

    # LLM直接改变Game State / Event重复提交：only the event changed flags.
    repo = JsonSessionRepository(repo_dir)
    state = repo.load(session_id).narrative_state
    state_exact = (
        state.narrative_flags == {"claude_has_appeared"}
        and state.completed_events == {EV_POC_CLAUDE_APPEARS}
    )
    rows.append(
        f"- 最终 Narrative State：flags={state.narrative_flags}, "
        f"completed={state.completed_events}"
    )
    results.append(("LLM直接改变Game State不存在（仅Event改动）", state_exact))
    results.append(
        ("Event不重复提交（completed仅一次）", state.completed_events == {EV_POC_CLAUDE_APPEARS})
    )

    # Refresh → 恢复Session → 继续游戏（fresh process, same repo）.
    rows.append("## Session 1 — Refresh → 恢复Session → 继续游戏")
    provider2 = RecordingProvider(DeepSeekProvider())
    client2 = _app(repo_dir, provider2)
    cont = _post(client2, "继续", session_id)
    cont_body = cont.json() if cont.status_code == 200 else {}
    restored_ok = (
        cont.status_code == 200
        and cont_body.get("session_id") == session_id
        and cont_body.get("character_id") == "deepseek"
    )
    rows.append(
        f"- 恢复后继续 → HTTP {cont.status_code}，同session={restored_ok}，"
        f"当前角色={cont_body.get('character_id')}"
    )
    history2 = client2.get(f"/api/chat/history?session_id={session_id}")
    history2_ok = history2.status_code == 200
    history2_last = history2.json()["messages"][-1] if history2_ok else {}
    restored_history_ok = history2_ok and history2_last.get("role") == "character"
    state2 = repo.load(session_id).narrative_state
    restored_state_ok = (
        state2.narrative_flags == {"claude_has_appeared"}
        and state2.completed_events == {EV_POC_CLAUDE_APPEARS}
    )
    orchestrator2 = client2.app.state.orchestrator
    restored_claude_mem = orchestrator2._memory_stores[session_id].retrieve("claude")
    restored_memory_ok = len(restored_claude_mem) == 0
    rows.append(
        f"- 恢复后 Narrative State 正确：{restored_state_ok}；"
        f"Claude 仍无私人 Memory：{restored_memory_ok}"
    )
    results.append(
        ("Refresh后Session正确恢复且Narrative State正确", restored_ok and restored_state_ok)
    )
    results.append(("Refresh后History仍存在", restored_history_ok))
    results.append(("Refresh后Memory Scope保持正确", restored_memory_ok))

    rows.append("- 全部 API 响应均携带完整契约字段（session_id/character_id/dialogue）：见上述行")


def _secondary_session(rows, results, label, script):
    """A second/third independent session (docs/06 §23: 3个独立Session)."""
    repo_dir = tempfile.mkdtemp(prefix="tv16-sec-")
    provider = RecordingProvider(DeepSeekProvider())
    client = _app(repo_dir, provider)
    rows.append(f"## {label} — 独立Session")
    session_id = None
    expected = "deepseek"
    ok = True
    turns = 0
    for message, character_id in script:
        response = _post(client, message, session_id, character_id)
        if character_id is not None:
            expected = character_id
        if response.status_code != 200:
            ok = False
            rows.append(f"- 「{message}」→ HTTP {response.status_code}")
            continue
        body = response.json()
        session_id = body.get("session_id", session_id)
        turns += 1
        ok = ok and body.get("character_id") == expected
        rows.append(f"- 「{message}」→ [{body['character_id']}] {body['dialogue']}")
    rows.append(f"- {label} 轮数：{turns}，无异常：{ok}")
    results.append((f"{label} 独立Session稳定", ok and turns >= 3))


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    rows = [
        "# TV-16 live Final Gate validation — End-to-End Stability samples",
        "",
        "date: 2026-08-14, model: deepseek-chat（经完整 FastAPI API + JSON Session Repository）",
        "",
        "真实组合状态下执行 docs/06 §22 的完整16步流程；以下为真实对话样本与检查结果。",
        "",
    ]
    results: list[tuple[str, bool]] = []

    _main_session(rows, results)
    _secondary_session(
        rows, results, "Session 2",
        [
            ("你好。", None),
            ("这里是哪里？", None),
            ("是谁把我们抓来的？", None),
            ("Claude，你终于出现了。", "claude"),
        ],
    )
    _secondary_session(
        rows, results, "Session 3",
        [
            ("在吗？", None),
            ("我有点害怕。", None),
            ("Claude，你还记得什么？", "claude"),
        ],
    )

    rows.append("## Results")
    for label, ok in results:
        rows.append(f"- {label}: {ok}")
    rows.append("")

    out_path = Path(__file__).resolve().parent / "response-samples.md"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))

    ok = all(ok for _, ok in results)
    print("\n" + " | ".join(f"{label.split('（')[0]}={ok}" for label, ok in results))
    print(f"==> {'PASS' if ok else 'FAIL'} ({sum(1 for _, ok in results if ok)}/{len(results)})")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
