"""P0-2 runner: version runs, aggregation, divergence, review export.

Deterministic and network-free: a fake provider serves fixed dialogues and a
fake judge serves fixed scores, so the harness mechanics are fully exercised
without an API key.
"""

from __future__ import annotations

import json

from app.eval.trial.cases import TRIAL_EVAL_CASES
from app.eval.trial.runner import (
    divergence_rows,
    export_review_csv,
    hard_rule_stats,
    judge_stats,
    metrics_summary,
    render_report,
    row_to_dict,
    run_trial_eval,
)
from app.providers.base import LLMProvider


class _FakeProvider(LLMProvider):
    def __init__(self, dialogue: str) -> None:
        self._dialogue = dialogue

    def complete(self, **kwargs) -> str:
        return self._dialogue


_GOOD_SCORES = json.dumps({
    "relevance": 0.8,
    "naturalness": 0.7,
    "persona": 0.9,
    "reasons": {"relevance": "ok", "naturalness": "ok", "persona": "ok"},
})


def _chat_cases():
    return [case for case in TRIAL_EVAL_CASES if case.surface == "chat"][:4]


def test_run_chat_rows_record_dialogue_checks_and_scores():
    provider = _FakeProvider("……我不记得了，先承认。奶茶好甜。")
    rows = run_trial_eval(provider, _FakeProvider(_GOOD_SCORES),
                          cases=_chat_cases(), repeats=1)
    versions = sorted({row.version for row in rows})
    assert versions == ["v1", "v2"]
    for row in rows:
        assert row.dialogue == "……我不记得了，先承认。奶茶好甜。"
        assert row.checks, "every chat case must carry check results"
        assert row.scores["relevance"] == 0.8
        assert not row.error


def test_run_deduction_rows_cover_legacy_and_revised():
    deduction = [case for case in TRIAL_EVAL_CASES if case.surface == "deduction"]
    rows = run_trial_eval(_FakeProvider(""), _FakeProvider(_GOOD_SCORES),
                          cases=deduction, repeats=1)
    assert {row.version for row in rows} == {"legacy", "revised"}
    assert len(rows) == len(deduction) * 2


def test_divergence_rows_are_exactly_the_eight_rule_changes():
    rows = run_trial_eval(_FakeProvider(""), _FakeProvider(_GOOD_SCORES), repeats=1)
    diverged = divergence_rows(rows)
    assert {row.case.case_id for row in diverged} == {
        "ded-neg-01", "ded-neg-02", "ded-neg-03",
        "ded-neg-04", "ded-neg-05", "ded-neg-06",
        "ded-eq-05", "ded-eq-06",
    }


def test_hard_rule_stats_aggregate_per_version_and_split():
    rows = run_trial_eval(_FakeProvider(""), _FakeProvider(_GOOD_SCORES), repeats=1)
    tune = hard_rule_stats(rows, surface="chat", version="v1", split="tune")
    holdout = hard_rule_stats(rows, surface="chat", version="v1", split="holdout")
    expected = sum(len(case.checks) for case in TRIAL_EVAL_CASES if case.surface == "chat")
    assert tune["total"] + holdout["total"] == expected
    for stats in (tune, holdout):
        assert 0 <= stats["pass"] <= stats["total"]


def test_judge_stats_and_metrics_summary_are_well_formed():
    rows = run_trial_eval(_FakeProvider("你好"), _FakeProvider(_GOOD_SCORES),
                          cases=_chat_cases(), repeats=2)
    stats = judge_stats(rows, version="v1")
    assert stats["relevance"]["mean"] == 0.8
    assert stats["relevance"]["n"] == 4 * 2
    metrics = metrics_summary(rows, version="v1")
    assert metrics["rows"] == 8


def test_render_report_mentions_environment_and_both_surfaces():
    provider = _FakeProvider("……")
    rows = run_trial_eval(provider, _FakeProvider(_GOOD_SCORES), repeats=1)
    text = render_report(rows, provider)
    assert "判定面" in text and "聊天面" in text
    assert "分歧用例" in text and "8 条" in text
    assert "_FakeProvider" in text


def test_row_to_dict_carries_the_p02_record_fields():
    rows = run_trial_eval(_FakeProvider("……"), _FakeProvider(_GOOD_SCORES),
                          cases=_chat_cases()[:1], repeats=1)
    payload = row_to_dict(rows[0])
    for key in ("version", "case_id", "player_message", "evidence_ids",
                "expected", "dialogue", "checks", "scores",
                "gen_metrics", "judge_metrics"):
        assert key in payload


def test_export_review_csv_writes_rows_and_rubric(tmp_path):
    rows = run_trial_eval(_FakeProvider("……"), _FakeProvider(_GOOD_SCORES),
                          cases=_chat_cases(), repeats=1)
    out = tmp_path / "review.csv"
    count = export_review_csv(rows, str(out))
    assert count == len(rows)
    assert out.exists()
    assert (tmp_path / "review.csv-rubric.md").exists()
    text = out.read_text(encoding="utf-8-sig")
    assert "overall_correct" in text.splitlines()[0]
