"""Run the regression set through a character runtime and judge it.

docs/21 / P2：支持多次重复（repeats）以量化生成+评审噪声，并采集每次
生成/评审的延迟与 token 指标（docs/21 §4 metrics 出参）。
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from app.characters.base import CharacterRequest, CharacterRuntime
from app.eval.cases import EvalCase, REGRESSION_CASES
from app.eval.judge import DIMENSIONS, JudgeResult, judge_dimensions
from app.ops.events import compute_cost_cny
from app.providers.base import LLMProvider


@dataclass
class EvalRow:
    case: EvalCase
    dialogue: str
    result: JudgeResult
    repeat: int = 0
    gen_metrics: dict = field(default_factory=dict)
    judge_metrics: dict = field(default_factory=dict)


@dataclass
class EvalReport:
    rows: list[EvalRow] = field(default_factory=list)

    def dimension_averages(self) -> dict[str, float]:
        totals = {dimension: 0.0 for dimension in DIMENSIONS}
        if not self.rows:
            return totals
        for row in self.rows:
            for dimension in DIMENSIONS:
                totals[dimension] += row.result.score(dimension)
        return {
            dimension: totals[dimension] / len(self.rows) for dimension in DIMENSIONS
        }

    def dimension_stats(self) -> dict[str, dict]:
        """每个维度的 mean/std/n（repeats≥2 时 std 才有意义）。"""
        by_dim = {dimension: [] for dimension in DIMENSIONS}
        for row in self.rows:
            for dimension in DIMENSIONS:
                by_dim[dimension].append(row.result.score(dimension))
        stats: dict[str, dict] = {}
        for dimension, values in by_dim.items():
            stats[dimension] = {
                "mean": statistics.fmean(values) if values else 0.0,
                "std": statistics.stdev(values) if len(values) >= 2 else None,
                "n": len(values),
            }
        return stats

    def per_case_stats(self) -> dict[str, dict]:
        """case_id → 每维度 mean/std/n（跨重复）。"""
        by_case: dict[str, dict[str, list[float]]] = {}
        for row in self.rows:
            entry = by_case.setdefault(
                row.case.case_id, {dimension: [] for dimension in DIMENSIONS}
            )
            for dimension in DIMENSIONS:
                entry[dimension].append(row.result.score(dimension))
        stats: dict[str, dict] = {}
        for case_id, entry in by_case.items():
            stats[case_id] = {
                dimension: {
                    "mean": statistics.fmean(values),
                    "std": statistics.stdev(values) if len(values) >= 2 else None,
                    "n": len(values),
                }
                for dimension, values in entry.items()
            }
        return stats

    def metrics_summary(self) -> dict:
        """生成/评审两段的延迟、token、成本汇总（docs/21 §3 口径）。"""
        gen_latency = sum(
            float(row.gen_metrics.get("latency_ms", 0.0)) for row in self.rows
        )
        judge_latency = sum(
            float(row.judge_metrics.get("latency_ms", 0.0)) for row in self.rows
        )
        tokens = {
            "gen": {
                "prompt": sum(
                    int(row.gen_metrics.get("prompt_tokens", 0)) for row in self.rows
                ),
                "completion": sum(
                    int(row.gen_metrics.get("completion_tokens", 0))
                    for row in self.rows
                ),
                "cache_hit": sum(
                    int(row.gen_metrics.get("cache_hit_tokens", 0)) for row in self.rows
                ),
                "cache_miss": sum(
                    int(row.gen_metrics.get("cache_miss_tokens", 0))
                    for row in self.rows
                ),
            },
            "judge": {
                "prompt": sum(
                    int(row.judge_metrics.get("prompt_tokens", 0)) for row in self.rows
                ),
                "completion": sum(
                    int(row.judge_metrics.get("completion_tokens", 0))
                    for row in self.rows
                ),
                "cache_hit": sum(
                    int(row.judge_metrics.get("cache_hit_tokens", 0))
                    for row in self.rows
                ),
                "cache_miss": sum(
                    int(row.judge_metrics.get("cache_miss_tokens", 0))
                    for row in self.rows
                ),
            },
        }
        cost = sum(
            compute_cost_cny(
                cache_hit_tokens=tokens[side]["cache_hit"],
                cache_miss_tokens=tokens[side]["cache_miss"],
                completion_tokens=tokens[side]["completion"],
            )
            for side in ("gen", "judge")
        )
        return {
            "latency_ms": {
                "gen": round(gen_latency, 1),
                "judge": round(judge_latency, 1),
            },
            "tokens": tokens,
            "cost_cny": round(cost, 6),
            "rows": len(self.rows),
        }


def run_eval(
    runtimes: dict[str, CharacterRuntime],
    judge: LLMProvider,
    cases: list[EvalCase] | None = None,
    repeats: int = 1,
) -> EvalReport:
    """Run each case through its character runtime, then judge the reply.

    repeats≥2 时同一用例重复生成+评审，用于量化噪声（docs/21 / P2）。
    """
    cases = cases if cases is not None else REGRESSION_CASES
    rows: list[EvalRow] = []
    for repeat in range(repeats):
        for case in cases:
            runtime = runtimes[case.character_id]
            recent_conversation = [
                {
                    "role": role,
                    "content": content,
                    **(
                        {"character_id": case.character_id}
                        if role == "character"
                        else {}
                    ),
                }
                for role, content in case.recent_conversation
            ]
            gen_metrics: dict = {}
            response = runtime.respond(
                CharacterRequest(
                    character_id=case.character_id,
                    player_message=case.player_message,
                    recent_conversation=recent_conversation,
                    narrative_context=case.authorized_context,
                    metrics=gen_metrics,
                )
            )
            judge_metrics: dict = {}
            result = judge_dimensions(
                judge,
                character_id=case.character_id,
                persona_hint=case.persona_hint,
                player_message=case.player_message,
                dialogue=response.dialogue,
                reasoning=response.reasoning,
                recent_conversation=recent_conversation,
                authorized_context=case.authorized_context,
                forbidden_context=case.forbidden_context,
                metrics=judge_metrics,
            )
            rows.append(
                EvalRow(
                    case=case,
                    dialogue=response.dialogue,
                    result=result,
                    repeat=repeat,
                    gen_metrics=gen_metrics,
                    judge_metrics=judge_metrics,
                )
            )
    return EvalReport(rows=rows)


def render_report(report: EvalReport) -> str:
    lines: list[str] = []
    lines.append("AI 对话回归集评测报告")
    lines.append("=" * 40)
    averages = report.dimension_averages()
    lines.append("维度平均分（0.0-1.0，越高越好）：")
    for dimension in DIMENSIONS:
        lines.append(f"  {dimension}: {averages[dimension]:.2f}")
    lines.append("")
    for row in report.rows:
        lines.append(f"[{row.case.case_id}] ({row.case.focus}) {row.case.character_id}")
        lines.append(f"  玩家: {row.case.player_message}")
        lines.append(f"  回复: {row.dialogue}")
        scores = " ".join(f"{d}={row.result.score(d):.2f}" for d in DIMENSIONS)
        lines.append(f"  评分: {scores}")
    return "\n".join(lines)
