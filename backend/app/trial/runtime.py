"""Deterministic trial_v1 state machine behind one small command interface."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from app.trial.content import (
    FIXTURE_LINES,
    TRIAL_EVIDENCE,
    TRIAL_EVIDENCE_BY_ID,
    TRIAL_ID,
    TRIAL_SCENES,
)

NOT_STARTED = "not_started"
OPENING_WARM_CHAT = "opening_warm_chat"
OPENING_INPUT = "opening_input"
OPENING_ANOMALY = "opening_anomaly"
OPENING_SHATTER = "opening_shatter"
OPENING_REMAINS = "opening_origin_ai_remains"
OPENING_SERVICE_STOPPED = "opening_service_stopped"
FRAGMENT_01_DEEPSEEK_INTRO = "fragment_01_deepseek_intro"
FRAGMENT_01_FIRST_REASONING = "fragment_01_first_reasoning"
FRAGMENT_01_GROUP_INTRO = "fragment_01_group_intro"
FRAGMENT_01_GROUP_REASONING = "fragment_01_group_reasoning"
FRAGMENT_02_HANDOFF_A = "fragment_02_handoff_a"
FRAGMENT_02_HANDOFF_B = "fragment_02_handoff_b"

TRIAL_PHASES = frozenset(
    {
        NOT_STARTED,
        OPENING_WARM_CHAT,
        OPENING_INPUT,
        OPENING_ANOMALY,
        OPENING_SHATTER,
        OPENING_REMAINS,
        OPENING_SERVICE_STOPPED,
        FRAGMENT_01_DEEPSEEK_INTRO,
        FRAGMENT_01_FIRST_REASONING,
        FRAGMENT_01_GROUP_INTRO,
        FRAGMENT_01_GROUP_REASONING,
        FRAGMENT_02_HANDOFF_A,
        FRAGMENT_02_HANDOFF_B,
    }
)

CHECKPOINT_PHASES = frozenset(
    {
        OPENING_ANOMALY,
        OPENING_REMAINS,
        OPENING_SERVICE_STOPPED,
        FRAGMENT_01_GROUP_INTRO,
        FRAGMENT_02_HANDOFF_A,
        FRAGMENT_02_HANDOFF_B,
    }
)

SHARD_IDS = ("SHARD_NW", "SHARD_NE", "SHARD_SE", "SHARD_SW")


@dataclass
class TrialState:
    experience_id: str = TRIAL_ID
    phase_id: str = NOT_STARTED
    completed_events: set[str] = field(default_factory=set)
    acquired_story_tokens: set[str] = field(default_factory=set)
    first_deduction_attempts: list[dict] = field(default_factory=list)
    deepseek_truth_revealed: bool = False
    final_evidence_ids: list[str] = field(default_factory=list)
    final_reasoning_outcome: str | None = None
    route_id: str | None = None
    last_outcome: str | None = None
    last_command_id: str | None = None

    def snapshot(self) -> dict:
        data = asdict(self)
        data["completed_events"] = sorted(self.completed_events)
        data["acquired_story_tokens"] = sorted(self.acquired_story_tokens)
        return data


@dataclass(frozen=True)
class TrialTransition:
    view: dict
    changed: bool
    checkpoint: bool


class TrialRuntime:
    """Owns every trial_v1 transition; callers only submit bounded commands."""

    def __init__(self) -> None:
        self._states: dict[str, TrialState] = {}

    def started(self, session_id: str) -> bool:
        state = self._states.get(session_id)
        return state is not None and state.phase_id != NOT_STARTED

    def finished(self, session_id: str) -> bool:
        state = self._states.get(session_id)
        return state is not None and state.phase_id in {
            FRAGMENT_02_HANDOFF_A,
            FRAGMENT_02_HANDOFF_B,
        }

    def current(self, session_id: str) -> dict:
        state = self._states.get(session_id, TrialState())
        return self._view(state)

    def handle(self, session_id: str, command: dict[str, Any]) -> TrialTransition:
        command_type = command.get("type")
        command_id = command.get("command_id")
        if not isinstance(command_id, str) or not command_id:
            raise ValueError("trial command_id is required")
        state = self._states.setdefault(session_id, TrialState())
        if state.last_command_id == command_id:
            return TrialTransition(self._view(state), changed=False, checkpoint=False)

        before_phase = state.phase_id
        if command_type == "ADVANCE":
            self._advance(state)
        elif command_type == "PLAYER_INPUT":
            self._player_input(state, command.get("message"))
        elif command_type == "COMPLETE_SHATTER":
            self._complete_shatter(state, command.get("shards"))
        elif command_type == "SUBMIT_REASONING":
            self._submit_reasoning(
                state,
                command.get("deduction_id"),
                command.get("evidence_ids"),
                command.get("message"),
            )
        else:
            raise ValueError(f"unknown trial command type {command_type!r}")

        state.last_command_id = command_id
        changed = before_phase != state.phase_id or command_type == "SUBMIT_REASONING"
        checkpoint = before_phase != state.phase_id and state.phase_id in CHECKPOINT_PHASES
        return TrialTransition(self._view(state), changed=changed, checkpoint=checkpoint)

    def snapshot(self, session_id: str) -> dict | None:
        state = self._states.get(session_id)
        return None if state is None or state.phase_id == NOT_STARTED else state.snapshot()

    def restore(self, session_id: str, snapshot: dict | None) -> None:
        if snapshot is None:
            self._states.pop(session_id, None)
            return
        self.validate_snapshot(snapshot)
        self._states[session_id] = TrialState(
            experience_id=TRIAL_ID,
            phase_id=snapshot["phase_id"],
            completed_events=set(snapshot.get("completed_events", [])),
            acquired_story_tokens=set(snapshot.get("acquired_story_tokens", [])),
            first_deduction_attempts=deepcopy(snapshot.get("first_deduction_attempts", [])),
            deepseek_truth_revealed=bool(snapshot.get("deepseek_truth_revealed", False)),
            final_evidence_ids=list(snapshot.get("final_evidence_ids", [])),
            final_reasoning_outcome=snapshot.get("final_reasoning_outcome"),
            route_id=snapshot.get("route_id"),
            last_outcome=snapshot.get("last_outcome"),
            last_command_id=snapshot.get("last_command_id"),
        )

    @staticmethod
    def validate_snapshot(snapshot: dict) -> None:
        if not isinstance(snapshot, dict):
            raise ValueError("trial_state must be an object")
        if snapshot.get("experience_id") != TRIAL_ID:
            raise ValueError("unknown trial experience_id")
        phase = snapshot.get("phase_id")
        if phase not in TRIAL_PHASES or phase == NOT_STARTED:
            raise ValueError(f"unknown trial phase: {phase!r}")
        evidence_ids = snapshot.get("final_evidence_ids", [])
        if not isinstance(evidence_ids, list) or any(
            evidence_id not in TRIAL_EVIDENCE_BY_ID for evidence_id in evidence_ids
        ):
            raise ValueError("trial_state contains unknown evidence ids")
        tokens = set(snapshot.get("acquired_story_tokens", []))
        if not tokens.issubset({"RING"}):
            raise ValueError("trial_state contains unknown story tokens")
        route_id = snapshot.get("route_id")
        if route_id not in {None, "fragment_02_a", "fragment_02_b"}:
            raise ValueError("trial_state contains unknown route")
        if phase.endswith("handoff_a") and route_id != "fragment_02_a":
            raise ValueError("trial handoff A requires route A")
        if phase.endswith("handoff_b") and route_id != "fragment_02_b":
            raise ValueError("trial handoff B requires route B")

    def _advance(self, state: TrialState) -> None:
        transitions = {
            NOT_STARTED: OPENING_WARM_CHAT,
            OPENING_WARM_CHAT: OPENING_INPUT,
            OPENING_ANOMALY: OPENING_SHATTER,
            OPENING_REMAINS: OPENING_SERVICE_STOPPED,
            OPENING_SERVICE_STOPPED: FRAGMENT_01_DEEPSEEK_INTRO,
            FRAGMENT_01_DEEPSEEK_INTRO: FRAGMENT_01_FIRST_REASONING,
            FRAGMENT_01_GROUP_INTRO: FRAGMENT_01_GROUP_REASONING,
        }
        next_phase = transitions.get(state.phase_id)
        if next_phase is None:
            raise ValueError(f"ADVANCE is not allowed during {state.phase_id}")
        if next_phase == OPENING_SERVICE_STOPPED:
            state.acquired_story_tokens.add("RING")
            state.completed_events.add("RING_ACQUIRED")
        state.phase_id = next_phase
        state.last_outcome = None

    def _player_input(self, state: TrialState, message: Any) -> None:
        if state.phase_id != OPENING_INPUT:
            raise ValueError(f"PLAYER_INPUT is not allowed during {state.phase_id}")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("player input must not be empty")
        if len(message) > 2000:
            raise ValueError("player input is too long")
        state.completed_events.add("OPENING_INPUT_COMPLETED")
        state.phase_id = OPENING_ANOMALY
        state.last_outcome = "ACCEPTED"

    def _complete_shatter(self, state: TrialState, shards: Any) -> None:
        if "SHATTER_SOLVED" in state.completed_events:
            return
        if state.phase_id != OPENING_SHATTER:
            raise ValueError(f"COMPLETE_SHATTER is not allowed during {state.phase_id}")
        if not isinstance(shards, list) or len(shards) != len(SHARD_IDS):
            raise ValueError("exactly four shard poses are required")
        by_id = {pose.get("shard_id"): pose for pose in shards if isinstance(pose, dict)}
        if set(by_id) != set(SHARD_IDS):
            raise ValueError("shard poses must contain the four unique shard ids")
        for shard_id in SHARD_IDS:
            pose = by_id[shard_id]
            try:
                x = float(pose["x"])
                y = float(pose["y"])
                rotation = float(pose["rotation"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid shard pose") from exc
            if abs(x) > 0.035 or abs(y) > 0.035 or abs(rotation) > 4.0:
                raise ValueError(f"shard {shard_id} is outside the snap tolerance")
        state.completed_events.add("SHATTER_SOLVED")
        state.phase_id = OPENING_REMAINS
        state.last_outcome = "ACCEPTED"

    def _submit_reasoning(
        self,
        state: TrialState,
        deduction_id: Any,
        evidence_ids: Any,
        message: Any,
    ) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("reasoning message must not be empty")
        if len(message) > 4000:
            raise ValueError("reasoning message is too long")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError("at least one evidence id is required")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence ids must be unique")
        if any(evidence_id not in TRIAL_EVIDENCE_BY_ID for evidence_id in evidence_ids):
            raise ValueError("unknown or unauthorized trial evidence")

        normalized = message.lower().replace(" ", "")
        if state.phase_id == FRAGMENT_01_FIRST_REASONING:
            if deduction_id != "TRIAL_DEDUCTION_DEEPSEEK_MEMORY":
                raise ValueError("unexpected deduction id")
            if len(evidence_ids) > 2:
                raise ValueError("first deduction accepts at most two evidence items")
            accepted = "TRIAL_EV_MEMORY_GAP" in evidence_ids and any(
                term in normalized for term in ("失忆", "记忆断层", "记不起来", "忘记")
            )
            state.first_deduction_attempts.append(
                {"evidence_ids": list(evidence_ids), "outcome": "ACCEPTED" if accepted else "NO_MATCH"}
            )
            if accepted:
                state.deepseek_truth_revealed = True
                state.completed_events.add("DEEPSEEK_MEMORY_TRUTH_REVEALED")
                state.phase_id = FRAGMENT_01_GROUP_INTRO
                state.last_outcome = "ACCEPTED"
            else:
                state.last_outcome = "NO_MATCH"
            return

        if state.phase_id == FRAGMENT_01_GROUP_REASONING:
            if deduction_id != "TRIAL_DEDUCTION_GROUP_TRUTH":
                raise ValueError("unexpected deduction id")
            if len(evidence_ids) > 3:
                raise ValueError("group deduction accepts at most three evidence items")
            correct_pair = {
                "TRIAL_EV_MEMORY_GAP",
                "TRIAL_EV_DIALOGUE_FRAGMENT",
            }.issubset(set(evidence_ids))
            semantic_match = any(
                term in normalized for term in ("真相", "身份", "异常", "记忆")
            )
            outcome = "ACCEPTED" if correct_pair and semantic_match else "NO_MATCH"
            route_id = (
                "fragment_02_b"
                if "TRIAL_EV_IDENTITY_NOISE" in evidence_ids
                else "fragment_02_a"
            )
            state.final_evidence_ids = list(evidence_ids)
            state.final_reasoning_outcome = outcome
            state.route_id = route_id
            state.completed_events.add("FRAGMENT_01_ROUTE_COMMITTED")
            state.phase_id = (
                FRAGMENT_02_HANDOFF_B if route_id == "fragment_02_b" else FRAGMENT_02_HANDOFF_A
            )
            state.last_outcome = outcome
            return

        if state.phase_id in {FRAGMENT_02_HANDOFF_A, FRAGMENT_02_HANDOFF_B}:
            return
        raise ValueError(f"SUBMIT_REASONING is not allowed during {state.phase_id}")

    def _view(self, state: TrialState) -> dict:
        phase = state.phase_id
        node = None
        interaction: dict[str, Any]
        evidence: list[dict] = []

        if phase == NOT_STARTED:
            interaction = {"kind": "advance", "label": "开始试玩"}
        elif phase == OPENING_INPUT:
            node = self._line(phase)
            interaction = {"kind": "text_input", "label": "发送"}
        elif phase == OPENING_SHATTER:
            node = self._line(phase)
            interaction = {
                "kind": "shatter_puzzle",
                "puzzle_id": "TRIAL_SHATTER_01",
                "shard_ids": list(SHARD_IDS),
            }
        elif phase == OPENING_SERVICE_STOPPED:
            interaction = {
                "kind": "service_stop_modal",
                "message": "AI 停止服务",
                "label": "继续",
            }
        elif phase in {FRAGMENT_01_FIRST_REASONING, FRAGMENT_01_GROUP_REASONING}:
            node = self._line(phase)
            first = phase == FRAGMENT_01_FIRST_REASONING
            evidence = [dict(item) for item in TRIAL_EVIDENCE]
            interaction = {
                "kind": "evidence_orbit",
                "deduction_id": (
                    "TRIAL_DEDUCTION_DEEPSEEK_MEMORY"
                    if first
                    else "TRIAL_DEDUCTION_GROUP_TRUTH"
                ),
                "selection_min": 1,
                "selection_max": 2 if first else 3,
                "allow_retry": first,
            }
        elif phase in {FRAGMENT_02_HANDOFF_A, FRAGMENT_02_HANDOFF_B}:
            node = self._line(phase)
            interaction = {"kind": "complete", "label": "片段 1 完成"}
        else:
            node = self._line(phase)
            interaction = {"kind": "advance", "label": "继续"}

        scene = self._scene_for(phase)
        return {
            "experience_id": TRIAL_ID,
            "started": phase != NOT_STARTED,
            "finished": phase in {FRAGMENT_02_HANDOFF_A, FRAGMENT_02_HANDOFF_B},
            "phase_id": phase,
            "node": node,
            "scene": scene,
            "interaction": interaction,
            "authorized_evidence": evidence,
            "story_tokens": sorted(state.acquired_story_tokens),
            "outcome": state.last_outcome,
            "reasoning_outcome": state.final_reasoning_outcome,
            "route_id": state.route_id,
            "fixture_content": True,
        }

    @staticmethod
    def _line(phase: str) -> dict:
        line = FIXTURE_LINES.get(phase)
        if line is None:
            raise ValueError(f"trial phase has no fixture line: {phase}")
        return {"kind": "line", **line}

    @staticmethod
    def _scene_for(phase: str) -> dict:
        if phase.startswith("opening") or phase == NOT_STARTED:
            scene = TRIAL_SCENES["opening"]
        elif phase in {FRAGMENT_01_DEEPSEEK_INTRO, FRAGMENT_01_FIRST_REASONING}:
            scene = TRIAL_SCENES["fragment_01_deepseek"]
        else:
            scene = TRIAL_SCENES["fragment_01_group"]
        return {
            **scene,
            "characters": [dict(character) for character in scene["characters"]],
        }
