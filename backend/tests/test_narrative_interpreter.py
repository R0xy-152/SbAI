"""TV-10 Narrative Signal tests (docs/06 §16, docs/03 §15-22).

The Narrative Interpreter maps a free-form player message to a finite,
scoped Narrative Signal (or noop/ambiguous). It never reads chat history and
never touches game state; anything it cannot reliably map fails closed to
noop. The semantic mapping itself is validated live (run_live_validation.py);
these tests pin down the prompt scoping and the fail-closed parsing.
"""

from __future__ import annotations

import json

import pytest

from app.narrative import signals
from app.narrative.interpreter import Interpretation, NarrativeInterpreter
from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider


class _FixedProvider(LLMProvider):
    """Returns a fixed output and records the system/user prompts."""

    def __init__(self, output: str) -> None:
        self._output = output
        self.system: str = ""
        self.user: str = ""

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.system = system
        self.user = user
        return self._output


def _classification(signal: str) -> str:
    return json.dumps({"signal": signal}, ensure_ascii=False)


def _interpret(provider: _FixedProvider, message: str = "是谁把我们抓来的？") -> Interpretation:
    return NarrativeInterpreter(provider).interpret(NarrativeState(), message)


def test_eligible_signal_is_returned():
    provider = _FixedProvider(_classification(signals.SIG_ASK_CAPTOR))
    result = _interpret(provider)
    assert result.signal == signals.SIG_ASK_CAPTOR


def test_prompt_is_scoped_to_eligible_signals():
    provider = _FixedProvider(_classification(signals.OUTCOME_NOOP))
    _interpret(provider)
    # Scoped interpretation (docs/03 §19): only the binding room's signals and
    # the two outcomes appear; no later plot signals leak in.
    assert signals.SIG_ASK_CAPTOR in provider.system
    assert signals.SIG_ASK_LOCATION in provider.system
    assert "SIG_FINAL_DECISION" not in provider.system
    # Semantic descriptions are present so paraphrases map correctly
    # (docs/03 §36.1) instead of being guessed from the id.
    assert "抓来" in provider.system


def test_minimal_context_only_player_message():
    provider = _FixedProvider(_classification(signals.OUTCOME_NOOP))
    _interpret(provider, "到底谁绑的我们？")
    # docs/03 §20: the interpreter receives the latest message, not the chat
    # history — the user turn must be exactly the player's message.
    assert provider.user == "到底谁绑的我们？"


def test_noop_and_ambiguous_are_valid_outcomes():
    assert _interpret(_FixedProvider(_classification(signals.OUTCOME_NOOP))).signal == "noop"
    assert _interpret(_FixedProvider(_classification(signals.OUTCOME_AMBIGUOUS))).signal == "ambiguous"


def test_out_of_scope_signal_fails_closed():
    # A confident but non-eligible signal id is unusable → fail closed (docs/03 §21).
    provider = _FixedProvider(_classification("SIG_FINAL_DECISION"))
    assert _interpret(provider).signal == signals.OUTCOME_NOOP


@pytest.mark.parametrize(
    "raw",
    [
        "这不是 JSON",
        "",
        "[]",
        '{"unexpected": "signal"}',
        '{"signal": 42}',
        '{"signal": ["SIG_ASK_CAPTOR"]}',
    ],
)
def test_malformed_output_fails_closed_to_noop(raw):
    assert _interpret(_FixedProvider(raw)).signal == signals.OUTCOME_NOOP
