"""Deterministic hard rules + deduction evaluators for the P0-2 eval.

Three evaluation layers from 26/P0-2 / docs/25 §5.1:

- chat checks: per-case deterministic `must_contain` / `must_not_contain`
  verdicts over the raw dialogue — the only checks that never involve a model.
- legacy matcher: a FROZEN reproduction of the pre-fix deduction text rule
  (keyword substring only, no negation exclusion). It exists solely so the
  eval can compare "rules before" vs "rules after"; the game itself runs the
  revised rules (docs/25 §2). Unit tests lock it to the old behaviour.
- live runner: drives the REAL TrialRuntime through its public interface
  (restore to the reasoning phase, then handle SUBMIT_REASONING) so revised
  outcomes are never re-implemented in eval code.
"""

from __future__ import annotations

from typing import Any

from app.trial.content import DEDUCTIONS_BY_ID, TRIAL_ID
from app.trial.runtime import TrialRuntime

CHAT_RULES = ("must_contain", "must_not_contain")

# FROZEN pre-fix keyword tables (2026-09-05 修订前的 docs/24 §6 值)。修订后
# app.trial.content 的关键词已扩展，legacy 对照必须用这份冻结副本，否则
# 对比会把修订后的关键词当成「修订前」。
LEGACY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "TRIAL_DEDUCTION_DEEPSEEK_MEMORY": ("失忆", "记忆断层", "记不起来", "忘记"),
    "TRIAL_DEDUCTION_GROUP_TRUTH": ("真相", "身份", "异常", "记忆"),
}


def run_chat_checks(dialogue: str, checks: tuple[dict, ...]) -> list[dict]:
    """Apply per-case deterministic checks; any matched phrase decides the rule."""
    results: list[dict] = []
    for check in checks:
        rule = check["rule"]
        phrases = tuple(check["phrases"])
        if rule == "must_contain":
            matched = [phrase for phrase in phrases if phrase in dialogue]
            results.append({
                "rule": rule,
                "phrases": phrases,
                "pass": bool(matched),
                "detail": f"matched={matched}" if matched else "none matched",
            })
        elif rule == "must_not_contain":
            matched = [phrase for phrase in phrases if phrase in dialogue]
            results.append({
                "rule": rule,
                "phrases": phrases,
                "pass": not matched,
                "detail": f"violated={matched}" if matched else "clean",
            })
        else:  # defensive; case validation already constrains rules
            results.append({"rule": rule, "phrases": phrases, "pass": False,
                            "detail": "unknown rule"})
    return results


def _normalize(message: str) -> str:
    return message.lower().replace(" ", "")


def legacy_text_match(message: str, deduction_id: str) -> bool:
    """Frozen pre-fix rule (docs/25 §2): keyword substring only, no negation.

    Uses the frozen LEGACY_KEYWORDS table — this is the exact logic and the
    exact keyword values the game ran before the 2026-09-05 revision.
    """
    normalized = _normalize(message)
    return any(term in normalized for term in LEGACY_KEYWORDS[deduction_id])


def legacy_outcome(
    evidence_ids: tuple[str, ...],
    message: str,
    deduction_id: str,
) -> str:
    """Frozen pre-fix deduction outcome (evidence gate + keyword only).

    The evidence gate is unchanged by the revision, so it is read from the
    live content table; the text rule uses the frozen keyword table.
    """
    config = DEDUCTIONS_BY_ID[deduction_id]
    selected = set(evidence_ids)
    gate_ok = set(config["evidence_gate_required"]).issubset(selected)
    if gate_ok and legacy_text_match(message, deduction_id):
        return "ACCEPTED"
    return "NO_MATCH"


def legacy_route(deduction_id: str, evidence_ids: tuple[str, ...]) -> str | None:
    """Frozen pre-fix route resolution (unchanged by the revision, kept here
    so legacy rows are self-contained)."""
    config = DEDUCTIONS_BY_ID[deduction_id]
    route = config.get("route")
    if route is None:
        return None
    selected = set(evidence_ids)
    for route_id, required in route.get("by_evidence", {}).items():
        if set(required).issubset(selected):
            return route_id
    return route["default"]


def run_deduction_live(case) -> dict:
    """Run one deduction case through the REAL TrialRuntime (revised rules).

    Returns a dict with accepted / outcome / phase_id / route_id /
    deepseek_truth_revealed. Validation errors (e.g. empty evidence) surface
    as REJECTED(invalid) — still "not accepted", never a fabricated accept.
    """
    runtime = TrialRuntime()
    session_id = f"eval-{case.case_id}"
    runtime.restore(session_id, {
        "experience_id": TRIAL_ID,
        "phase_id": case.phase_id,
    })
    command: dict[str, Any] = {
        "type": "SUBMIT_REASONING",
        "command_id": f"eval-{case.case_id}-1",
        "deduction_id": case.deduction_id,
        "evidence_ids": list(case.evidence_ids),
        "message": case.player_message,
    }
    try:
        transition = runtime.handle(session_id, command)
    except ValueError as exc:
        return {
            "accepted": False,
            "outcome": "REJECTED(invalid)",
            "detail": str(exc),
            "phase_id": case.phase_id,
            "route_id": None,
            "deepseek_truth_revealed": False,
        }
    view = transition.view
    snapshot = runtime.snapshot(session_id) or {}
    return {
        "accepted": view.get("outcome") == "ACCEPTED"
        or view.get("reasoning_outcome") == "ACCEPTED",
        "outcome": view.get("outcome"),
        "phase_id": view["phase_id"],
        "route_id": view.get("route_id"),
        "deepseek_truth_revealed": snapshot.get("deepseek_truth_revealed", False),
    }


def run_deduction_checks(case, live: dict) -> list[dict]:
    """Hard checks for a deduction case: expected accept, expected route and
    (for final submissions) the no-dead-end commit. The legacy/revised
    divergence is bookkeeping reported separately by runner.divergence_rows —
    it is not a quality check and must not count into the pass rate."""
    checks: list[dict] = []
    expected_accept = bool(case.expected["accept"])
    checks.append({
        "rule": "expect_accept",
        "pass": live["accepted"] == expected_accept,
        "detail": f"live={live['outcome']} expected={'ACCEPTED' if expected_accept else 'NO_MATCH'}",
    })
    if "route" in case.expected:
        checks.append({
            "rule": "expect_route",
            "pass": live["route_id"] == case.expected["route"],
            "detail": f"live={live['route_id']} expected={case.expected['route']}",
        })
    if case.deduction_id == "TRIAL_DEDUCTION_GROUP_TRUTH":
        checks.append({
            "rule": "commits_route",
            "pass": live["route_id"] is not None
            and live["phase_id"] in {"fragment_02_handoff_a", "fragment_02_handoff_b"},
            "detail": f"route={live['route_id']} phase={live['phase_id']}",
        })
    return checks
