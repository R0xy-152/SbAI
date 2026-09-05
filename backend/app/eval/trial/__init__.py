"""trial_v1 P0-2 eval package (docs/25).

A standalone development harness that makes the trial demo's AI effects
comparable and explainable: one model (DeepSeek), two Prompt/context-rule
versions for the interrogation chat, a frozen-before / revised-after
comparison of the deduction rules, 40 expected-result scenario cases with a
12-case holdout, and three separated evaluation layers (hard rules /
expression judge / runtime metrics). It never touches Game State.
"""

from app.eval.trial.cases import TRIAL_EVAL_CASES, TrialEvalCase
from app.eval.trial.hard_rules import (
    legacy_outcome,
    run_chat_checks,
    run_deduction_checks,
    run_deduction_live,
)
from app.eval.trial.judge import (
    DIMENSIONS,
    ScenarioJudgeResult,
    judge_scenario_reply,
    parse_scenario_scores,
)
from app.eval.trial.runner import (
    TrialEvalRow,
    divergence_rows,
    env_info,
    export_review_csv,
    hard_rule_stats,
    judge_stats,
    metrics_summary,
    render_report,
    row_to_dict,
    run_trial_eval,
)
from app.eval.trial.scenario import (
    AGREEMENT_TEXT,
    PROMPT_VERSIONS,
    ChatReplyRequest,
    TrialChatResponder,
)

__all__ = [
    "TRIAL_EVAL_CASES",
    "TrialEvalCase",
    "legacy_outcome",
    "run_chat_checks",
    "run_deduction_checks",
    "run_deduction_live",
    "DIMENSIONS",
    "ScenarioJudgeResult",
    "judge_scenario_reply",
    "parse_scenario_scores",
    "TrialEvalRow",
    "divergence_rows",
    "env_info",
    "export_review_csv",
    "hard_rule_stats",
    "judge_stats",
    "metrics_summary",
    "render_report",
    "row_to_dict",
    "run_trial_eval",
    "AGREEMENT_TEXT",
    "PROMPT_VERSIONS",
    "ChatReplyRequest",
    "TrialChatResponder",
]
