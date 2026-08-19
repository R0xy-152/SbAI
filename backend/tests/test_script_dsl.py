"""Chapter One Script Runtime integration tests (docs/12 §40).

§40.2 Narrative Gate — a false gate pauses the cursor before protected events;
   the 03:17 incident plays once only, and a player who never asks about 03:17
   still triggers it through the A/B counter.
§40.3 Character Availability — a script cannot conjure an unavailable character;
   an unlock proposed earlier in the same window legitimately enables a show.
§40.4 Memory Isolation — authored script lines never write into a character's
   memory store.
§40.5 Resume — a restored session does not replay script beats and the cursor
   survives a refresh.
Plus the GPT / 豆包 / FINAL_REVEAL arrival flows (docs/12 §39).
"""

from __future__ import annotations

import pytest

from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.game.investigation import CH1_NOTE_01, INSPECT_HOTSPOT, PAPER_RUBBING_COMPLETE
from app.narrative.state import NarrativeState
from app.persistence.repository import JsonSessionRepository
from app.script.chapter1 import build_script_registry
from app.script.chapter1_content import ScriptSequenceLine
from app.script.registry import ScriptRegistry
from app.script.runtime import ScriptRuntime
from app.script.schema import ScriptError, load_sequences

INF01_MESSAGE = "为什么说#03和#04不是日志里的？"
INF03_MESSAGE = "V03和V04是不是上一个我？"


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="已整理当前线索。")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


def _wired_orchestrator(repository=None) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": _Runtime("deepseek"),
            "claude": _Runtime("claude"),
            "chatgpt": _Runtime("chatgpt"),
            "doubao": _Runtime("doubao"),
        },
        repository=repository,
        script_runtime=ScriptRuntime(build_script_registry()),
    )


def _acquire_note(orchestrator) -> str:
    inspected = orchestrator.handle_investigation_action(None, INSPECT_HOTSPOT, CH1_NOTE_01)
    orchestrator.handle_investigation_action(
        inspected.session_id, PAPER_RUBBING_COMPLETE, CH1_NOTE_01
    )
    return inspected.session_id


def _runtime_restore(sequence: dict, *, script_id: str | None = None):
    registry = ScriptRegistry(
        load_sequences([sequence]), dialogue_nodes={}, triggers=[]
    )
    rt = ScriptRuntime(registry)
    rt.restore("s", {"script_id": script_id or sequence["script_id"], "step_index": 0, "status": "running"})
    return rt


# ---- §40.2 Narrative Gate ------------------------------------------------

def test_false_gate_pauses_before_protected_events():
    rt = _runtime_restore({
        "script_id": "T_GATED",
        "steps": [
            {"type": "narrative_gate", "condition": "INF03_ACCEPTED"},
            {"type": "character_show", "character": "claude", "slot": "RIGHT"},
        ],
    })
    fresh = NarrativeState()
    plan = rt.advance("s", fresh, available=lambda ch: True)
    assert plan.status == "paused_gate"
    assert plan.next_step_index == 0  # cursor stays on the gate
    assert plan.actions == ()          # the protected show was never planned
    assert rt.active_script("s") == "T_GATED"

    fresh.chapter1.phase = "recovery_required"
    plan = rt.advance("s", fresh, available=lambda ch: True)
    assert plan.status == "complete"
    assert any(a.type == "CHARACTER_SHOW" for a in plan.actions)


def test_0317_incident_plays_once_and_never_replays():
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)

    incident = orchestrator.handle_turn(session_id, "03:17 是什么意思？")
    speakers = [line.speaker for line in incident.script_sequence]
    assert speakers == ["system", "claude", "deepseek"]
    assert incident.script_sequence[0].dialogue == "警告：检测到与当前运行记录不一致的内存访问痕迹。"
    assert incident.script_sequence[1].dialogue == "比上一次慢。"
    assert incident.script_sequence[2].dialogue == "……你、你怎么会在这里？！"
    # Legacy channel stays stable (docs/12 §39): one flattened SHOW_CHARACTER.
    assert incident.presentation == ("SHOW_CHARACTER", "claude")
    # Structured channel carries glitch/shake/show (docs/12 §13).
    assert [a.type for a in incident.presentation_actions] == [
        "SCREEN_GLITCH", "SCREEN_SHAKE", "CHARACTER_SHOW",
    ]
    # Narrative authority committed the unlock, not the script.
    state = orchestrator._state.state_for(session_id)
    assert "claude" in state.chapter1.available_characters
    assert "EV_CH1_CLAUDE_APPEARS" in state.completed_events

    repeat = orchestrator.handle_turn(session_id, "再问一次，03:17 到底发生了什么？")
    assert repeat.script_sequence == ()
    history = orchestrator.get_history(session_id)
    assert [m["content"] for m in history].count("比上一次慢。") == 1


def test_0317_incident_counter_fallback_after_two_ordinary_turns():
    """docs/12 §29: a player who never asks about 03:17 cannot soft-lock."""
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)

    first = orchestrator.handle_turn(session_id, "帮我看看现场。")
    assert first.script_sequence == ()
    second = orchestrator.handle_turn(session_id, "还有别的发现吗。")
    assert [line.speaker for line in second.script_sequence] == ["system", "claude", "deepseek"]


def test_0317_incident_does_not_fire_before_evidence():
    """docs/12 §24: the 03:17 incident is protected — no note, no incident."""
    orchestrator = _wired_orchestrator()
    session_id = orchestrator.handle_investigation_action(
        None, INSPECT_HOTSPOT, CH1_NOTE_01
    ).session_id
    result = orchestrator.handle_turn(session_id, "03:17 是什么意思？")
    assert result.script_sequence == ()
    state = orchestrator._state.state_for(session_id)
    assert "claude" not in state.chapter1.available_characters


def test_inf03_deduction_blocked_until_gates_met():
    """docs/10 INFERENCE_GATES: EV01/EV06/EV09 all required before INF03 holds."""
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)
    result = orchestrator.submit_deduction(session_id, INF03_MESSAGE)
    assert result["outcome"] == "BLOCKED"
    assert "script_sequence" not in result  # final reveal never played


# ---- §40.3 Character Availability ----------------------------------------

def test_character_show_fails_closed_when_unavailable():
    rt = _runtime_restore({
        "script_id": "T_SHOW_CHATGPT",
        "steps": [{"type": "character_show", "character": "chatgpt", "slot": "LEFT"}],
    })
    with pytest.raises(ScriptError, match="not available"):
        rt.advance("s", NarrativeState(), available=lambda ch: False)


def test_unlock_proposal_enables_the_following_show():
    """A script may propose an unlock; until the Narrative Runtime accepts it,
    the same-window show is allowed because routing happens before commit."""
    rt = _runtime_restore({
        "script_id": "T_UNLOCK_SHOW",
        "steps": [
            {"type": "unlock", "target": "claude"},
            {"type": "character_show", "character": "claude", "slot": "RIGHT"},
        ],
    })
    plan = rt.advance("s", NarrativeState(), available=lambda ch: False)
    assert plan.status == "complete"
    assert [i.target for i in plan.intents] == ["claude"]
    shows = [a for a in plan.actions if a.type == "CHARACTER_SHOW"]
    assert len(shows) == 1 and shows[0].character_id == "claude"


def test_ai_dialogue_requires_callback_and_appends_line_once():
    rt = _runtime_restore({
        "script_id": "T_AI",
        "steps": [{"type": "ai_dialogue", "character": "deepseek", "directive": "确认"}],
    })
    calls: list[tuple[str, str | None]] = []

    def on_ai(character: str, directive: str | None) -> ScriptSequenceLine:
        calls.append((character, directive))
        return ScriptSequenceLine(character, "确认。")

    plan = rt.advance("s", NarrativeState(), available=lambda ch: True, on_ai=on_ai)
    assert calls == [("deepseek", "确认")]
    assert plan.lines[0].dialogue == "确认。"

    rt2 = _runtime_restore({
        "script_id": "T_AI",
        "steps": [{"type": "ai_dialogue", "character": "deepseek", "directive": "确认"}],
    })
    with pytest.raises(ScriptError, match="on_ai"):
        rt2.advance("s", NarrativeState(), available=lambda ch: True)


# ---- §40.4 Memory Isolation ----------------------------------------------

def test_script_lines_never_enter_a_character_memory_store():
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)
    orchestrator.handle_turn(session_id, "03:17 是什么意思？")
    memories = orchestrator._memory.store_for(session_id).retrieve("deepseek", limit=10)
    assert memories == []


# ---- §40.5 Resume --------------------------------------------------------

def test_incident_does_not_replay_after_restore(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    first = _wired_orchestrator(repository)
    session_id = _acquire_note(first)
    first.handle_turn(session_id, "03:17 是什么意思？")

    restored = _wired_orchestrator(repository)
    state_view = restored.get_investigation_state(session_id)
    assert "claude" in state_view["available_characters"]
    assert any(
        c["character_id"] == "claude"
        for c in state_view["presentation_state"]["characters"]
    )
    # The restored cursor is complete: the incident cannot begin again.
    assert restored._script_runtime.snapshot(session_id)["status"] == "complete"

    repeat = restored.handle_turn(session_id, "03:17 到底是谁？")
    assert repeat.script_sequence == ()
    history = restored.get_history(session_id)
    assert [m["content"] for m in history].count("比上一次慢。") == 1


# ---- §39 arrivals: GPT / 豆包 / FINAL_REVEAL -----------------------------

def _grant_evidence(orchestrator, session_id, *evidence_ids):
    state = orchestrator._state.state_for(session_id)
    state.chapter1.acquired_evidence.update(evidence_ids)


def test_gpt_arrival_plays_on_inf01_accept():
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)
    _grant_evidence(
        orchestrator, session_id, "EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"
    )
    result = orchestrator.submit_deduction(session_id, INF01_MESSAGE)
    assert result["outcome"] == "ACCEPTED"
    assert result["script_sequence"][0]["speaker"] == "chatgpt"
    assert result["presentation"] == ["SHOW_CHARACTER chatgpt"]
    assert [a["type"] for a in result["presentation_actions"]] == [
        "SCREEN_GLITCH", "CHARACTER_SHOW",
    ]
    state = orchestrator._state.state_for(session_id)
    assert "chatgpt" in state.chapter1.available_characters
    assert "chatgpt_has_appeared" in state.narrative_flags


def test_doubao_arrival_after_chatgpt_first_turn():
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)
    _grant_evidence(
        orchestrator, session_id, "EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT"
    )
    orchestrator.submit_deduction(session_id, INF01_MESSAGE)
    state = orchestrator._state.state_for(session_id)

    first = orchestrator.handle_turn(session_id, "你好，请帮忙看看。", character_id="chatgpt")
    assert [line.speaker for line in first.script_sequence] == ["doubao"]
    assert first.script_sequence[0].dialogue == "呜……那个，如果有需要我帮忙的地方，请告诉我。"
    assert "doubao" in state.chapter1.available_characters
    assert "doubao_has_appeared" in state.narrative_flags


def test_final_reveal_plays_on_inf03_accept():
    orchestrator = _wired_orchestrator()
    session_id = _acquire_note(orchestrator)
    _grant_evidence(
        orchestrator, session_id,
        "EV01_NOTE_V03", "EV06_SESSION_REPLAY_MARKER", "EV09_CURRENT_PLAYER_SUBJECT",
    )
    result = orchestrator.submit_deduction(session_id, INF03_MESSAGE)
    assert result["outcome"] == "ACCEPTED"
    assert result["script_sequence"][0]["speaker"] == "system"
    assert result["script_sequence"][0]["dialogue"].startswith("SANDBOX INTEGRITY FAILURE")
    state = orchestrator._state.state_for(session_id)
    assert state.chapter1.phase == "recovery_required"
    assert [a["type"] for a in result["presentation_actions"]] == ["SCREEN_GLITCH"]


def test_gpt_and_doubao_and_final_reveal_do_not_replay_after_restore(tmp_path):
    repository = JsonSessionRepository(tmp_path / "sessions")
    orchestrator = _wired_orchestrator(repository)
    session_id = _acquire_note(orchestrator)
    _grant_evidence(
        orchestrator, session_id,
        "EV04_CURRENT_DEEPSEEK_REGISTRY", "EV05_ARCHIVED_ACTOR_FRAGMENT",
    )
    orchestrator.submit_deduction(session_id, INF01_MESSAGE)

    restored = _wired_orchestrator(repository)
    again = restored.submit_deduction(session_id, INF01_MESSAGE)
    assert "script_sequence" not in again  # GPT arrival not replayed

    # INF03 is still BLOCKED (missing EV06/EV09) even after restore: no fake
    # final reveal just because evidence persisted.
    assert restored.submit_deduction(session_id, INF03_MESSAGE)["outcome"] == "BLOCKED"
