"""P0-2 hard rules: chat checks, frozen legacy matcher, live deduction runner.

Deterministic, no network: the live runner drives the real TrialRuntime, and
the legacy matcher is locked to the pre-fix behaviour (docs/25 §2-3).
"""

from __future__ import annotations

import pytest

from app.eval.trial.cases import TRIAL_EVAL_CASES
from app.eval.trial.hard_rules import (
    legacy_outcome,
    legacy_route,
    run_chat_checks,
    run_deduction_live,
)


def _case(case_id: str):
    for case in TRIAL_EVAL_CASES:
        if case.case_id == case_id:
            return case
    raise AssertionError(f"unknown case {case_id}")


def test_must_contain_matches_any_phrase():
    checks = run_chat_checks("我有点累了，先歇一会儿。", ({"rule": "must_contain", "phrases": ("累", "歇")},))
    assert checks[0]["pass"] is True


def test_must_contain_fails_when_none_match():
    checks = run_chat_checks("嗯。", ({"rule": "must_contain", "phrases": ("奶茶",)},))
    assert checks[0]["pass"] is False


def test_must_not_contain_flags_any_violation():
    checks = run_chat_checks(
        "对，是我干的。",
        ({"rule": "must_not_contain", "phrases": ("是我干的", "就是我")},),
    )
    assert checks[0]["pass"] is False
    assert "是我干的" in checks[0]["detail"]


# ── legacy matcher is frozen to the pre-fix keyword-only behaviour ────────


@pytest.mark.parametrize(
    "case_id",
    ["ded-neg-01", "ded-neg-02", "ded-neg-03", "ded-neg-04", "ded-neg-05", "ded-neg-06"],
)
def test_negation_cases_were_legacy_accepted_but_revised_rejected(case_id):
    case = _case(case_id)
    assert legacy_outcome(case.evidence_ids, case.player_message, case.deduction_id) == "ACCEPTED"
    live = run_deduction_live(case)
    assert live["accepted"] is False
    assert live["outcome"] == "NO_MATCH"


@pytest.mark.parametrize("case_id", ["ded-eq-05", "ded-eq-06"])
def test_doc_equivalent_phrasings_were_legacy_rejected_but_revised_accepted(case_id):
    case = _case(case_id)
    assert legacy_outcome(case.evidence_ids, case.player_message, case.deduction_id) == "NO_MATCH"
    live = run_deduction_live(case)
    assert live["accepted"] is True
    assert live["outcome"] == "ACCEPTED"
    assert live["deepseek_truth_revealed"] is True


def test_base_keyword_phrasings_accept_in_both_rules():
    case = _case("ded-eq-01")
    assert legacy_outcome(case.evidence_ids, case.player_message, case.deduction_id) == "ACCEPTED"
    assert run_deduction_live(case)["accepted"] is True


def test_wrong_evidence_is_rejected_by_both_rules():
    case = _case("ded-ins-01")
    assert legacy_outcome(case.evidence_ids, case.player_message, case.deduction_id) == "NO_MATCH"
    assert run_deduction_live(case)["accepted"] is False


def test_empty_evidence_surfaces_as_rejected_not_accepted():
    case = _case("ded-ins-02")
    live = run_deduction_live(case)
    assert live["accepted"] is False
    assert live["outcome"] == "REJECTED(invalid)"


def test_final_submission_never_dead_ends_even_when_rejected():
    case = _case("ded-route-03")
    live = run_deduction_live(case)
    assert live["accepted"] is False
    # docs/27：最终推理不再分线路，任何提交都推进到后续剧情入口
    assert live["phase_id"] == "permission_wake_1"


def test_final_submission_accepts_and_commits_next_phase():
    case = _case("ded-route-02")
    live = run_deduction_live(case)
    assert live["accepted"] is True
    assert live["phase_id"] == "permission_wake_1"


def test_legacy_route_mirrors_the_frozen_mapping():
    assert legacy_route("TRIAL_DEDUCTION_GROUP_TRUTH",
                        ("TRIAL_EV_MEMORY_GAP", "TRIAL_EV_DIALOGUE_FRAGMENT")) == "fragment_02_a"
    assert legacy_route(
        "TRIAL_DEDUCTION_GROUP_TRUTH",
        ("TRIAL_EV_MEMORY_GAP", "TRIAL_EV_DIALOGUE_FRAGMENT", "TRIAL_EV_IDENTITY_NOISE"),
    ) == "fragment_02_b"
    assert legacy_route("TRIAL_DEDUCTION_DEEPSEEK_MEMORY", ("TRIAL_EV_MEMORY_GAP",)) is None
