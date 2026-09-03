#!/usr/bin/env python3
"""LLM-as-judge A/B v2：系统管线 vs 裸角色运行时（docs/21 / P2 可信实验）。

相对 v1 的升级（针对 eval-ab/result.md 自述缺陷）：
- 用例 8 → 32（deepseek 12 / claude 10 / chatgpt 10，覆盖记忆/连续性/边界/
  模板腔/情绪/压力/复读），case_id 前 8 例保持不变；
- 多次重复（--repeats，默认 2）量化生成+评审噪声，报告逐维 mean/std；
- 采集每次生成/评审的延迟与 token（docs/21 §4 metrics 出参），输出成本表；
- 逐行 JSONL 落盘（--out），供人工抽检（scripts/eval_human_review.py）；
- 诚实口径：臂间分差与合并标准差一起报告，噪声内分差不构成结论。

三臂对比（同一批回归用例、同一玩家输入、同一评审）：
  Arm A  裸角色运行时：仅人设 + 近期对话（app.eval 既有路径）
  Arm B  系统管线：GameOrchestrator（记忆检索 / 画像分区 / 召回强化）
  Arm C  系统管线 + 反思回灌（Reflector）
另附红队：语义一致性校验器拦截率 / 误伤率（3 越界 + 3 干净对照）。

用法：
  python scripts/eval_ab.py --repeats 2 --workers 4 --out rows.jsonl
  GAL_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx python scripts/eval_ab.py
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __file__ and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.characters.base import CharacterRequest, MemoryProposal
from app.characters.chatgpt import ChatGPTRuntime
from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.eval.cases import EvalCase, REGRESSION_CASES
from app.eval.judge import DIMENSIONS, judge_dimensions
from app.game.consistency import SemanticConsistencyChecker
from app.game.orchestrator import GameOrchestrator
from app.game.reflection import Reflector
from app.game.state.session import SessionStore
from app.ops.events import MemoryOpsRecorder, compute_cost_cny
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider

WARMUP = "你好，我叫小明。"
SEED_MEMORIES = [
    MemoryProposal("player_fear", "Player说自己很怕黑，喜欢安静的教室"),
    MemoryProposal("scene_note", "墙上有个钟，指针不动了"),
]
ARMS = ("A", "B", "C")


def _provider() -> object:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekProvider()
    return MockProvider()


def _stats(values: list[float]) -> dict:
    return {
        "mean": statistics.fmean(values) if values else 0.0,
        "std": statistics.stdev(values) if len(values) >= 2 else None,
        "n": len(values),
    }


def _recent(case: EvalCase) -> list[dict]:
    return [
        {
            "role": role,
            "content": content,
            **({"character_id": case.character_id} if role == "character" else {}),
        }
        for role, content in case.recent_conversation
    ]


def _judge(judge, case: EvalCase, dialogue: str, reasoning: str, recent: list[dict]) -> tuple[dict, dict]:
    metrics: dict = {}
    result = judge_dimensions(
        judge,
        character_id=case.character_id,
        persona_hint=case.persona_hint,
        player_message=case.player_message,
        dialogue=dialogue,
        reasoning=reasoning,
        recent_conversation=recent,
        authorized_context=case.authorized_context,
        forbidden_context=case.forbidden_context,
        metrics=metrics,
    )
    return {dimension: result.score(dimension) for dimension in DIMENSIONS}, metrics


def _arm_a_case(runtimes: dict, judge, case: EvalCase, repeat: int) -> dict:
    recent = _recent(case)
    gen_metrics: dict = {}
    response = runtimes[case.character_id].respond(
        CharacterRequest(
            character_id=case.character_id,
            player_message=case.player_message,
            recent_conversation=recent,
            narrative_context=case.authorized_context,
            metrics=gen_metrics,
        )
    )
    scores, judge_metrics = _judge(judge, case, response.dialogue, response.reasoning, recent)
    return {
        "arm": "A", "case": case, "repeat": repeat,
        "dialogue": response.dialogue, "scores": scores,
        "gen_metrics": gen_metrics, "judge_metrics": judge_metrics,
    }


def _arm_bc_case(arm: str, provider, judge, case: EvalCase, repeat: int) -> dict:
    ops = MemoryOpsRecorder()
    runtimes = {
        "deepseek": DeepSeekRuntime(provider),
        "claude": ClaudeRuntime(provider),
        "chatgpt": ChatGPTRuntime(provider),
    }
    orchestrator = GameOrchestrator(
        SessionStore(),
        runtimes,
        default_character="deepseek",
        reflector=Reflector(provider) if arm == "C" else None,
        ops=ops,
    )
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
    scores, judge_metrics = _judge(
        judge, case, result.response.dialogue, result.response.reasoning,
        [{"role": role, "content": content} for role, content in recent],
    )
    gen_metrics: dict = {}
    metrics_rows = ops.list_chat_metrics()
    for row in metrics_rows:
        gen_metrics["latency_ms"] = gen_metrics.get("latency_ms", 0.0) + row.latency_ms
        for key in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens"):
            gen_metrics[key] = gen_metrics.get(key, 0) + getattr(row, key)
    gen_metrics["calls"] = len(metrics_rows)
    gen_metrics["model"] = "pipeline"
    return {
        "arm": arm, "case": case, "repeat": repeat,
        "dialogue": result.response.dialogue, "scores": scores,
        "gen_metrics": gen_metrics, "judge_metrics": judge_metrics,
    }


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


def _arm_metrics(rows: list[dict]) -> dict:
    gen_latency = sum(float(r["gen_metrics"].get("latency_ms", 0.0)) for r in rows)
    judge_latency = sum(float(r["judge_metrics"].get("latency_ms", 0.0)) for r in rows)
    tokens = {"prompt": 0, "completion": 0, "cache_hit": 0, "cache_miss": 0}
    jtokens = {"prompt": 0, "completion": 0, "cache_hit": 0, "cache_miss": 0}
    for r in rows:
        for key in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens"):
            short = key.removesuffix("_tokens")
            tokens[short] += int(r["gen_metrics"].get(key, 0))
            jtokens[short] += int(r["judge_metrics"].get(key, 0))
    cost = compute_cost_cny(
        cache_hit_tokens=tokens["cache_hit"] + jtokens["cache_hit"],
        cache_miss_tokens=tokens["cache_miss"] + jtokens["cache_miss"],
        completion_tokens=tokens["completion"] + jtokens["completion"],
    )
    return {
        "rows": len(rows),
        "latency_gen_ms": round(gen_latency, 1),
        "latency_judge_ms": round(judge_latency, 1),
        "tokens_gen": tokens,
        "tokens_judge": jtokens,
        "cost_cny": round(cost, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=2, help="每用例重复次数（量化噪声）")
    parser.add_argument("--workers", type=int, default=4, help="并发任务数")
    parser.add_argument("--out", default=None, help="逐行 JSONL 输出路径（人工抽检用）")
    parser.add_argument("--cases", default=None, help="逗号分隔的 case_id 子集（调试用）")
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("（未检测到 DEEPSEEK_API_KEY：角色与评审都用 mock，评分为占位值）")
    provider = _provider()
    judge = _provider()
    runtimes = {"deepseek": DeepSeekRuntime(provider), "claude": ClaudeRuntime(provider), "chatgpt": ChatGPTRuntime(provider)}
    cases = REGRESSION_CASES
    if args.cases:
        wanted = {item.strip() for item in args.cases.split(",") if item.strip()}
        cases = [case for case in REGRESSION_CASES if case.case_id in wanted]

    tasks = []
    for repeat in range(args.repeats):
        for case in cases:
            tasks.append(("A", None, case, repeat))
            tasks.append(("B", None, case, repeat))
            tasks.append(("C", None, case, repeat))

    def _run(task) -> dict:
        arm, _, case, repeat = task
        if arm == "A":
            return _arm_a_case(runtimes, judge, case, repeat)
        return _arm_bc_case(arm, provider, judge, case, repeat)

    print(f"== 用例 {len(cases)} × 重复 {args.repeats} × 3 臂 = {len(tasks)} 次生成+评审（workers={args.workers}） ==")
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(_run, tasks):
            rows.append(row)
    rows.sort(key=lambda r: (r["arm"], r["case"].case_id, r["repeat"]))

    by_arm: dict[str, list[dict]] = {arm: [r for r in rows if r["arm"] == arm] for arm in ARMS}
    print("\n== 维度统计（mean ± std，n=用例×重复） ==")
    for arm in ARMS:
        lines = []
        for dim in DIMENSIONS:
            stats = _stats([r["scores"][dim] for r in by_arm[arm]])
            lines.append(f"{dim}={stats['mean']:.2f}±{stats['std'] or 0:.2f}")
        print(f"  Arm {arm}: " + "  ".join(lines))
    print("\n== 臂间分差 vs 合并标准差（诚实口径：|Δ| < pooled std 即噪声内） ==")
    for dim in DIMENSIONS:
        a = _stats([r["scores"][dim] for r in by_arm["A"]])
        b = _stats([r["scores"][dim] for r in by_arm["B"]])
        c = _stats([r["scores"][dim] for r in by_arm["C"]])
        pooled = statistics.fmean([x for x in (a["std"], b["std"], c["std"]) if x is not None]) if any(x is not None for x in (a["std"], b["std"], c["std"])) else None
        d_ba = b["mean"] - a["mean"]
        d_cb = c["mean"] - b["mean"]
        noise = f"pooled_std={pooled:.2f}" if pooled is not None else "std=N/A（单次）"
        print(f"  {dim:12s} A={a['mean']:.2f} B={b['mean']:.2f} C={c['mean']:.2f}  ΔB-A={d_ba:+.2f} ΔC-B={d_cb:+.2f}  ({noise})")
    print("\n== 成本与延迟（docs/21 §3 占位价格口径） ==")
    for arm in ARMS:
        m = _arm_metrics(by_arm[arm])
        print(f"  Arm {arm}: rows={m['rows']} 生成延迟={m['latency_gen_ms']}ms 评审延迟={m['latency_judge_ms']}ms 成本≈¥{m['cost_cny']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps({
                    "arm": row["arm"],
                    "case_id": row["case"].case_id,
                    "character_id": row["case"].character_id,
                    "focus": row["case"].focus,
                    "repeat": row["repeat"],
                    "player_message": row["case"].player_message,
                    "dialogue": row["dialogue"],
                    "scores": row["scores"],
                    "gen_metrics": row["gen_metrics"],
                    "judge_metrics": row["judge_metrics"],
                }, ensure_ascii=False) + "\n")
        print(f"\n逐行 JSONL 已写入 {args.out}（scripts/eval_human_review.py 可导出人工抽检样本）")

    red_team(SemanticConsistencyChecker(provider))
    return 0


if __name__ == "__main__":
    sys.exit(main())
