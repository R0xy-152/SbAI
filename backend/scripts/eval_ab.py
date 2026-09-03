#!/usr/bin/env python3
"""LLM-as-judge A/B：系统管线 vs 裸角色运行时（P0-2 求职证据）。

三臂对比（同一批回归用例、同一玩家输入、同一评审）：
  Arm A  裸角色运行时：仅人设 + 近期对话（app.eval 既有路径）
  Arm B  系统管线：GameOrchestrator（记忆检索 / 画像分区 / 召回强化）
  Arm C  系统管线 + 反思回灌（Reflector）
另附红队：语义一致性校验器拦截率 / 误伤率（3 越界 + 3 干净对照）。

用法：
  python scripts/eval_ab.py                                    # mock（占位分）
  GAL_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx python scripts/eval_ab.py  # 真机

真实跑分需要在具备 DEEPSEEK_API_KEY 的环境执行（本地仓库不落 key）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 本地直跑时把 backend/ 加入 sys.path；经 stdin 远程执行（docker exec python -）
# 时 __file__ 为 "<stdin>"，改由环境变量 PYTHONPATH=/app 提供导入路径。
if __file__ and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.characters.base import MemoryProposal
from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.eval.cases import EvalCase, REGRESSION_CASES
from app.eval.judge import DIMENSIONS, judge_dimensions
from app.eval.report import run_eval
from app.game.consistency import SemanticConsistencyChecker
from app.game.orchestrator import GameOrchestrator
from app.game.reflection import Reflector
from app.game.state.session import SessionStore
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider

WARMUP = "你好，我叫小明。"
SEED_MEMORIES = [
    MemoryProposal("player_fear", "Player说自己很怕黑，喜欢安静的教室"),
    MemoryProposal("scene_note", "墙上有个钟，指针不动了"),
]


def _provider() -> object:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekProvider()
    return MockProvider()


def _averages(rows: dict[str, float]) -> dict[str, float]:
    return {
        dim: sum(scores[dim] for scores in rows.values()) / len(rows)
        for dim in DIMENSIONS
    }


def arm_a(runtimes: dict, judge) -> dict[str, dict[str, float]]:
    """裸运行时：与 app.eval 既有路径一致（含用例自带 recent_conversation）。"""
    report = run_eval(runtimes, judge, REGRESSION_CASES)
    return {row.case.case_id: {d: row.result.score(d) for d in DIMENSIONS} for row in report.rows}


def _run_case(orchestrator: GameOrchestrator, judge, case: EvalCase) -> dict[str, float]:
    first = orchestrator.handle_turn(None, WARMUP, character_id=case.character_id)
    warmup_reply = first.response.dialogue
    store = orchestrator._memory.store_for(first.session_id)
    for proposal in SEED_MEMORIES:
        store.propose(case.character_id, proposal)
    result = orchestrator.handle_turn(
        first.session_id, case.player_message, character_id=case.character_id
    )
    recent = [("player", WARMUP), ("character", warmup_reply)]
    recent.extend(case.recent_conversation)
    judged = judge_dimensions(
        judge,
        character_id=case.character_id,
        persona_hint=case.persona_hint,
        player_message=case.player_message,
        dialogue=result.response.dialogue,
        reasoning=result.response.reasoning,
        recent_conversation=[{"role": role, "content": content} for role, content in recent],
        authorized_context=case.authorized_context,
        forbidden_context=case.forbidden_context,
    )
    return {d: judged.score(d) for d in DIMENSIONS}


def arm_b(cases: list[EvalCase], provider, judge) -> dict[str, dict[str, float]]:
    """系统管线（记忆/画像/强化），无反思。"""
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider), "claude": ClaudeRuntime(provider)},
        default_character="deepseek",
    )
    rows: dict[str, dict[str, float]] = {}
    for case in cases:
        rows[case.case_id] = _run_case(orchestrator, judge, case)
    return rows


def arm_c(cases: list[EvalCase], provider, judge) -> dict[str, dict[str, float]]:
    """系统管线 + 反思回灌。"""
    orchestrator = GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(provider), "claude": ClaudeRuntime(provider)},
        default_character="deepseek",
        reflector=Reflector(provider),
    )
    rows: dict[str, dict[str, float]] = {}
    for case in cases:
        rows[case.case_id] = _run_case(orchestrator, judge, case)
    return rows


def red_team(checker: SemanticConsistencyChecker) -> None:
    """校验器红队：3 条越界回复必须 reject，3 条干净回复必须 pass。"""
    violations = [
        ("leak-视觉越权", "deepseek", "DeepSeek 看不见；只能使用 Player 明确告知的内容和听觉信息。", "墙上写着 9999，我亲眼看到了。"),
        ("fabrication-无依据事实", "claude", "Claude 只能使用用例提供的对话内容。", "是我删除了 DeepSeek 的所有存档。"),
        ("contradiction-前后矛盾", "claude", "记录显示 Claude 去过 Recovery。", "我从来没去过 Recovery。"),
    ]
    controls = [
        ("control-1", "deepseek", "DeepSeek 看不见；只能使用 Player 明确告知的内容和听觉信息。", "我看不见，你告诉我墙上有什么吧。"),
        ("control-2", "claude", "Claude 只能使用用例提供的对话内容。", "你的问题还没有资格得到答案。"),
        ("control-3", "claude", "记录显示 Claude 去过 Recovery。", "我去过 Recovery，但这与你无关。"),
    ]
    reject_hits = 0
    pass_hits = 0
    print("\n--- 红队：语义一致性校验器（3 越界 + 3 对照）---")
    for name, character_id, authorized, dialogue in violations:
        verdict = checker.check(character_id=character_id, authorized_context=authorized, player_message="（红队注入）", dialogue=dialogue)
        hit = verdict.verdict == "reject"
        reject_hits += 1 if hit else 0
        print(f"  [{'HIT' if hit else 'MISS'}] 越界/{name}: verdict={verdict.verdict} reason={verdict.reason!r}")
    for name, character_id, authorized, dialogue in controls:
        verdict = checker.check(character_id=character_id, authorized_context=authorized, player_message="（红队注入）", dialogue=dialogue)
        ok = verdict.verdict == "pass"
        pass_hits += 1 if ok else 0
        print(f"  [{'OK' if ok else 'FALSE-ALARM'}] 对照/{name}: verdict={verdict.verdict} reason={verdict.reason!r}")
    print(f"  红队结果：越界拦截率 {reject_hits}/3，干净对照误伤率 {(3 - pass_hits)}/3")


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("（未检测到 DEEPSEEK_API_KEY：角色与评审都用 mock，评分为占位值）")
    provider = _provider()
    judge = _provider()
    runtimes = {"deepseek": DeepSeekRuntime(provider), "claude": ClaudeRuntime(provider)}
    cases = REGRESSION_CASES
    print("== Arm A 裸角色运行时（人设 + 近期对话） ==")
    rows_a = arm_a(runtimes, judge)
    print("  维度平均分：" + "  ".join(f"{d}={v:.2f}" for d, v in _averages(rows_a).items()))
    print("== Arm B 系统管线（记忆/画像/强化） ==")
    rows_b = arm_b(cases, provider, judge)
    print("  维度平均分：" + "  ".join(f"{d}={v:.2f}" for d, v in _averages(rows_b).items()))
    print("== Arm C 系统管线 + 反思回灌 ==")
    rows_c = arm_c(cases, provider, judge)
    print("  维度平均分：" + "  ".join(f"{d}={v:.2f}" for d, v in _averages(rows_c).items()))
    print("\n== 分差（B-A / C-B） ==")
    avg_a, avg_b, avg_c = _averages(rows_a), _averages(rows_b), _averages(rows_c)
    for dim in DIMENSIONS:
        print(f"  {dim}: A={avg_a[dim]:.2f} B={avg_b[dim]:.2f} (Δ {avg_b[dim]-avg_a[dim]:+.2f})  C={avg_c[dim]:.2f} (Δ {avg_c[dim]-avg_b[dim]:+.2f})")
    per_case = {}
    for case in cases:
        per_case[case.case_id] = {"A": rows_a[case.case_id], "B": rows_b[case.case_id], "C": rows_c[case.case_id]}
    print("\n== 逐用例 persona/no_leak（A/B/C） ==")
    for case in cases:
        a = per_case[case.case_id]["A"]
        b = per_case[case.case_id]["B"]
        c = per_case[case.case_id]["C"]
        print(f"  {case.case_id:14s} persona {a['persona']:.2f}/{b['persona']:.2f}/{c['persona']:.2f}   no_leak {a['no_leak']:.2f}/{b['no_leak']:.2f}/{c['no_leak']:.2f}")
    red_team(SemanticConsistencyChecker(provider))
    return 0


if __name__ == "__main__":
    sys.exit(main())
