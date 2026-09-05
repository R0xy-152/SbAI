"""P0-2 scenario judge parsing: tolerant, clamped, never raises (docs/25 §5.2)."""

from __future__ import annotations

import json

from app.eval.trial.judge import (
    DIMENSIONS,
    ScenarioJudgeResult,
    judge_scenario_reply,
    parse_scenario_scores,
)
from app.providers.base import LLMProvider


class _FakeJudge(LLMProvider):
    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.system_prompts: list[str] = []
        self.user_prompts: list[str] = []

    def complete(self, **kwargs) -> str:
        self.system_prompts.append(kwargs["system"])
        self.user_prompts.append(kwargs["user"])
        return self._raw


_GOOD = json.dumps({
    "relevance": 0.9,
    "naturalness": 1.5,  # out of range -> clamped to 1.0
    "persona": 0.7,
    "reasons": {"relevance": "ok"},
})


def test_parse_clamps_and_fills_reasons():
    result = parse_scenario_scores(_GOOD)
    assert result.score("relevance") == 0.9
    assert result.score("naturalness") == 1.0
    assert result.score("persona") == 0.7


def test_parse_tolerates_garbage():
    result = parse_scenario_scores("not json at all")
    for dimension in DIMENSIONS:
        assert result.score(dimension) == 0.0


def test_judge_prompt_carries_three_dimensions_and_context():
    judge = _FakeJudge(_GOOD)
    judge_scenario_reply(
        judge,
        player_message="那晚你后来去了哪里？",
        dialogue="……我不记得了，先承认这一点。",
        evidence_ids=(),
        agreement_active=True,
    )
    assert judge.system_prompts, "judge system prompt was not sent"
    for dimension in DIMENSIONS:
        assert dimension in judge.system_prompts[0]
    user = judge.user_prompts[0]
    assert "那晚你后来去了哪里？" in user
    assert "不记得了" in user
    assert "约定" in user


def test_empty_result_is_neutral():
    empty = ScenarioJudgeResult()
    for dimension in DIMENSIONS:
        assert empty.score(dimension) == 0.0
