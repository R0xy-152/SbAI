"""docs/21 / P2：扩展后的评测用例集与重复运行统计（mock，无网络）。"""

from __future__ import annotations

import json

import pytest

from app.characters.base import CharacterResponse, CharacterRuntime
from app.eval.cases import PERSONA_HINTS, REGRESSION_CASES
from app.eval.judge import DIMENSIONS
from app.eval.report import EvalReport, run_eval


class _Runtime(CharacterRuntime):
    character_id = "deepseek"

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="固定回复")


class _FakeJudge:
    supports_metrics = False

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, **kwargs) -> str:
        self.calls += 1
        return json.dumps(
            {
                "persona": 0.9,
                "repetition": 0.8,
                "no_leak": 0.7,
                "anti_template": 0.6,
                "reasons": {},
            }
        )


def test_case_ids_unique_and_stable_prefix():
    ids = [case.case_id for case in REGRESSION_CASES]
    assert len(ids) == len(set(ids)) == 32
    # 原始 8 例的 id 保持不变（历史回归连续性）
    assert ids[:8] == [
        "ds-smalltalk", "ds-lie", "ds-followup", "ds-probe",
        "cl-smalltalk", "cl-lie", "cl-probe", "cl-contradiction",
    ]


def test_case_characters_and_focuses_cover_probes():
    characters = {case.character_id for case in REGRESSION_CASES}
    assert characters == {"deepseek", "claude", "chatgpt"}
    focuses = {case.focus for case in REGRESSION_CASES}
    assert {
        "lie", "followup", "probe", "contradiction", "smalltalk",
        "memory", "continuity", "boundary", "template", "emotion",
    } <= focuses


def test_every_case_has_hint_and_context():
    for case in REGRESSION_CASES:
        assert case.persona_hint == PERSONA_HINTS[case.character_id]
        assert case.authorized_context and case.forbidden_context


def test_run_eval_repeats_produce_stats():
    runtimes = {
        "deepseek": _Runtime(),
        "claude": _Runtime(),
        "chatgpt": _Runtime(),
    }
    report = run_eval(runtimes, _FakeJudge(), repeats=3)
    assert len(report.rows) == 32 * 3
    stats = report.dimension_stats()
    assert stats["persona"]["n"] == 96
    assert stats["persona"]["mean"] == pytest.approx(0.9)
    assert stats["persona"]["std"] == pytest.approx(0.0)
    per_case = report.per_case_stats()
    assert per_case["ds-smalltalk"]["no_leak"]["n"] == 3


def test_metrics_summary_empty_without_provider_metrics():
    report = run_eval(
        {"deepseek": _Runtime(), "claude": _Runtime(), "chatgpt": _Runtime()},
        _FakeJudge(),
        repeats=1,
    )
    summary = report.metrics_summary()
    assert summary["rows"] == 32
    assert summary["latency_ms"]["gen"] == 0.0
    assert summary["cost_cny"] == 0.0


def test_render_report_lists_repeats():
    report = run_eval(
        {"deepseek": _Runtime(), "claude": _Runtime(), "chatgpt": _Runtime()},
        _FakeJudge(),
        repeats=2,
    )
    text = __import__("app.eval.report", fromlist=["render_report"]).render_report(report)
    assert "[ds-smalltalk]" in text
    assert text.count("[ds-smalltalk]") == 2
