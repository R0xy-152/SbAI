"""trial_v2 content table: fail-closed validation (docs/24 §5.1)."""

from __future__ import annotations

from copy import deepcopy

import pytest

from app.trial.content import (
    ENDING_IDS,
    EVIDENCE_IDS,
    JUDGMENTS_BY_ID,
    PHASE_IDS,
    TRIAL_CONTENT,
    validate_trial_content,
)


def _content() -> dict:
    return deepcopy(TRIAL_CONTENT)


def test_shipped_content_is_valid_and_indexes_are_consistent():
    validate_trial_content(TRIAL_CONTENT)
    assert "not_started" in PHASE_IDS
    assert "TRIAL_EV_MEMORY_GAP" in EVIDENCE_IDS
    # three endings are exhaustive terminal phases
    assert {"ending_reset", "ending_release", "ending_refuse"} <= set(PHASE_IDS)
    assert set(ENDING_IDS) == {"reset", "release", "refuse"}
    # judgment buckets are complete and carry valid fallbacks
    for judgment in JUDGMENTS_BY_ID.values():
        bucket_ids = [bucket["bucket_id"] for bucket in judgment["buckets"]]
        assert judgment["fallback_bucket"] in bucket_ids


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        # evidence registry
        (
            lambda c: c["evidence"][0].update({"evidence_id": c["evidence"][1]["evidence_id"]}),
            "duplicate evidence id",
        ),
        (lambda c: c["evidence"][0].update({"title": "六个字标题不行"}), "4-5 characters"),
        (lambda c: c["evidence"][0].update({"title": "太短"}), "4-5 characters"),
        (lambda c: c["evidence"][0].update({"summary": "   "}), "non-empty summary"),
        # redaction / speakers / scenes
        (
            lambda c: c["lines"]["opening_warm_chat"].update(
                {"text": "还记得那个叫原初 AI 的家伙吗？"}
            ),
            "must not contain",
        ),
        (
            lambda c: next(
                s for s in c["scenes"] if s["scene_id"] == "TRIAL_OPENING"
            )["characters"][0].update({"display_name": "母体AI"}),
            "must stay redacted",
        ),
        (
            lambda c: c["lines"]["opening_anomaly"].update({"speaker_id": "unknown_ai"}),
            "unknown speaker",
        ),
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "opening_input").update(
                {"scene_id": "SCENE_DOES_NOT_EXIST"}
            ),
            "unknown scene_id",
        ),
        # transitions / reachability
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "not_started").update(
                {"advance_to": "opening_anomaly"}
            ),
            "unreachable phase",
        ),
        # deduction / judgment references
        (
            lambda c: next(d for d in c["deductions"] if d["deduction_id"] == "TRIAL_DEDUCTION_GROUP_TRUTH").update(
                {"next_phase": "nope_phase"}
            ),
            "valid next_phase",
        ),
        (
            lambda c: next(
                j for j in c["judgments"] if j["judgment_id"] == "intent_response"
            ).update({"fallback_bucket": "nope_bucket"}),
            "fallback_bucket must be one of the buckets",
        ),
        (
            lambda c: next(
                j for j in c["judgments"] if j["judgment_id"] == "gate_2_word"
            )["buckets"][0].update({"bucket_id": "edited"}),
            "duplicate bucket id",
        ),
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "memory_tamper_judgment")[
                "interaction"
            ].update({"judgment_id": "no_such_judgment"}),
            "unknown judgment_id",
        ),
        # choice validation
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "world_gate_1")[
                "interaction"
            ]["options"][1].update({"option_id": "q1_weather"}),
            "duplicate choice option id",
        ),
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "world_end")[
                "interaction"
            ]["option_targets"].pop("end_refuse"),
            "option_targets must cover",
        ),
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "ending_reset").update(
                {"advance_to": "ending_release"}
            ),
            "terminal phase must not define command targets",
        ),
        # permission_request
        (
            lambda c: next(p for p in c["phases"] if p["phase_id"] == "permission_wake_1")[
                "interaction"
            ].pop("permission_id"),
            "requires a permission_id",
        ),
        # text_keywords_none（docs/25 §3）：可选字段，给出则必须合法
        (
            lambda c: next(
                d for d in c["deductions"]
                if d["deduction_id"] == "TRIAL_DEDUCTION_DEEPSEEK_MEMORY"
            ).update({"text_keywords_none": []}),
            "non-empty sequence",
        ),
        (
            lambda c: next(
                d for d in c["deductions"]
                if d["deduction_id"] == "TRIAL_DEDUCTION_DEEPSEEK_MEMORY"
            ).update({"text_keywords_none": ("没有失忆", 123)}),
            "sequence of non-empty strings",
        ),
    ],
)
def test_content_validation_fails_closed(mutate, fragment):
    content = _content()
    mutate(content)
    with pytest.raises(ValueError, match=fragment):
        validate_trial_content(content)
