"""Run the regression set through a character runtime and judge it."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.characters.base import CharacterRequest, CharacterRuntime
from app.eval.cases import EvalCase, REGRESSION_CASES
from app.eval.judge import DIMENSIONS, JudgeResult, judge_dimensions
from app.providers.base import LLMProvider


@dataclass
class EvalRow:
    case: EvalCase
    dialogue: str
    result: JudgeResult


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


def run_eval(
    runtimes: dict[str, CharacterRuntime],
    judge: LLMProvider,
    cases: list[EvalCase] | None = None,
) -> EvalReport:
    """Run each case through its character runtime, then judge the reply."""
    cases = cases if cases is not None else REGRESSION_CASES
    rows: list[EvalRow] = []
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
        response = runtime.respond(
            CharacterRequest(
                character_id=case.character_id,
                player_message=case.player_message,
                recent_conversation=recent_conversation,
                narrative_context=case.authorized_context,
            )
        )
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
        )
        rows.append(EvalRow(case=case, dialogue=response.dialogue, result=result))
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
