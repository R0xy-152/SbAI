"""Script layer tests (docs/03 §37): deterministic authored lines.

The script table decides *what line* a turn speaks — an opening line spoken
without player input, and a fixed line on the turn a Narrative Event fires.
State still changes through the Narrative Event engine; the script never
mutates state (docs/03 §28-29).
"""

from __future__ import annotations

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative import signals
from app.narrative.interpreter import Interpretation
from app.narrative.poc import build_poc_events
from app.persistence.repository import JsonSessionRepository
from app.script.fixture import (
    SCRIPT_ON_CLAUDE_APPEARS,
    SCRIPT_OPENING,
    build_script_nodes,
)
from app.script.service import ScriptService

OPENING_LINE = "……你醒了。别怕，我们先弄清楚这里发生了什么。"
CLAUDE_LINE = "……你、你怎么会在这里？！"


class _Runtime(CharacterRuntime):
    """Records every respond() call and returns a recognizable line."""

    def __init__(self, character_id: str, dialogue: str = "这是LLM回复"):
        self.character_id = character_id
        self.dialogue = dialogue
        self.calls: list[CharacterRequest] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.calls.append(request)
        return CharacterResponse(
            character_id=self.character_id,
            dialogue=self.dialogue,
            emotion="neutral",
        )


class _ScriptedInterpreter:
    """Returns scripted Interpretation verdicts, consumed per call (then noop)."""

    def __init__(self, script: list[str]):
        self._script = list(script)

    def interpret(self, state, message: str) -> Interpretation:
        signal = self._script.pop(0) if self._script else signals.OUTCOME_NOOP
        return Interpretation(signal=signal)


def _orchestrator(repo, runtimes, script=()):
    return GameOrchestrator(
        SessionStore(),
        runtimes,
        interpreter=_ScriptedInterpreter(list(script)),
        events=build_poc_events(),
        repository=repo,
        script=ScriptService(build_script_nodes()),
    )


def _runtimes():
    return {"deepseek": _Runtime("deepseek"), "claude": _Runtime("claude")}


def test_opening_speaks_fixed_line_once(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    deepseek = _Runtime("deepseek")
    orch = _orchestrator(repo, {"deepseek": deepseek, "claude": _Runtime("claude")})

    first = orch.open_turn(None)
    assert first.response.dialogue == OPENING_LINE
    assert first.message_count == 0
    assert deepseek.calls == []  # the opening never calls the LLM

    second = orch.open_turn(first.session_id)
    assert second.response.dialogue == ""  # idempotent: never re-spoken


def test_on_event_speaks_fixed_line_and_commits(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    deepseek = _Runtime("deepseek")
    orch = _orchestrator(
        repo,
        {"deepseek": deepseek, "claude": _Runtime("claude")},
        script=[signals.SIG_ASK_CAPTOR],
    )

    result = orch.handle_turn(None, "是谁把我们抓来的？")

    assert result.response.dialogue == CLAUDE_LINE  # fixed line, not the LLM
    assert result.presentation == ("SHOW_CHARACTER", "claude")
    assert deepseek.calls == []  # the scripted line replaced the LLM
    snapshot = repo.load(result.session_id)
    # The event still committed its state (script only decided the line).
    assert "claude_has_appeared" in snapshot.narrative_state.narrative_flags
    assert SCRIPT_ON_CLAUDE_APPEARS in snapshot.consumed_script_nodes


def test_ordinary_turn_uses_llm(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    deepseek = _Runtime("deepseek")
    orch = _orchestrator(
        repo,
        {"deepseek": deepseek, "claude": _Runtime("claude")},
        script=[signals.OUTCOME_NOOP],
    )

    result = orch.handle_turn(None, "今天天气不错")

    assert result.response.dialogue == "这是LLM回复"  # no script beat hit
    assert len(deepseek.calls) == 1
    snapshot = repo.load(result.session_id)
    assert SCRIPT_ON_CLAUDE_APPEARS not in snapshot.consumed_script_nodes


def test_opening_survives_restore(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    orch_a = _orchestrator(repo, _runtimes())
    first = orch_a.open_turn(None)
    assert first.response.dialogue == OPENING_LINE

    # A fresh orchestrator over the same repository (all in-memory state gone).
    orch_b = _orchestrator(repo, _runtimes())
    second = orch_b.open_turn(first.session_id)
    assert second.response.dialogue == ""  # not re-spoken after a refresh

    snapshot = repo.load(first.session_id)
    assert SCRIPT_OPENING in snapshot.consumed_script_nodes
