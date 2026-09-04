"""docs/23 trial_v1: deterministic flow, redaction, gates and restore."""

from __future__ import annotations

import json

import pytest

from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository
from app.trial.runtime import TrialRuntime


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="fixture")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="fixture")


def _command(command_type: str, index: int, **payload) -> dict:
    return {"type": command_type, "command_id": f"command-{index}", **payload}


def _solved_shards() -> list[dict]:
    return [
        {"shard_id": shard_id, "x": 0.0, "y": 0.0, "rotation": 0.0}
        for shard_id in ("SHARD_NW", "SHARD_NE", "SHARD_SE", "SHARD_SW")
    ]


def _advance_to_first_reasoning(runtime: TrialRuntime, session_id: str = "s") -> None:
    runtime.handle(session_id, _command("ADVANCE", 1))
    runtime.handle(session_id, _command("ADVANCE", 2))
    runtime.handle(session_id, _command("PLAYER_INPUT", 3, message="晚安"))
    runtime.handle(session_id, _command("ADVANCE", 4))
    runtime.handle(
        session_id,
        _command("COMPLETE_SHATTER", 5, shards=_solved_shards()),
    )
    runtime.handle(session_id, _command("ADVANCE", 6))
    runtime.handle(session_id, _command("ADVANCE", 7))
    runtime.handle(session_id, _command("ADVANCE", 8))


def test_trial_flow_redacts_origin_ai_and_commits_ring_once():
    runtime = TrialRuntime()
    first = runtime.current("s")
    assert first["phase_id"] == "not_started"

    opening = runtime.handle("s", _command("ADVANCE", 1)).view
    serialized = json.dumps(opening, ensure_ascii=False)
    assert opening["node"]["speaker_label"] == "████"
    assert "原初 AI" not in serialized

    runtime.handle("s", _command("ADVANCE", 2))
    anomaly = runtime.handle("s", _command("PLAYER_INPUT", 3, message="还不睡吗？"))
    assert anomaly.checkpoint
    runtime.handle("s", _command("ADVANCE", 4))

    with pytest.raises(ValueError, match="snap tolerance"):
        bad = _solved_shards()
        bad[0]["x"] = 0.4
        runtime.handle("s", _command("COMPLETE_SHATTER", 5, shards=bad))

    remains = runtime.handle(
        "s",
        _command("COMPLETE_SHATTER", 6, shards=_solved_shards()),
    )
    assert remains.view["phase_id"] == "opening_origin_ai_remains"
    stopped = runtime.handle("s", _command("ADVANCE", 7))
    assert stopped.view["story_tokens"] == ["RING"]
    assert stopped.view["interaction"]["kind"] == "service_stop_modal"

    duplicate = runtime.handle("s", _command("ADVANCE", 7))
    assert not duplicate.changed
    assert duplicate.view["story_tokens"] == ["RING"]


def test_first_deduction_gates_group_but_final_submission_never_dead_ends():
    runtime = TrialRuntime()
    _advance_to_first_reasoning(runtime)
    view = runtime.current("s")
    assert view["interaction"]["deduction_id"] == "TRIAL_DEDUCTION_DEEPSEEK_MEMORY"
    assert all(4 <= len(item["title"]) <= 5 for item in view["authorized_evidence"])

    wrong = runtime.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            9,
            deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
            evidence_ids=["TRIAL_EV_TIME_VOID"],
            message="我还不确定",
        ),
    )
    assert wrong.view["phase_id"] == "fragment_01_first_reasoning"
    assert wrong.view["outcome"] == "NO_MATCH"

    accepted = runtime.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            10,
            deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
            evidence_ids=["TRIAL_EV_MEMORY_GAP"],
            message="你失忆了",
        ),
    )
    assert accepted.view["phase_id"] == "fragment_01_group_intro"
    assert accepted.checkpoint

    runtime.handle("s", _command("ADVANCE", 11))
    final = runtime.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            12,
            deduction_id="TRIAL_DEDUCTION_GROUP_TRUTH",
            evidence_ids=["TRIAL_EV_IDENTITY_NOISE"],
            message="错误也必须继续",
        ),
    )
    assert final.view["reasoning_outcome"] == "NO_MATCH"
    assert final.view["route_id"] == "fragment_02_b"
    assert final.view["finished"] is True
    assert final.checkpoint


def test_snapshot_restore_preserves_authoritative_route():
    source = TrialRuntime()
    _advance_to_first_reasoning(source)
    source.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            9,
            deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
            evidence_ids=["TRIAL_EV_MEMORY_GAP"],
            message="这是失忆",
        ),
    )
    source.handle("s", _command("ADVANCE", 10))
    source.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            11,
            deduction_id="TRIAL_DEDUCTION_GROUP_TRUTH",
            evidence_ids=["TRIAL_EV_MEMORY_GAP", "TRIAL_EV_DIALOGUE_FRAGMENT"],
            message="这就是真相",
        ),
    )
    snapshot = source.snapshot("s")

    target = TrialRuntime()
    target.restore("restored", snapshot)
    assert target.current("restored") == source.current("s")
    assert target.current("restored")["route_id"] == "fragment_02_a"


def test_snapshot_validation_fails_closed():
    with pytest.raises(ValueError, match="unknown trial phase"):
        TrialRuntime.validate_snapshot(
            {"experience_id": "trial_v1", "phase_id": "invented"}
        )


def test_orchestrator_restores_trial_without_touching_story_cursor(tmp_path):
    runtimes = {
        character_id: _Runtime(character_id)
        for character_id in ("deepseek", "chatgpt", "claude", "doubao")
    }
    repository = JsonSessionRepository(tmp_path / "sessions")
    first = GameOrchestrator(
        SessionStore(), runtimes, repository=repository, trial_runtime=TrialRuntime()
    )
    view = first.trial_handle(None, _command("ADVANCE", 1), player_id="player")
    session_id = view["session_id"]
    persisted = repository.load(session_id)
    assert persisted is not None
    assert persisted.story_cursor is None
    assert persisted.trial_state["experience_id"] == "trial_v1"

    restored = GameOrchestrator(
        SessionStore(), runtimes, repository=repository, trial_runtime=TrialRuntime()
    )
    current = restored.trial_current(session_id)
    assert current["phase_id"] == "opening_warm_chat"
    assert restored.story_progress(session_id) == {
        "story_cursor": None,
        "story_finished": False,
    }
