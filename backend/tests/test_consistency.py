"""Semantic consistency gate tests (defense-in-depth).

The checker is untrusted and fails open (pass); the orchestrator turns a
rejected verdict into a safe fallback. Deterministic (no network): the checker
judge is a mock provider.
"""

from __future__ import annotations

import json

from app.characters.deepseek import DeepSeekRuntime
from app.game.consistency import (
    CONSISTENCY_SYSTEM_PROMPT,
    SemanticConsistencyChecker,
    parse_consistency_verdict,
)
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.providers.base import LLMProvider, ProviderError
from app.providers.mock import MockProvider


def _verdict_json(verdict: str) -> str:
    return json.dumps({"verdict": verdict, "reason": "测试理由"})


class _FakeChecker(LLMProvider):
    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.users: list[str] = []

    def complete(self, **kwargs) -> str:
        self.users.append(kwargs["user"])
        return self._raw


# ---- parse (tolerant, fail-open) ----


def test_parse_verdict_reject():
    assert parse_consistency_verdict(_verdict_json("reject")).verdict == "reject"


def test_parse_verdict_pass():
    assert parse_consistency_verdict(_verdict_json("pass")).verdict == "pass"


def test_parse_verdict_garbage_fails_open():
    assert parse_consistency_verdict("not json").verdict == "pass"


def test_parse_verdict_non_object_fails_open():
    assert parse_consistency_verdict("[1,2,3]").verdict == "pass"


# ---- checker prompt ----


def test_checker_prompt_carries_authorized_context():
    judge = _FakeChecker(_verdict_json("pass"))
    checker = SemanticConsistencyChecker(judge)
    verdict = checker.check(
        character_id="deepseek",
        authorized_context="环境：你听见滴水声",
        player_message="墙上写着什么？",
        dialogue="我看不见。",
    )
    assert verdict.verdict == "pass"
    user = judge.users[0]
    assert "有权知道" in user
    assert "滴水声" in user
    assert "我看不见。" in user
    # The rubric names the three violation classes.
    for keyword in ("leak", "fabrication", "contradiction"):
        assert keyword in CONSISTENCY_SYSTEM_PROMPT


class _FailingJudge(LLMProvider):
    def complete(self, **kwargs) -> str:
        raise ProviderError("judge provider down")


def test_checker_fails_open_on_provider_error():
    """A judge that cannot be reached must never block the reply (fail-open)."""
    checker = SemanticConsistencyChecker(_FailingJudge())
    verdict = checker.check(
        character_id="deepseek",
        authorized_context="",
        player_message="你好",
        dialogue="你好呀",
    )
    assert verdict.verdict == "pass"


# ---- orchestrator wiring ----


def _orchestrator(checker_raw: str | None) -> GameOrchestrator:
    checker = (
        SemanticConsistencyChecker(_FakeChecker(checker_raw))
        if checker_raw is not None
        else None
    )
    return GameOrchestrator(
        SessionStore(),
        {"deepseek": DeepSeekRuntime(MockProvider())},
        consistency_checker=checker,
    )


def test_orchestrator_rejects_on_reject_verdict():
    orchestrator = _orchestrator(_verdict_json("reject"))
    result = orchestrator.handle_turn(None, "你好。")
    # Rejected → safe fallback line, not the mock's dialogue.
    assert result.response.dialogue == "……等一下，我脑子有点卡住了。"


def test_orchestrator_passes_on_pass_verdict():
    orchestrator = _orchestrator(_verdict_json("pass"))
    result = orchestrator.handle_turn(None, "你好。")
    assert "本地模拟回复" in result.response.dialogue


def test_orchestrator_without_checker_keeps_normal_reply():
    orchestrator = _orchestrator(None)
    result = orchestrator.handle_turn(None, "你好。")
    assert "本地模拟回复" in result.response.dialogue
