"""trial_v1 content table: fail-closed validation (docs/24 §5.1)."""

from __future__ import annotations

from copy import deepcopy

import pytest

from app.trial.content import (
    TRIAL_CONTENT,
    EVIDENCE_IDS,
    PHASE_IDS,
    ROUTE_IDS,
    validate_trial_content,
)


def _content() -> dict:
    return deepcopy(TRIAL_CONTENT)


def test_shipped_content_is_valid_and_indexes_are_consistent():
    validate_trial_content(TRIAL_CONTENT)
    assert "not_started" in PHASE_IDS
    assert "fragment_02_a" in ROUTE_IDS and "fragment_02_b" in ROUTE_IDS
    assert "TRIAL_EV_MEMORY_GAP" in EVIDENCE_IDS
    # every orbit / terminal phase is covered and the walk ends at handoffs
    assert {"fragment_02_handoff_a", "fragment_02_handoff_b"} <= set(PHASE_IDS)


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
        # deduction / route references
        (
            lambda c: next(d for d in c["deductions"] if d["deduction_id"] == "TRIAL_DEDUCTION_GROUP_TRUTH")[
                "route"
            ].update({"default": "nope_route"}),
            "unknown route",
        ),
        (
            lambda c: c["routes"][0].update({"phase_id": "opening_shatter"}),
            "must target a terminal phase",
        ),
        (
            lambda c: c["routes"][1].update({"phase_id": "fragment_02_handoff_a"}),
            "matching handoff phase",
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
