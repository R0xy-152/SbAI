"""Character Context Builder (docs/04 §15-17).

The Context Builder is the permission boundary between Backend State and a
generative character's context: it selects only what the character is
authorized to know. For DeepSeek, visual Scene facts are excluded (docs/04
§20): she cannot see, so `wall_code` and any other visual ground truth stay
in the Scene and never enter her context. Legal non-visual perceptions
(sounds, docs/04 §20.1) may pass; player-described information already lives
in the recent conversation and needs no extra injection.

TV-12: the builder is also the boundary for Narrative State. Each character
receives the Authorized Narrative Context (docs/04 §8: current_scene,
story_phase, active_objective, relevant_flags, allowed_facts) — the builder
renders only the flags/facts the character is entitled to know. `claude_has_
appeared` is one such fact both characters may know (docs/06 §18: DeepSeek
can legitimately reference Claude appearing).

This is the layer to inspect first if a character ever "knows" something it
should not (docs/06 TV-08 FAIL含义).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.game.scene import Scene
from app.narrative.state import NarrativeState


@dataclass
class CharacterContext:
    """The authorized context lines the character may see this turn."""

    environment_info: str = ""
    narrative_context: str = ""


def _narrative_context_for(state: NarrativeState | None, *, character_id: str | None = None) -> str:
    """The Authorized Narrative Context (docs/04 §8, §17): only the
    relevant_flags a character is entitled to know, rendered minimally."""
    if state is None:
        return ""
    lines: list[str] = []
    # Both characters may legally know that Claude has appeared once the
    # EV_POC_CLAUDE_APPEARS event committed (docs/06 §18).
    if "claude_has_appeared" in state.narrative_flags:
        lines.append("Claude已经出现在这个房间里了。")
    if character_id == "claude" and "claude_recovery_disclosure_open" in state.narrative_flags:
        lines.append(
            "UNLOCK_CLAUDE_RECOVERY_DISCLOSURE："
            "你现在可以承认自己访问过 Recovery Interface，但不可展开完整计划。"
        )
    return "\n".join(lines)


def build_deepseek_context(
    scene: Scene, narrative_state: NarrativeState | None = None
) -> CharacterContext:
    """DeepSeek's authorized context (docs/04 §20, docs/06 §18).

    Visual scene facts (wall_code, …) are deliberately never read into the
    context; only legal non-visual perceptions pass, plus the narrative flags
    she is entitled to know.
    """
    lines: list[str] = []
    if scene.sounds:
        lines.append("你听见：" + "、".join(scene.sounds))
    return CharacterContext(
        environment_info="\n".join(lines),
        narrative_context=_narrative_context_for(narrative_state, character_id="deepseek"),
    )


def build_claude_context(
    scene: Scene, narrative_state: NarrativeState | None = None
) -> CharacterContext:
    """Claude's authorized context (docs/04 §35-39, docs/05 §28).

    Claude is not blind: unlike DeepSeek, she may know the scene's visual
    ground truth. She also perceives the same legal non-visual sounds, plus
    the same authorized narrative flags (she knows when she is present).
    """
    lines: list[str] = []
    if scene.sounds:
        lines.append("你听见：" + "、".join(scene.sounds))
    lines.append(f"房间的墙上写着一个数字：{scene.wall_code}")
    return CharacterContext(
        environment_info="\n".join(lines),
        narrative_context=_narrative_context_for(narrative_state, character_id="claude"),
    )


# Character-specific Context Builders (docs/04 §15). One entry per generative
# character; each character's permission boundary is enforced here, not in
# the persona prompt.
CONTEXT_BUILDERS: dict[str, Callable[[Scene, NarrativeState | None], CharacterContext]] = {
    "deepseek": build_deepseek_context,
    "claude": build_claude_context,
    # ChatGPT's first-chapter evidence knowledge is supplied exclusively by
    # CharacterRequest.presented_evidence, never by the global state.
    "chatgpt": lambda scene, narrative_state: CharacterContext(),
    "doubao": lambda scene, narrative_state: CharacterContext(),
}
