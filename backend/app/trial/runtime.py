"""Deterministic trial_v2 state machine behind one small command interface.

Runtime and content are fully separated (docs/24): every line, scene, evidence,
deduction/judgment rule, transition target, literal and checkpoint lives in
app.trial.content, which is fail-closed validated at import.  This module only
executes that validated table; swapping the real script means editing content,
never this file.

External contract: TrialState snapshot/restore shape, the bounded commands
(ADVANCE / PLAYER_INPUT / COMPLETE_SHATTER / SUBMIT_REASONING /
PERMISSION_RESPONSE / CHOOSE / SUBMIT_JUDGMENT), idempotency by command_id,
checkpoint-on-enter semantics and the TrialView shape consumed by
frontend-vue/src/api/trial.ts.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from app.trial.content import (
    CHECKPOINT_PHASE_IDS,
    DEDUCTIONS_BY_ID,
    ENDING_IDS,
    EVIDENCE,
    EVIDENCE_IDS,
    JUDGMENTS_BY_ID,
    NOT_STARTED,
    PHASES_BY_ID,
    PHASE_IDS,
    SCENES_BY_ID,
    TERMINAL_PHASE_IDS,
    TOKEN_IDS,
    TRIAL_CONTENT,
    TRIAL_ID,
)

# Mechanical validation tolerances (not authored content; docs/24 §5.2).
SHARD_POSITION_TOLERANCE = 0.035
SHARD_ROTATION_TOLERANCE = 4.0

# docs/27 §4「延迟即情感」：reply_delay_ms 由 autonomy 派生（表现层提示）。
_REPLY_DELAY_MS_PER_LEVEL = 500

# Events whose names come from content; collected once so late duplicate
# COMPLETE_SHATTER / PLAYER_INPUT requests stay silent no-ops (as before).
SHATTER_EVENTS: tuple[str, ...] = tuple(
    event
    for phase in PHASES_BY_ID.values()
    for event in (phase.get("shatter_events") or ())
)


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
    # docs/27 §4/§5/§6 state
    autonomy_level: int = 0
    granted_permissions: list[str] = field(default_factory=list)
    intent_outcomes: list[dict] = field(default_factory=list)
    ending: str | None = None
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
    """Owns every trial_v2 transition; callers only submit bounded commands."""

    def __init__(self) -> None:
        self._states: dict[str, TrialState] = {}

    def started(self, session_id: str) -> bool:
        state = self._states.get(session_id)
        return state is not None and state.phase_id != NOT_STARTED

    def finished(self, session_id: str) -> bool:
        state = self._states.get(session_id)
        return state is not None and state.phase_id in TERMINAL_PHASE_IDS

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
        elif command_type == "PERMISSION_RESPONSE":
            self._permission_response(state, command.get("permission_id"), command.get("grant"))
        elif command_type == "CHOOSE":
            self._choose(state, command.get("option_id"))
        elif command_type == "SUBMIT_JUDGMENT":
            self._submit_judgment(state, command.get("judgment_id"), command.get("message"))
        else:
            raise ValueError(f"unknown trial command type {command_type!r}")

        state.last_command_id = command_id
        changed = before_phase != state.phase_id or command_type in {
            "SUBMIT_REASONING",
            "SUBMIT_JUDGMENT",
        }
        checkpoint = before_phase != state.phase_id and state.phase_id in CHECKPOINT_PHASE_IDS
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
            autonomy_level=int(snapshot.get("autonomy_level", 0)),
            granted_permissions=list(snapshot.get("granted_permissions", [])),
            intent_outcomes=deepcopy(snapshot.get("intent_outcomes", [])),
            ending=snapshot.get("ending"),
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
        if phase not in PHASE_IDS or phase == NOT_STARTED:
            raise ValueError(f"unknown trial phase: {phase!r}")
        evidence_ids = snapshot.get("final_evidence_ids", [])
        if not isinstance(evidence_ids, list) or any(
            evidence_id not in EVIDENCE_IDS for evidence_id in evidence_ids
        ):
            raise ValueError("trial_state contains unknown evidence ids")
        tokens = set(snapshot.get("acquired_story_tokens", []))
        if not tokens.issubset(TOKEN_IDS):
            raise ValueError("trial_state contains unknown story tokens")
        autonomy = snapshot.get("autonomy_level", 0)
        if not isinstance(autonomy, int) or not 0 <= autonomy <= 3:
            raise ValueError("trial_state autonomy_level must be 0..3")
        permissions = snapshot.get("granted_permissions", [])
        if not isinstance(permissions, list) or any(
            not isinstance(pid, str) for pid in permissions
        ):
            raise ValueError("trial_state granted_permissions must be strings")
        ending = snapshot.get("ending")
        if ending not in {None, *ENDING_IDS}:
            raise ValueError("trial_state contains unknown ending")

    # ── command handlers ───────────────────────────────────────────────

    def _advance(self, state: TrialState) -> None:
        row = PHASES_BY_ID[state.phase_id]
        target = row.get("advance_to")
        if target is None:
            raise ValueError(f"ADVANCE is not allowed during {state.phase_id}")
        self._enter(state, target)
        state.last_outcome = None

    def _player_input(self, state: TrialState, message: Any) -> None:
        row = PHASES_BY_ID[state.phase_id]
        target = row.get("player_input_to")
        if target is None:
            raise ValueError(f"PLAYER_INPUT is not allowed during {state.phase_id}")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("player input must not be empty")
        if len(message) > 2000:
            raise ValueError("player input is too long")
        answer = row.get("player_input_answer")
        if answer is not None and message.strip() != answer:
            raise ValueError("密码不正确，再看看纸上的字。")
        for event in row.get("player_input_events") or ():
            state.completed_events.add(event)
        self._enter(state, target)
        state.last_outcome = "ACCEPTED"

    def _complete_shatter(self, state: TrialState, shards: Any) -> None:
        if any(event in state.completed_events for event in SHATTER_EVENTS):
            return
        row = PHASES_BY_ID[state.phase_id]
        target = row.get("shatter_to")
        if target is None:
            raise ValueError(f"COMPLETE_SHATTER is not allowed during {state.phase_id}")
        shard_ids = tuple(row["interaction"].get("shard_ids", ()))
        if not isinstance(shards, list) or len(shards) != len(shard_ids):
            raise ValueError(f"exactly {len(shard_ids)} shard poses are required")
        by_id = {pose.get("shard_id"): pose for pose in shards if isinstance(pose, dict)}
        if set(by_id) != set(shard_ids):
            raise ValueError("shard poses must contain the unique shard ids")
        for shard_id in shard_ids:
            pose = by_id[shard_id]
            try:
                x = float(pose["x"])
                y = float(pose["y"])
                rotation = float(pose["rotation"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid shard pose") from exc
            if (
                abs(x) > SHARD_POSITION_TOLERANCE
                or abs(y) > SHARD_POSITION_TOLERANCE
                or abs(rotation) > SHARD_ROTATION_TOLERANCE
            ):
                raise ValueError(f"shard {shard_id} is outside the snap tolerance")
        for event in row.get("shatter_events") or ():
            state.completed_events.add(event)
        # docs/27 §4：修复 1 后 autonomy 0→1（幂等，不会倒退）。
        state.autonomy_level = max(state.autonomy_level, 1)
        self._enter(state, target)
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
        if any(evidence_id not in EVIDENCE_IDS for evidence_id in evidence_ids):
            raise ValueError("unknown or unauthorized trial evidence")

        normalized = message.lower().replace(" ", "")
        row = PHASES_BY_ID[state.phase_id]
        # Terminal phases accept (and ignore) late submissions (no dead end).
        if row["interaction"].get("kind") == "complete":
            return
        if row.get("deduction_id") is None:
            raise ValueError(f"SUBMIT_REASONING is not allowed during {state.phase_id}")
        if deduction_id != row["deduction_id"]:
            raise ValueError("unexpected deduction id")
        config = DEDUCTIONS_BY_ID[row["deduction_id"]]
        if len(evidence_ids) > config["evidence_max"]:
            raise ValueError(
                f"{row['deduction_id']} accepts at most "
                f"{config['evidence_max']} evidence items"
            )

        selected = set(evidence_ids)
        # docs/25 §3：否定/矛盾短语命中即拒绝；判定式=证据门 AND 关键词 AND 非否定。
        accepted = (
            set(config["evidence_gate_required"]).issubset(selected)
            and any(
                term in normalized
                for term in config["text_keywords_any"]
            )
            and not any(
                term in normalized
                for term in config.get("text_keywords_none", ())
            )
        )
        outcome = (
            config["accept"]["outcome"] if accepted else config["reject"]["outcome"]
        )
        if config.get("records_attempts"):
            state.first_deduction_attempts.append(
                {"evidence_ids": list(evidence_ids), "outcome": outcome}
            )

        if config.get("final"):
            # Every final submission commits and advances to next_phase
            # (reasoning correctness and ending are separate results).
            state.final_evidence_ids = list(evidence_ids)
            state.final_reasoning_outcome = outcome
            state.last_outcome = outcome
            for event in config.get("commit_events", ()):
                state.completed_events.add(event)
            self._enter(state, config["next_phase"])
            return

        if accepted:
            accept = config["accept"]
            flag = accept.get("flag")
            if flag is not None:
                setattr(state, flag, True)
            for event in accept.get("events", ()):
                state.completed_events.add(event)
            self._enter(state, accept["next_phase"])
        state.last_outcome = outcome

    def _permission_response(
        self, state: TrialState, permission_id: Any, grant: Any
    ) -> None:
        row = PHASES_BY_ID[state.phase_id]
        interaction = row.get("interaction") or {}
        if interaction.get("kind") != "permission_request":
            raise ValueError(
                f"PERMISSION_RESPONSE is not allowed during {state.phase_id}"
            )
        if permission_id != interaction.get("permission_id"):
            raise ValueError("unexpected permission id")
        if not isinstance(grant, bool):
            raise ValueError("grant must be a boolean")
        if grant and permission_id not in state.granted_permissions:
            # docs/27 §4/§5：每授予一项 autonomy +1（幂等）。
            state.granted_permissions.append(permission_id)
            state.autonomy_level = min(3, state.autonomy_level + 1)
            state.completed_events.add("PERMISSION_GRANTED")
        state.last_outcome = "GRANTED" if grant else "DENIED"
        # 授权/拒绝都推进（无死路）。
        self._enter(state, row["permission_to"])

    def _choose(self, state: TrialState, option_id: Any) -> None:
        row = PHASES_BY_ID[state.phase_id]
        interaction = row.get("interaction") or {}
        if interaction.get("kind") != "choice":
            raise ValueError(f"CHOOSE is not allowed during {state.phase_id}")
        options = interaction.get("options", ())
        option_ids = [option.get("option_id") for option in options]
        if option_id not in option_ids:
            raise ValueError("unknown choice option")
        option_targets = interaction.get("option_targets")
        if option_targets is not None:
            # terminal three-way choice → commit ending
            target = option_targets[option_id]
            ending = target.removeprefix("ending_")
            state.ending = ending
            for event in (interaction.get("commit_event"),):
                if event is not None:
                    state.completed_events.add(event)
            state.last_outcome = ending
            self._enter(state, target)
            return
        # gate-style choice: correct → advance, wrong → soft fail (no checkpoint)
        if option_id == interaction.get("correct_option_id"):
            for event in (interaction.get("pass_event"),):
                if event is not None:
                    state.completed_events.add(event)
            state.last_outcome = "ACCEPTED"
            self._enter(state, interaction["correct_to"])
        else:
            for event in (interaction.get("fail_event"),):
                if event is not None:
                    state.completed_events.add(event)
            state.last_outcome = "NO_MATCH"
            self._enter(state, interaction["fail_to"])

    def _submit_judgment(
        self, state: TrialState, judgment_id: Any, message: Any
    ) -> None:
        row = PHASES_BY_ID[state.phase_id]
        interaction = row.get("interaction") or {}
        if interaction.get("kind") != "judgment":
            raise ValueError(f"SUBMIT_JUDGMENT is not allowed during {state.phase_id}")
        if judgment_id != interaction.get("judgment_id"):
            raise ValueError("unexpected judgment id")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("judgment message must not be empty")
        if len(message) > 4000:
            raise ValueError("judgment message is too long")
        config = JUDGMENTS_BY_ID[judgment_id]
        bucket = self._classify_bucket(message, config)
        state.intent_outcomes.append(
            {"judgment_id": judgment_id, "bucket_id": bucket}
        )
        commit_event = config.get("commit_event")
        if commit_event is not None:
            state.completed_events.add(commit_event)
        state.last_outcome = bucket
        self._enter(state, config["next_phase"])

    @staticmethod
    def _classify_bucket(message: str, config: dict[str, Any]) -> str:
        normalized = message.lower().replace(" ", "")
        for bucket in config["buckets"]:
            if any(term in normalized for term in bucket.get("keywords_any", ())):
                if not any(
                    term in normalized for term in bucket.get("keywords_none", ())
                ):
                    return bucket["bucket_id"]
        return config["fallback_bucket"]

    @staticmethod
    def _enter(state: TrialState, phase_id: str) -> None:
        destination = PHASES_BY_ID[phase_id]
        state.phase_id = phase_id
        on_enter = destination.get("on_enter")
        if on_enter is not None:
            for event in on_enter.get("events", ()):
                state.completed_events.add(event)
            for token in on_enter.get("tokens", ()):
                state.acquired_story_tokens.add(token)

    # ── view ───────────────────────────────────────────────────────────

    def _view(self, state: TrialState) -> dict:
        row = PHASES_BY_ID[state.phase_id]
        interaction = deepcopy(row["interaction"])
        if interaction["kind"] == "evidence_orbit":
            config = DEDUCTIONS_BY_ID[interaction["deduction_id"]]
            interaction.update(
                {
                    "selection_min": config["evidence_min"],
                    "selection_max": config["evidence_max"],
                    "allow_retry": config["allow_retry"],
                    "seed": config["orbit_seed"],
                }
            )
        node = None
        line_id = row.get("line_id")
        if line_id is not None:
            node = {"kind": "line", **TRIAL_CONTENT["lines"][line_id]}
        return {
            "experience_id": TRIAL_ID,
            "started": state.phase_id != NOT_STARTED,
            "finished": state.phase_id in TERMINAL_PHASE_IDS,
            "phase_id": state.phase_id,
            "node": node,
            "scene": deepcopy(SCENES_BY_ID[row["scene_id"]]),
            "interaction": interaction,
            "authorized_evidence": (
                [dict(item) for item in EVIDENCE]
                if interaction["kind"] == "evidence_orbit"
                else []
            ),
            "story_tokens": sorted(state.acquired_story_tokens),
            "outcome": state.last_outcome,
            "reasoning_outcome": state.final_reasoning_outcome,
            "ending": state.ending,
            "reply_delay_ms": state.autonomy_level * _REPLY_DELAY_MS_PER_LEVEL,
            "fixture_content": bool(TRIAL_CONTENT["fixture_content"]),
        }
