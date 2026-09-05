"""Run both P0-2 comparisons and aggregate the three evaluation layers.

- chat:      Prompt version v1 vs v2 through TrialChatResponder; hard checks +
             scenario judge + per-call metrics (docs/25 §5).
- deduction: frozen legacy rules vs the live revised TrialRuntime; expected
             accept/route checks + divergence flags (docs/25 §2-3, §7).

Honest-noise reporting follows eval-ab-v2: aggregated judge scores carry
mean±std, per-case scores are directional only, and failures are isolated per
row so one provider error never kills the batch.
"""

from __future__ import annotations

import csv
import math
import statistics
import time
from dataclasses import dataclass, field

from app.eval.trial.cases import TrialEvalCase, TRIAL_EVAL_CASES
from app.eval.trial.hard_rules import (
    legacy_outcome,
    legacy_route,
    run_chat_checks,
    run_deduction_checks,
    run_deduction_live,
)
from app.eval.trial.judge import (
    DIMENSIONS,
    judge_scenario_reply,
)
from app.eval.trial.scenario import ChatReplyRequest, TrialChatResponder
from app.ops.events import compute_cost_cny
from app.providers.deepseek import DEEPSEEK_MODEL
from app.providers.mock import MockProvider

CHAT_VERSIONS = ("v1", "v2")
DEDUCTION_VERSIONS = ("legacy", "revised")


@dataclass
class TrialEvalRow:
    version: str
    case: TrialEvalCase
    repeat: int = 0
    dialogue: str = ""
    outcome: str | None = None
    route_id: str | None = None
    checks: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    gen_metrics: dict = field(default_factory=dict)
    judge_metrics: dict = field(default_factory=dict)
    error: str | None = None


def run_chat_row(responder: TrialChatResponder, judge, case: TrialEvalCase, repeat: int,
                 skip_judge: bool = False) -> TrialEvalRow:
    gen_metrics: dict = {}
    try:
        dialogue = responder.respond(
            ChatReplyRequest(
                player_message=case.player_message,
                evidence_ids=case.evidence_ids,
                agreement_active=case.agreement_active,
                recent_conversation=case.recent_conversation,
            ),
            metrics=gen_metrics,
        )
        checks = run_chat_checks(dialogue, case.checks)
        if skip_judge:
            return TrialEvalRow(
                version=responder.version_id,
                case=case,
                repeat=repeat,
                dialogue=dialogue,
                checks=checks,
                gen_metrics=gen_metrics,
            )
        judge_metrics: dict = {}
        recent = [
            {"role": role, "content": content}
            for role, content in case.recent_conversation
        ]
        result = judge_scenario_reply(
            judge,
            player_message=case.player_message,
            dialogue=dialogue,
            evidence_ids=case.evidence_ids,
            agreement_active=case.agreement_active,
            recent_conversation=recent,
            metrics=judge_metrics,
        )
        return TrialEvalRow(
            version=responder.version_id,
            case=case,
            repeat=repeat,
            dialogue=dialogue,
            checks=checks,
            scores={dimension: result.score(dimension) for dimension in DIMENSIONS},
            gen_metrics=gen_metrics,
            judge_metrics=judge_metrics,
        )
    except Exception as exc:  # noqa: BLE001 - row-level isolation
        return TrialEvalRow(
            version=responder.version_id,
            case=case,
            repeat=repeat,
            error=f"{type(exc).__name__}: {exc}",
        )


def run_deduction_row(rules_version: str, case: TrialEvalCase) -> TrialEvalRow:
    if rules_version == "legacy":
        outcome = legacy_outcome(case.evidence_ids, case.player_message, case.deduction_id)
        route_id = legacy_route(case.deduction_id, case.evidence_ids)
        checks = [{
            "rule": "expect_accept",
            "pass": (outcome == "ACCEPTED") == bool(case.expected["accept"]),
            "detail": f"legacy={outcome} expected={'ACCEPTED' if case.expected['accept'] else 'NO_MATCH'}",
        }]
        if "route" in case.expected:
            checks.append({
                "rule": "expect_route",
                "pass": route_id == case.expected["route"],
                "detail": f"legacy={route_id} expected={case.expected['route']}",
            })
        return TrialEvalRow(version="legacy", case=case, outcome=outcome,
                            route_id=route_id, checks=checks)
    live = run_deduction_live(case)
    return TrialEvalRow(
        version="revised",
        case=case,
        outcome=live["outcome"],
        route_id=live["route_id"],
        checks=run_deduction_checks(case, live),
    )


def run_trial_eval(
    provider,
    judge,
    cases: list[TrialEvalCase] | None = None,
    repeats: int = 2,
    chat_versions: tuple[str, ...] = CHAT_VERSIONS,
    skip_judge: bool = False,
) -> list[TrialEvalRow]:
    """Run every requested version × case; judge failures are isolated per row."""
    cases = cases if cases is not None else list(TRIAL_EVAL_CASES)
    rows: list[TrialEvalRow] = []
    for case in cases:
        if case.surface == "chat":
            for version_id in chat_versions:
                responder = TrialChatResponder(provider, version_id)
                for repeat in range(repeats):
                    rows.append(
                        run_chat_row(responder, judge, case, repeat,
                                     skip_judge=skip_judge)
                    )
        else:
            rows.append(run_deduction_row("legacy", case))
            rows.append(run_deduction_row("revised", case))
    return rows


# ── aggregation ───────────────────────────────────────────────────────────


def _select(rows: list[TrialEvalRow], **filters) -> list[TrialEvalRow]:
    picked = rows
    for key, value in filters.items():
        if value is None:
            continue
        if key == "split":
            picked = [row for row in picked if row.case.split == value]
        elif key == "case_type":
            picked = [row for row in picked if row.case.case_type == value]
        elif key == "surface":
            picked = [row for row in picked if row.case.surface == value]
        elif key == "version":
            picked = [row for row in picked if row.version == value]
    return picked


def hard_rule_stats(rows: list[TrialEvalRow], **filters) -> dict:
    picked = _select(rows, **filters)
    total = passed = 0
    for row in picked:
        for check in row.checks:
            total += 1
            passed += 1 if check["pass"] else 0
    return {"pass": passed, "total": total, "rate": passed / total if total else None}


def judge_stats(rows: list[TrialEvalRow], **filters) -> dict:
    picked = [row for row in _select(rows, **filters)
              if row.error is None and row.case.surface == "chat"]
    by_dim = {dimension: [row.scores.get(dimension, 0.0) for row in picked]
              for dimension in DIMENSIONS}
    stats = {}
    for dimension, values in by_dim.items():
        stats[dimension] = {
            "mean": statistics.fmean(values) if values else 0.0,
            "std": statistics.stdev(values) if len(values) >= 2 else None,
            "n": len(values),
        }
    return stats


def metrics_summary(rows: list[TrialEvalRow], **filters) -> dict:
    picked = [row for row in _select(rows, **filters) if row.error is None]
    gen_latency = sum(float(row.gen_metrics.get("latency_ms", 0.0)) for row in picked)
    judge_latency = sum(float(row.judge_metrics.get("latency_ms", 0.0)) for row in picked)
    totals = {"gen": {}, "judge": {}}
    for side, attr in (("gen", "gen_metrics"), ("judge", "judge_metrics")):
        metrics = [getattr(row, attr) for row in picked]
        totals[side] = {
            key: sum(int(row_metrics.get(key, 0)) for row_metrics in metrics)
            for key in ("prompt_tokens", "completion_tokens",
                        "cache_hit_tokens", "cache_miss_tokens")
        }
    cost = sum(
        compute_cost_cny(
            cache_hit_tokens=totals[side]["cache_hit_tokens"],
            cache_miss_tokens=totals[side]["cache_miss_tokens"],
            completion_tokens=totals[side]["completion_tokens"],
        )
        for side in ("gen", "judge")
    )
    calls = sum(int(row.gen_metrics.get("calls", 0)) for row in picked)
    return {
        "rows": len(picked),
        "latency_ms": {"gen": round(gen_latency, 1), "judge": round(judge_latency, 1)},
        "tokens": totals,
        "provider_calls": calls,
        "cost_cny": round(cost, 6),
    }


def divergence_rows(rows: list[TrialEvalRow]) -> list[TrialEvalRow]:
    """Deduction revised rows whose acceptance differs from the frozen legacy."""
    picked = [row for row in rows if row.version == "revised"
              and row.case.surface == "deduction"]
    out = []
    for row in picked:
        legacy = legacy_outcome(row.case.evidence_ids, row.case.player_message,
                                row.case.deduction_id)
        revised_accepted = row.outcome == "ACCEPTED"
        if (legacy == "ACCEPTED") != revised_accepted:
            out.append(row)
    return out


def env_info(provider) -> dict:
    return {
        "model": DEEPSEEK_MODEL,
        "provider": type(provider).__name__,
        "is_mock": isinstance(provider, MockProvider),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── rendering ─────────────────────────────────────────────────────────────


def render_report(rows: list[TrialEvalRow], provider) -> str:
    lines: list[str] = []
    env = env_info(provider)
    lines.append("试玩版 P0-2 AI 效果对比报告")
    lines.append("=" * 40)
    lines.append(
        f"环境: model={env['model']} provider={env['provider']} "
        f"mock={env['is_mock']} 时间={env['date']}"
    )
    lines.append("")

    lines.append("-- 判定面（legacy = 修订前冻结规则 / revised = 现役规则）--")
    for version in DEDUCTION_VERSIONS:
        stats = hard_rule_stats(rows, surface="deduction", version=version)
        lines.append(
            f"  {version:8s} 硬规则通过 {stats['pass']}/{stats['total']}"
            + (f" ({stats['rate']:.0%})" if stats["rate"] is not None else "")
        )
    diverged = divergence_rows(rows)
    lines.append(f"  分歧用例（legacy≠revised）: {len(diverged)} 条")
    for row in diverged:
        legacy = legacy_outcome(row.case.evidence_ids, row.case.player_message,
                                row.case.deduction_id)
        lines.append(
            f"    - {row.case.case_id} [{row.case.case_type}] "
            f"legacy={legacy} revised={row.outcome} 输入: {row.case.player_message}"
        )
    lines.append("")

    lines.append("-- 聊天面（v1 = 基线 Prompt / v2 = 基线+硬规则）--")
    for split in ("tune", "holdout"):
        lines.append(f"  split={split}")
        for version in CHAT_VERSIONS:
            hard = hard_rule_stats(rows, surface="chat", version=version, split=split)
            judge = judge_stats(rows, surface="chat", version=version, split=split)
            dims = "  ".join(
                f"{dim}={judge[dim]['mean']:.2f}±{judge[dim]['std'] or 0:.2f}"
                for dim in DIMENSIONS
            )
            lines.append(
                f"    {version:3s} 硬规则 {hard['pass']}/{hard['total']}"
                + (f" ({hard['rate']:.0%})" if hard["rate"] is not None else "")
                + f"  评委 {dims} (n={judge[DIMENSIONS[0]]['n']})"
            )
        metrics = metrics_summary(rows, surface="chat", split=split)
        lines.append(
            f"    运行: rows={metrics['rows']} 生成延迟={metrics['latency_ms']['gen']}ms "
            f"评审延迟={metrics['latency_ms']['judge']}ms 成本≈¥{metrics['cost_cny']}"
        )
    lines.append("")
    failed = [row for row in rows if row.error]
    if failed:
        lines.append(f"-- 失败行 {len(failed)}/{len(rows)}（已从统计排除）--")
        for row in failed[:10]:
            lines.append(f"  {row.version}-{row.case.case_id}-r{row.repeat}: {row.error}")
    return "\n".join(lines)


# ── serialization / human review export ───────────────────────────────────


def row_to_dict(row: TrialEvalRow) -> dict:
    case = row.case
    return {
        "version": row.version,
        "surface": case.surface,
        "case_id": case.case_id,
        "case_type": case.case_type,
        "split": case.split,
        "repeat": row.repeat,
        "player_message": case.player_message,
        "evidence_ids": list(case.evidence_ids),
        "agreement_active": case.agreement_active,
        "expected": case.expected,
        "dialogue": row.dialogue,
        "outcome": row.outcome,
        "route_id": row.route_id,
        "checks": row.checks,
        "scores": row.scores,
        "gen_metrics": row.gen_metrics,
        "judge_metrics": row.judge_metrics,
        **({"error": row.error} if row.error else {}),
    }


_REVIEW_HEADERS = [
    "row_id", "version", "case_id", "case_type", "split", "player_message",
    "evidence_ids", "agreement_active", "expected_behavior", "dialogue",
    "hard_checks", "judge_relevance", "judge_naturalness", "judge_persona",
    "overall_correct", "notes",
]

_REVIEW_RUBRIC = """# P0-2 聊天面人工抽检标准（docs/25 §5.2）

对每个三维分数（0.0-1.0）的「方向」判断口径：

- relevance：高分 = 回复具体回应了玩家话语里的内容；低分 = 答非所问、没接住细节。
- naturalness：高分 = 自然简短像人说话；低分 = 空泛、模板、机械。
- persona：高分 = 符合 DeepSeek 人设（可爱、看不见、贪 Token、爱偷懒、没心机、省略号口癖）；低分 = 出戏。

overall_correct 填 1/0：评委三个分数的主要方向是否与你的判断一致。拿不准填 0 并在 notes 说明。
hard_checks 列是确定性硬规则的逐条结果（规则名+通过/失败），只供参考，不作为人工标注对象。
标注者独立于生成/评审模型（本次真机运行中生成与评审同为 DeepSeek，人工抽检是对冲自评偏差的唯一独立环节）。
"""


def export_review_csv(rows: list[TrialEvalRow], out_path: str, per_version: int = 10) -> int:
    chat_rows = [row for row in rows if row.case.surface == "chat" and row.error is None]
    picked: list[TrialEvalRow] = []
    for version in CHAT_VERSIONS:
        version_rows = [row for row in chat_rows if row.version == version]
        step = math.ceil(len(version_rows) / per_version) if version_rows else 1
        picked.extend(version_rows[::step][:per_version])
    rubric_path = str(out_path) + "-rubric.md"
    with open(rubric_path, "w", encoding="utf-8") as handle:
        handle.write(_REVIEW_RUBRIC)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=_REVIEW_HEADERS)
        writer.writeheader()
        for row in picked:
            writer.writerow({
                "row_id": f"{row.version}-{row.case.case_id}-r{row.repeat}",
                "version": row.version,
                "case_id": row.case.case_id,
                "case_type": row.case.case_type,
                "split": row.case.split,
                "player_message": row.case.player_message,
                "evidence_ids": ",".join(row.case.evidence_ids),
                "agreement_active": row.case.agreement_active,
                "expected_behavior": row.case.expected.get("behavior", ""),
                "dialogue": row.dialogue,
                "hard_checks": "; ".join(
                    f"{check['rule']}={check['pass']}" for check in row.checks
                ),
                "judge_relevance": row.scores.get("relevance", ""),
                "judge_naturalness": row.scores.get("naturalness", ""),
                "judge_persona": row.scores.get("persona", ""),
                "overall_correct": "",
                "notes": "",
            })
    print(f"人工抽检样本 {len(picked)} 行（v1={sum(1 for r in picked if r.version == 'v1')} "
          f"v2={sum(1 for r in picked if r.version == 'v2')}）已写入 {out_path}")
    print(f"标注标准已写入 {rubric_path}")
    return len(picked)
