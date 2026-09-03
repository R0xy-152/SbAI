"""看板聚合（docs/21 §5）：纯函数，HTTP 与 CLI 共用同一口径。

所有数字基于原始事件/指标行计算，不跨行猜测；样本小时各指标如实携带 n。
"""

from __future__ import annotations

import math
from collections import Counter

from app.ops.events import (
    EVENT_AI_CHAT_ENTER,
    EVENT_AI_CHAT_ERROR,
    EVENT_AI_CHAT_TURN,
    EVENT_PROLOGUE_COMPLETED,
    EVENT_PROLOGUE_START,
    EVENT_PROLOGUE_VISIT_CHOSEN,
    EVENT_PROLOGUE_VISIT_COMPLETED,
    EVENT_VALIDATION_REJECT,
    ChatMetric,
    OpsEvent,
)

# 漏斗阶段顺序（docs/21 §5）：每会话取最远阶段，相邻差即流失量。
_STAGES = (
    "started",
    "visit_chosen",
    "visit_completed",
    "three_visits",
    "prologue_completed",
    "ai_chat_entered",
)


def _percentile(sorted_values: list[float], p: float) -> float | None:
    """nearest-rank 分位数；空样本返回 None。"""
    if not sorted_values:
        return None
    rank = max(0, math.ceil(p * len(sorted_values)) - 1)
    return sorted_values[rank]


def _session_states(events: list[OpsEvent]) -> dict[str, dict]:
    sessions: dict[str, dict] = {}
    for event in events:
        if not event.session_id:
            continue
        state = sessions.setdefault(
            event.session_id,
            {
                "started": False,
                "chosen": 0,
                "chosen_chars": [],
                "completed_visits": set(),
                "prologue_done": False,
                "chat_entered": False,
            },
        )
        payload = event.payload or {}
        if event.event_name == EVENT_PROLOGUE_START:
            state["started"] = True
        elif event.event_name == EVENT_PROLOGUE_VISIT_CHOSEN:
            state["chosen"] += 1
            char = payload.get("character_id")
            if char:
                state["chosen_chars"].append(char)
        elif event.event_name == EVENT_PROLOGUE_VISIT_COMPLETED:
            char = payload.get("character_id")
            if char:
                state["completed_visits"].add(char)
        elif event.event_name == EVENT_PROLOGUE_COMPLETED:
            state["prologue_done"] = True
        elif event.event_name == EVENT_AI_CHAT_ENTER:
            state["chat_entered"] = True
    return sessions


def _furthest(state: dict) -> str:
    if state["chat_entered"]:
        return "ai_chat_entered"
    if state["prologue_done"]:
        return "prologue_completed"
    if len(state["completed_visits"]) >= 3:
        return "three_visits"
    if state["completed_visits"]:
        return "visit_completed"
    if state["chosen"] >= 1:
        return "visit_chosen"
    return "started"


def compute_funnel(events: list[OpsEvent]) -> dict:
    """序章完成漏斗、每阶段流失量、按角色访问完成率（docs/21 §5）。"""
    sessions = _session_states(events)
    stage_counts = {stage: 0 for stage in _STAGES}
    furthest = Counter()
    for state in sessions.values():
        if not state["started"]:
            continue
        stage = _furthest(state)
        furthest[stage] += 1
        # 阶段 k 的到达数 = 最远阶段 ≥ k 的会话数（累加到最远阶段为止）
        for s in _STAGES:
            stage_counts[s] += 1
            if s == stage:
                break

    chosen: Counter = Counter()
    completed: Counter = Counter()
    for state in sessions.values():
        chosen.update(state["chosen_chars"])
        completed.update(state["completed_visits"])
    characters: dict[str, dict] = {}
    for char in sorted(set(chosen) | set(completed)):
        characters[char] = {
            "chosen": chosen.get(char, 0),
            "completed": completed.get(char, 0),
            "completion_rate": (
                round(completed.get(char, 0) / chosen.get(char, 1), 4)
                if chosen.get(char, 0)
                else None
            ),
        }
    return {
        "total_sessions_with_events": len(sessions),
        "stage_counts": stage_counts,
        "furthest_stage_counts": dict(furthest),
        "characters": characters,
    }


def compute_preferences(events: list[OpsEvent]) -> dict:
    """首访角色分布与聊天角色选择分布（docs/21 §5）。"""
    first_visit: Counter = Counter()
    chat_choice: Counter = Counter()
    for event in events:
        payload = event.payload or {}
        if event.event_name == EVENT_PROLOGUE_VISIT_CHOSEN:
            if payload.get("order") == 1 and payload.get("character_id"):
                first_visit[payload["character_id"]] += 1
        elif event.event_name == EVENT_PROLOGUE_COMPLETED:
            char = payload.get("chat_character_id")
            if char:
                chat_choice[char] += 1
    return {
        "first_visit": dict(first_visit),
        "chat_choice": dict(chat_choice),
    }


def compute_ai_metrics(events: list[OpsEvent], metrics: list[ChatMetric]) -> dict:
    """AI 成功率 / 延迟分位数 / 成本 / 校验拦截（docs/21 §5）。"""
    turns = sum(1 for e in events if e.event_name == EVENT_AI_CHAT_TURN)
    errors = sum(1 for e in events if e.event_name == EVENT_AI_CHAT_ERROR)
    rejected = [
        e
        for e in events
        if e.event_name == EVENT_VALIDATION_REJECT
    ]
    gates = Counter((e.payload or {}).get("gate", "unknown") for e in rejected)

    latencies = sorted(m.latency_ms for m in metrics)
    n = len(latencies)
    total_cost = sum(m.cost_cny for m in metrics)
    entered_sessions = {
        e.session_id
        for e in events
        if e.event_name == EVENT_AI_CHAT_ENTER and e.session_id
    }
    providers = Counter(m.provider for m in metrics)
    return {
        "turn_count": turns,
        "error_count": errors,
        "success_rate": round(turns / (turns + errors), 4) if (turns + errors) else None,
        "validation_reject_count": len(rejected),
        "validation_reject_by_gate": dict(gates),
        "latency": {
            "n": n,
            "p50_ms": _percentile(latencies, 0.5),
            "p95_ms": _percentile(latencies, 0.95),
        },
        "cost": {
            "total_cny": round(total_cost, 6),
            "complete_sessions": len(entered_sessions),
            "avg_per_complete_session_cny": (
                round(total_cost / len(entered_sessions), 6)
                if entered_sessions
                else None
            ),
        },
        "providers": dict(providers),
    }
