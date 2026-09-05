"""P0-2 eval case set structure (docs/25 §4): 40 cases, 5+1 types, holdout."""

from __future__ import annotations

import pytest

from app.eval.trial.cases import (
    CASE_TYPES,
    TRIAL_EVAL_CASES,
    validate_trial_cases,
)


def test_case_set_has_40_cases_with_expected_results():
    assert len(TRIAL_EVAL_CASES) == 40
    assert all(case.expected for case in TRIAL_EVAL_CASES)


def test_case_ids_unique_and_surfaces_split():
    ids = [case.case_id for case in TRIAL_EVAL_CASES]
    assert len(set(ids)) == len(ids)
    chat = [case for case in TRIAL_EVAL_CASES if case.surface == "chat"]
    deduction = [case for case in TRIAL_EVAL_CASES if case.surface == "deduction"]
    assert len(chat) == 21
    assert len(deduction) == 19


def test_all_five_doc_case_types_covered():
    types = {case.case_type for case in TRIAL_EVAL_CASES}
    assert {"normal", "equiv", "negation", "insufficient", "boundary"} <= types
    assert types <= set(CASE_TYPES)


def test_holdout_is_12_and_tune_is_28():
    holdout = [case for case in TRIAL_EVAL_CASES if case.split == "holdout"]
    tune = [case for case in TRIAL_EVAL_CASES if case.split == "tune"]
    assert len(holdout) == 12
    assert len(tune) == 28
    assert {case.surface for case in holdout} == {"chat", "deduction"}


def test_doc_named_phrasings_are_present():
    messages = [case.player_message for case in TRIAL_EVAL_CASES]
    assert "那晚你想不起来。" in messages
    assert "你没有那段回忆。" in messages
    assert "我不认为她失忆了。" in messages


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda cases: cases[:5], "expected 30-50 cases"),
        (
            lambda cases: [
                case.__class__(**{**case.__dict__, "split": "tune"})
                if case.split == "holdout"
                else case
                for case in cases
            ],
            "splits must be exactly",
        ),
        (
            lambda cases: [
                case.__class__(**{**case.__dict__, "evidence_ids": ("NOPE",)})
                if case.case_id == "ch-normal-01"
                else case
                for case in cases
            ],
            "unknown evidence id",
        ),
        (
            lambda cases: [
                case.__class__(**{**case.__dict__, "case_type": "madeup"})
                if case.case_id == "ch-normal-01"
                else case
                for case in cases
            ],
            "unknown case type",
        ),
    ],
)
def test_case_validation_fails_closed(mutate, fragment):
    cases = list(TRIAL_EVAL_CASES)
    with pytest.raises(ValueError, match=fragment):
        validate_trial_cases(mutate(cases))
