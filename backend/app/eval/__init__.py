"""Dialogue regression eval (LLM-as-judge).

A standalone quality harness for the "thinking AI" levers: a fixed regression
set of player inputs is run through each character runtime, then each reply is
scored on four dimensions (persona / repetition / fact-leak / template-tone) by
a judge LLM. It never touches Game State — it is a development tool, not part of
the runtime path.
"""

from app.eval.cases import EvalCase, REGRESSION_CASES
from app.eval.judge import DIMENSIONS, JudgeResult, judge_dimensions, parse_judge_scores
from app.eval.report import EvalReport, render_report, run_eval

__all__ = [
    "EvalCase",
    "REGRESSION_CASES",
    "DIMENSIONS",
    "JudgeResult",
    "judge_dimensions",
    "parse_judge_scores",
    "EvalReport",
    "render_report",
    "run_eval",
]
