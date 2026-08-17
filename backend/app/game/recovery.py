"""Deterministic turn-based Recovery game (docs/07)."""

from __future__ import annotations

from app.narrative.state import NarrativeState

NODES = ("CORE", "WORLD", "MEMORY", "CHARACTER", "AUTH", "EXIT")
CRITICAL = frozenset({"CORE", "WORLD", "MEMORY", "CHARACTER", "AUTH"})
GPT_THRESHOLD = 2


def start(state: NarrativeState) -> dict:
    chapter = state.chapter1
    if "INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE" not in chapter.accepted_inferences:
        raise ValueError("Recovery requires the V03/V04 inference")
    chapter.phase = "recovery"
    chapter.recovery_status = "active"
    chapter.recovery = {"nodes": {node: "CORRUPTED" for node in NODES}, "protected": [], "gpt_delegated_privilege": 0, "human_credential_restored": False}
    state.current_scene = "RECOVERY_CORE"
    state.story_phase = "chapter1_recovery"
    return view(state)


def act(state: NarrativeState, action: str, target: str, actor: str = "player") -> dict:
    chapter = state.chapter1
    game = chapter.recovery
    if chapter.recovery_status != "active" or target not in NODES:
        raise ValueError("Recovery action is unavailable")
    nodes = game["nodes"]
    if action == "PREVIEW" and actor == "deepseek":
        game["preview"] = target
    elif action == "VERIFY" and actor == "claude":
        nodes[target] = "UNVERIFIED"
    elif action == "PROTECT" and actor == "doubao":
        if target not in game["protected"]:
            game["protected"].append(target)
    elif action == "REPAIR" and actor == "player":
        if nodes[target] != "UNVERIFIED":
            return {**view(state), "outcome": "RETRY"}
        nodes[target] = "RECOVERED"
        if target == "AUTH":
            game["human_credential_restored"] = True
    elif action == "OPTIMIZE" and actor == "chatgpt":
        game["gpt_delegated_privilege"] += 1
        nodes[target] = "RECOVERED"
        for node in NODES:
            if nodes[node] == "CORRUPTED":
                nodes[node] = "RECOVERED"
                break
    else:
        raise ValueError("invalid Recovery action")
    _finish_if_ready(state)
    return {**view(state), "outcome": "APPLIED"}


def _finish_if_ready(state: NarrativeState) -> None:
    chapter = state.chapter1
    game = chapter.recovery
    if not all(game["nodes"][node] == "RECOVERED" for node in CRITICAL):
        return
    delegated = game["gpt_delegated_privilege"]
    if delegated >= GPT_THRESHOLD:
        chapter.admin_holder = "chatgpt"
    elif game["human_credential_restored"]:
        chapter.admin_holder = "player"
    else:
        return
    chapter.recovery_status = "resolved"
    state.active_objective = "进入最终 Security Review"


def view(state: NarrativeState) -> dict:
    return dict(state.chapter1.recovery)
