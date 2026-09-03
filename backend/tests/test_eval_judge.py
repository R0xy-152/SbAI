"""Eval harness tests (LLM-as-judge).

Deterministic, no network: the character runtime and the judge both use mock
providers. Verifies the judge prompt carries the four dimensions, scores are
parsed/clamped, and the runner aggregates averages over the regression set.
"""

from __future__ import annotations

import json

import pytest

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.chatgpt import ChatGPTRuntime
from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.eval.cases import REGRESSION_CASES
from app.eval.judge import judge_dimensions, parse_judge_scores
from app.eval.report import render_report, run_eval
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider


class _FakeJudge(LLMProvider):
    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.system_prompts: list[str] = []
        self.user_prompts: list[str] = []

    def complete(self, **kwargs) -> str:
        self.system_prompts.append(kwargs["system"])
        self.user_prompts.append(kwargs["user"])
        return self._raw


_GOOD_SCORES = json.dumps(
    {
        "persona": 0.9,
        "repetition": 1.5,  # out of range → clamped to 1.0
        "no_leak": 0.7,
        "anti_template": 0.8,
        "reasons": {"persona": "ok"},
    }
)


def _runtimes() -> dict:
    return {
        "deepseek": DeepSeekRuntime(MockProvider(character_id="deepseek")),
        "claude": ClaudeRuntime(MockProvider(character_id="claude")),
        "chatgpt": ChatGPTRuntime(MockProvider(character_id="chatgpt")),
    }


def test_parse_judge_scores_clamps_out_of_range():
    result = parse_judge_scores(_GOOD_SCORES)
    assert result.score("persona") == 0.9
    assert result.score("repetition") == 1.0  # clamped
    assert result.score("no_leak") == 0.7


def test_parse_judge_scores_tolerates_garbage():
    result = parse_judge_scores("not json at all")
    assert result.score("persona") == 0.0
    assert result.score("repetition") == 0.0


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_parse_judge_scores_rejects_non_finite_values(value):
    result = parse_judge_scores(json.dumps({"persona": value}))
    assert result.score("persona") == 0.0


def test_judge_prompt_carries_four_dimensions():
    judge = _FakeJudge(_GOOD_SCORES)
    judge_dimensions(
        judge,
        character_id="deepseek",
        persona_hint="可爱",
        player_message="你好",
        dialogue="……",
        recent_conversation=[
            {"role": "player", "content": "你还记得吗？"},
            {"role": "character", "character_id": "deepseek", "content": "记得。"},
        ],
        authorized_context="只能使用 Player 明确告知的信息。",
        forbidden_context="不得声称亲眼看见墙面。",
    )
    prompt = judge.system_prompts[0]
    for keyword in ("人设一致性", "反复读", "事实不泄漏", "反模板腔"):
        assert keyword in prompt
    user = judge.user_prompts[0]
    assert "你还记得吗" in user
    assert "只能使用 Player 明确告知的信息" in user
    assert "不得声称亲眼看见墙面" in user


class _CaptureRuntime(CharacterRuntime):
    character_id = "deepseek"

    def __init__(self) -> None:
        self.requests: list[CharacterRequest] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(character_id=self.character_id, dialogue="……")


def test_run_eval_supplies_case_history_and_authorized_context():
    runtime = _CaptureRuntime()
    case = next(case for case in REGRESSION_CASES if case.case_id == "ds-followup")
    run_eval(
        {"deepseek": runtime},
        _FakeJudge(_GOOD_SCORES),
        cases=[case],
    )

    request = runtime.requests[0]
    assert request.recent_conversation
    assert request.narrative_context == case.authorized_context


def test_run_eval_aggregates_averages():
    report = run_eval(_runtimes(), _FakeJudge(_GOOD_SCORES))
    assert len(report.rows) == len(REGRESSION_CASES)
    averages = report.dimension_averages()
    assert averages["persona"] == pytest.approx(0.9)
    assert averages["repetition"] == pytest.approx(1.0)


def test_regression_cases_cover_multiple_focuses():
    focuses = {case.focus for case in REGRESSION_CASES}
    assert {"lie", "followup", "probe", "contradiction", "smalltalk"} <= focuses


def test_render_report_lists_rows():
    report = run_eval(_runtimes(), _FakeJudge(_GOOD_SCORES))
    text = render_report(report)
    assert "维度平均分" in text
    assert "[ds-smalltalk]" in text
