"""Formal authored Script content for Chapter One (docs/12)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptSequenceLine:
    speaker: str
    dialogue: str
    emotion: str = "neutral"
    animation: str = "none"


# CH1-N03 — one formal, deterministic sequence. Its state transition remains
# in Chapter1ScriptRuntime; this module owns only authored presentation text.
CH1_N03_CLAUDE_INCIDENT_SEQUENCE = (
    ScriptSequenceLine("claude", "比上一次慢。", emotion="serious", animation="fade_in"),
    ScriptSequenceLine("deepseek", "……你、你怎么会在这里？！", emotion="annoyed"),
)
