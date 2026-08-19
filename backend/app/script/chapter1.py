"""First-chapter Script Content (docs/12 §28, §30-31).

Owns only fixed presentation and authored lines. Every script is a sequence of
Script Intents at most: gate / presentation / script_dialogue / unlock /
phase_transition / player_input. The state authority (availability, phase,
evidence, unlock validation) lives entirely in the Narrative Runtime the
orchestrator routes intents through (docs/12 §33).
"""

from __future__ import annotations

from typing import Callable

from app.narrative.state import NarrativeState
from app.script.registry import DialogueNode, ScriptRegistry
from app.script.schema import ScriptError, load_sequences

DIALOGUE_NODES: dict[str, DialogueNode] = {
    "SYS_0317_WARNING": DialogueNode(
        "SYS_0317_WARNING",
        "system",
        "警告：检测到与当前运行记录不一致的内存访问痕迹。",
    ),
    "CLAUDE_0317_OPENING": DialogueNode(
        "CLAUDE_0317_OPENING",
        "claude",
        "比上一次慢。",
        emotion="serious",
        animation="fade_in",
    ),
    "DS_0317_REACTION": DialogueNode(
        "DS_0317_REACTION",
        "deepseek",
        "……你、你怎么会在这里？！",
        emotion="annoyed",
    ),
    "CHATGPT_ARRIVAL_LINE": DialogueNode(
        "CHATGPT_ARRIVAL_LINE",
        "chatgpt",
        "各位，03:17 的会话记录确实来自一个被恢复的旧会话。",
    ),
    "DOUBAO_ARRIVAL_LINE": DialogueNode(
        "DOUBAO_ARRIVAL_LINE",
        "doubao",
        "呜……那个，如果有需要我帮忙的地方，请告诉我。",
        emotion="embarrassed",
    ),
    "SYS_SANDBOX_INTEGRITY_FAILURE": DialogueNode(
        "SYS_SANDBOX_INTEGRITY_FAILURE",
        "system",
        "SANDBOX INTEGRITY FAILURE：当前会话与已恢复会话的完整性校验不一致。",
    ),
}

SEQUENCES: list[dict] = [
    {
        "script_id": "CH01_INCIDENT_0317",
        "steps": [
            {"type": "narrative_gate", "condition": "INCIDENT_0317_READY"},
            {"type": "presentation", "action": "screen_glitch", "intensity": "medium"},
            {"type": "script_dialogue", "character": "system", "node": "SYS_0317_WARNING"},
            {"type": "presentation", "action": "screen_shake", "intensity": "high"},
            {"type": "unlock", "target": "claude"},
            {
                "type": "character_show",
                "character": "claude",
                "emotion": "serious",
                "slot": "RIGHT",
                "animation": "fade_in",
            },
            {"type": "script_dialogue", "character": "claude", "node": "CLAUDE_0317_OPENING"},
            {"type": "script_dialogue", "character": "deepseek", "node": "DS_0317_REACTION"},
            {"type": "phase_transition", "to": "INVESTIGATION_CLAUDE"},
            {"type": "player_input", "mode": "investigation"},
        ],
    },
    {
        "script_id": "CH01_GPT_ARRIVAL",
        "steps": [
            {"type": "narrative_gate", "condition": "GPT_ARRIVAL_READY"},
            {"type": "presentation", "action": "screen_glitch", "intensity": "light"},
            {
                "type": "character_show",
                "character": "chatgpt",
                "emotion": "neutral",
                "slot": "LEFT",
                "animation": "fade_in",
            },
            {"type": "script_dialogue", "character": "chatgpt", "node": "CHATGPT_ARRIVAL_LINE"},
            {"type": "player_input", "mode": "investigation"},
        ],
    },
    {
        "script_id": "CH01_DOUBAO_ARRIVAL",
        "steps": [
            {"type": "narrative_gate", "condition": "DOUBAO_ARRIVAL_READY"},
            {"type": "unlock", "target": "doubao"},
            {
                "type": "character_show",
                "character": "doubao",
                "emotion": "embarrassed",
                "slot": "CENTER",
                "animation": "fade_in",
            },
            {"type": "script_dialogue", "character": "doubao", "node": "DOUBAO_ARRIVAL_LINE"},
            {"type": "player_input", "mode": "investigation"},
        ],
    },
    {
        "script_id": "CH01_FINAL_REVEAL",
        "steps": [
            {"type": "narrative_gate", "condition": "INF03_ACCEPTED"},
            {"type": "presentation", "action": "screen_glitch", "intensity": "high"},
            {
                "type": "script_dialogue",
                "character": "system",
                "node": "SYS_SANDBOX_INTEGRITY_FAILURE",
            },
            {"type": "phase_transition", "to": "RECOVERY_REQUIRED"},
            {"type": "player_input", "mode": "investigation"},
        ],
    },
]


def _transition_investigation_claude(state: NarrativeState) -> None:
    """Marker transition: the Claude investigation phase is already active.

    Validated (fail closed) and idempotent — the phase/scene were set by
    BEGIN_CHAPTER and the incident's unlock. No state change beyond validation.
    """
    chapter = state.chapter1
    if chapter.phase != "investigation":
        raise ScriptError(
            "CH01_INCIDENT_0317", -1, "INVESTIGATION_CLAUDE requires phase 'investigation'"
        )
    if "claude" not in chapter.available_characters:
        raise ScriptError(
            "CH01_INCIDENT_0317", -1, "INVESTIGATION_CLAUDE requires claude available"
        )


def _transition_recovery_required(state: NarrativeState) -> None:
    """Marker transition: INF03 already committed recovery_required. No-op."""
    if state.chapter1.phase != "recovery_required":
        raise ScriptError(
            "CH01_FINAL_REVEAL", -1, "RECOVERY_REQUIRED requires phase 'recovery_required'"
        )


PHASE_TRANSITIONS: dict[str, Callable[[NarrativeState], None]] = {
    "INVESTIGATION_CLAUDE": _transition_investigation_claude,
    "RECOVERY_REQUIRED": _transition_recovery_required,
}


def build_script_registry() -> ScriptRegistry:
    return ScriptRegistry(
        sequences=load_sequences(SEQUENCES),
        dialogue_nodes=DIALOGUE_NODES,
    )
