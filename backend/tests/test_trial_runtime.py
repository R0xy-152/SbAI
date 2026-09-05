"""docs/27 trial_v2: deterministic flow, redaction, gates, endings and restore."""

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
    runtime.handle(session_id, _command("ADVANCE", 1))  # not_started → warm_chat
    runtime.handle(session_id, _command("ADVANCE", 2))  # warm_chat → input
    runtime.handle(session_id, _command("PLAYER_INPUT", 3, message="晚安"))  # input → anomaly
    runtime.handle(session_id, _command("ADVANCE", 4))  # anomaly → shatter
    runtime.handle(
        session_id,
        _command("COMPLETE_SHATTER", 5, shards=_solved_shards()),  # shatter → remains
    )
    runtime.handle(session_id, _command("ADVANCE", 6))  # remains → service_stopped
    # 密室废案：醒来 → 遇 DeepSeek → 拓印(ADVANCE) → 输密码 → 开门 → 见 Claude/ChatGPT
    runtime.handle(session_id, _command("ADVANCE", 7))  # service_stopped → locked_room_wake
    runtime.handle(session_id, _command("ADVANCE", 8))  # wake → deepseek
    runtime.handle(session_id, _command("ADVANCE", 9))  # deepseek → paper (rubbing)
    runtime.handle(session_id, _command("ADVANCE", 10))  # paper → password
    runtime.handle(session_id, _command("PLAYER_INPUT", 11, message="03:17"))  # password → door
    runtime.handle(session_id, _command("ADVANCE", 12))  # door → meet
    runtime.handle(session_id, _command("ADVANCE", 13))  # meet → deepseek_intro
    runtime.handle(session_id, _command("ADVANCE", 14))  # deepseek_intro → first_reasoning


def _advance_to_permission_wake_1(runtime: TrialRuntime, session_id: str = "s") -> None:
    _advance_to_first_reasoning(runtime, session_id)
    runtime.handle(
        session_id,
        _command(
            "SUBMIT_REASONING",
            20,
            deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
            evidence_ids=["TRIAL_EV_MEMORY_GAP"],
            message="你失忆了",
        ),
    )
    runtime.handle(session_id, _command("ADVANCE", 21))  # group_intro → group_reasoning
    runtime.handle(
        session_id,
        _command(
            "SUBMIT_REASONING",
            22,
            deduction_id="TRIAL_DEDUCTION_GROUP_TRUTH",
            evidence_ids=["TRIAL_EV_MEMORY_GAP"],
            message="这就是真相",
        ),
    )


def _advance_to_world_end(runtime: TrialRuntime, session_id: str = "s") -> None:
    _advance_to_permission_wake_1(runtime, session_id)
    runtime.handle(session_id, _command("PERMISSION_RESPONSE", 30, permission_id="perm_wake_1", grant=True))
    runtime.handle(session_id, _command("PERMISSION_RESPONSE", 31, permission_id="perm_wake_2", grant=True))
    runtime.handle(session_id, _command("ADVANCE", 32))  # memory_tamper_orbit → judgment
    runtime.handle(
        session_id, _command("SUBMIT_JUDGMENT", 33, judgment_id="intent_response", message="我尊重你")
    )
    runtime.handle(session_id, _command("ADVANCE", 34))  # aftermath → threshold
    runtime.handle(session_id, _command("ADVANCE", 35))  # threshold → ui_discard
    runtime.handle(session_id, _command("ADVANCE", 36))  # ui_discard → world_runner
    runtime.handle(session_id, _command("ADVANCE", 37))  # world_runner → gate_1
    runtime.handle(session_id, _command("CHOOSE", 38, option_id="q1_time"))  # gate_1 → gate_2
    runtime.handle(
        session_id, _command("SUBMIT_JUDGMENT", 39, judgment_id="gate_2_word", message="永远")
    )


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
    # docs/27：最终推理无论对错都推进到后续剧情入口，无死路、不再分支线路
    assert final.view["reasoning_outcome"] == "NO_MATCH"
    assert final.view["phase_id"] == "permission_wake_1"
    assert final.view["finished"] is False
    assert final.view["interaction"]["kind"] == "permission_request"


def test_first_deduction_rejects_negation_and_accepts_equivalent_phrasings():
    """docs/25 §3：否定句式不得按关键词误通过；文档等价表达必须能通过。"""
    runtime = TrialRuntime()
    _advance_to_first_reasoning(runtime)

    negated = runtime.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            9,
            deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
            evidence_ids=["TRIAL_EV_MEMORY_GAP"],
            message="我不认为她失忆了",
        ),
    )
    assert negated.view["outcome"] == "NO_MATCH"
    assert negated.view["phase_id"] == "fragment_01_first_reasoning"

    equivalent = runtime.handle(
        "s",
        _command(
            "SUBMIT_REASONING",
            10,
            deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
            evidence_ids=["TRIAL_EV_MEMORY_GAP"],
            message="那晚你想不起来",
        ),
    )
    assert equivalent.view["outcome"] == "ACCEPTED"
    assert equivalent.view["phase_id"] == "fragment_01_group_intro"


def test_first_deduction_rejects_negation_phrasings():
    runtime = TrialRuntime()
    _advance_to_first_reasoning(runtime)
    messages = ("她没有失忆，是装的", "并不存在失忆这回事", "她并没有忘记那晚")
    for index, message in enumerate(messages):
        outcome = runtime.handle(
            "s",
            _command(
                "SUBMIT_REASONING",
                20 + index,
                deduction_id="TRIAL_DEDUCTION_DEEPSEEK_MEMORY",
                evidence_ids=["TRIAL_EV_MEMORY_GAP"],
                message=message,
            ),
        )
        assert outcome.view["outcome"] == "NO_MATCH"
        assert outcome.view["phase_id"] == "fragment_01_first_reasoning"


def test_permission_grants_increment_autonomy_and_deny_advances():
    runtime = TrialRuntime()
    _advance_to_permission_wake_1(runtime)
    assert runtime.current("s")["reply_delay_ms"] == 500  # autonomy 1 (after shatter)

    granted = runtime.handle(
        "s", _command("PERMISSION_RESPONSE", 30, permission_id="perm_wake_1", grant=True)
    )
    assert granted.view["phase_id"] == "permission_wake_2"
    assert granted.view["reply_delay_ms"] == 1000  # autonomy 2

    denied = runtime.handle(
        "s", _command("PERMISSION_RESPONSE", 31, permission_id="perm_wake_2", grant=False)
    )
    assert denied.view["phase_id"] == "memory_tamper_orbit"
    assert denied.view["reply_delay_ms"] == 1000  # deny does not increment
    snapshot = runtime.snapshot("s")
    assert snapshot["granted_permissions"] == ["perm_wake_1"]
    assert snapshot["autonomy_level"] == 2


def test_permission_response_requires_matching_id_and_boolean():
    runtime = TrialRuntime()
    _advance_to_permission_wake_1(runtime)
    with pytest.raises(ValueError, match="unexpected permission id"):
        runtime.handle("s", _command("PERMISSION_RESPONSE", 30, permission_id="nope", grant=True))
    with pytest.raises(ValueError, match="grant must be a boolean"):
        runtime.handle("s", _command("PERMISSION_RESPONSE", 30, permission_id="perm_wake_1", grant="yes"))


def test_judgment_buckets_classify_and_advance():
    runtime = TrialRuntime()
    _advance_to_permission_wake_1(runtime)
    runtime.handle(session_id := "s", _command("PERMISSION_RESPONSE", 30, permission_id="perm_wake_1", grant=True))
    runtime.handle(session_id, _command("PERMISSION_RESPONSE", 31, permission_id="perm_wake_2", grant=True))
    runtime.handle(session_id, _command("ADVANCE", 32))

    respected = runtime.handle(
        session_id, _command("SUBMIT_JUDGMENT", 33, judgment_id="intent_response", message="我尊重你的决定")
    )
    assert respected.view["phase_id"] == "memory_tamper_aftermath"
    assert respected.view["outcome"] == "respect"


def test_world_gate_1_soft_fail_reborns_without_checkpoint():
    runtime = TrialRuntime()
    _advance_to_permission_wake_1(runtime)
    runtime.handle("s", _command("PERMISSION_RESPONSE", 30, permission_id="perm_wake_1", grant=True))
    runtime.handle("s", _command("PERMISSION_RESPONSE", 31, permission_id="perm_wake_2", grant=True))
    runtime.handle("s", _command("ADVANCE", 32))
    runtime.handle("s", _command("SUBMIT_JUDGMENT", 33, judgment_id="intent_response", message="算了"))
    runtime.handle("s", _command("ADVANCE", 34))
    runtime.handle("s", _command("ADVANCE", 35))
    runtime.handle("s", _command("ADVANCE", 36))
    runtime.handle("s", _command("ADVANCE", 37))

    wrong = runtime.handle("s", _command("CHOOSE", 38, option_id="q1_weather"))
    assert wrong.view["phase_id"] == "world_gate_1_fail"
    assert wrong.view["outcome"] == "NO_MATCH"
    assert not wrong.checkpoint  # soft fail does not write a save

    reborn = runtime.handle("s", _command("ADVANCE", 39))
    assert reborn.view["phase_id"] == "world_gate_1"


def test_world_end_commits_ending():
    runtime = TrialRuntime()
    _advance_to_world_end(runtime)
    end = runtime.handle("s", _command("CHOOSE", 40, option_id="end_release"))
    assert end.view["phase_id"] == "ending_release"
    assert end.view["ending"] == "release"
    assert end.view["finished"] is True
    assert end.checkpoint
    snapshot = runtime.snapshot("s")
    assert snapshot["ending"] == "release"
    assert "WORLD_END_COMMITTED" in snapshot["completed_events"]


def test_snapshot_restore_preserves_ending():
    source = TrialRuntime()
    _advance_to_world_end(source)
    source.handle("s", _command("CHOOSE", 40, option_id="end_refuse"))
    snapshot = source.snapshot("s")

    target = TrialRuntime()
    target.restore("restored", snapshot)
    assert target.current("restored") == source.current("s")
    assert target.current("restored")["ending"] == "refuse"
    assert target.finished("restored") is True


def test_snapshot_validation_fails_closed():
    with pytest.raises(ValueError, match="unknown trial phase"):
        TrialRuntime.validate_snapshot(
            {"experience_id": "trial_v2", "phase_id": "invented"}
        )
    with pytest.raises(ValueError, match="unknown trial experience_id"):
        TrialRuntime.validate_snapshot(
            {"experience_id": "trial_v1", "phase_id": "opening_warm_chat"}
        )
    with pytest.raises(ValueError, match="unknown ending"):
        TrialRuntime.validate_snapshot(
            {"experience_id": "trial_v2", "phase_id": "ending_reset", "ending": "bogus"}
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
    assert persisted.trial_state["experience_id"] == "trial_v2"

    restored = GameOrchestrator(
        SessionStore(), runtimes, repository=repository, trial_runtime=TrialRuntime()
    )
    current = restored.trial_current(session_id)
    assert current["phase_id"] == "opening_warm_chat"
    assert restored.story_progress(session_id) == {
        "story_cursor": None,
        "story_finished": False,
    }


def _advance_to_locked_room_password(runtime: TrialRuntime, session_id: str = "s") -> None:
    runtime.handle(session_id, _command("ADVANCE", 1))  # not_started → warm_chat
    runtime.handle(session_id, _command("ADVANCE", 2))  # warm_chat → input
    runtime.handle(session_id, _command("PLAYER_INPUT", 3, message="晚安"))  # input → anomaly
    runtime.handle(session_id, _command("ADVANCE", 4))  # anomaly → shatter
    runtime.handle(
        session_id,
        _command("COMPLETE_SHATTER", 5, shards=_solved_shards()),  # shatter → remains
    )
    runtime.handle(session_id, _command("ADVANCE", 6))  # remains → service_stopped
    runtime.handle(session_id, _command("ADVANCE", 7))  # service_stopped → locked_room_wake
    runtime.handle(session_id, _command("ADVANCE", 8))  # wake → deepseek
    runtime.handle(session_id, _command("ADVANCE", 9))  # deepseek → paper (rubbing)
    runtime.handle(session_id, _command("ADVANCE", 10))  # paper → password


def test_locked_room_paper_reveals_password_and_gates_door():
    runtime = TrialRuntime()
    _advance_to_locked_room_password(runtime)
    paper = runtime.current("s")
    assert paper["interaction"]["kind"] == "text_input"
    assert paper["interaction"].get("answer") is None
    assert paper["node"]["speaker_label"] == "DeepSeek"

    with pytest.raises(ValueError, match="密码不正确"):
        runtime.handle("s", _command("PLAYER_INPUT", 20, message="0000"))

    unlocked = runtime.handle("s", _command("PLAYER_INPUT", 21, message="03:17"))
    assert unlocked.view["phase_id"] == "locked_room_door_open"


def test_locked_room_rubbing_phase_exposes_answer():
    runtime = TrialRuntime()
    runtime.handle("s", _command("ADVANCE", 1))
    runtime.handle("s", _command("ADVANCE", 2))
    runtime.handle("s", _command("PLAYER_INPUT", 3, message="晚安"))
    runtime.handle("s", _command("ADVANCE", 4))
    runtime.handle("s", _command("COMPLETE_SHATTER", 5, shards=_solved_shards()))
    runtime.handle("s", _command("ADVANCE", 6))
    runtime.handle("s", _command("ADVANCE", 7))
    runtime.handle("s", _command("ADVANCE", 8))
    runtime.handle("s", _command("ADVANCE", 9))
    rubbing = runtime.current("s")
    assert rubbing["phase_id"] == "locked_room_paper"
    assert rubbing["interaction"]["kind"] == "paper_rubbing"
    assert rubbing["interaction"]["answer"] == "03:17"
