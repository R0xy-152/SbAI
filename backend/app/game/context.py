"""Character Context Builder (docs/04 §15-17).

The Context Builder is the permission boundary between Backend State and a
generative character's context: it selects only what the character is
authorized to know. For DeepSeek, visual Scene facts are excluded (docs/04
§20): she cannot see, so `wall_code` and any other visual ground truth stay
in the Scene and never enter her context. Legal non-visual perceptions
(sounds, docs/04 §20.1) may pass; player-described information already lives
in the recent conversation and needs no extra injection.

This is the layer to inspect first if a character ever "knows" something it
should not (docs/06 TV-08 FAIL含义).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.game.scene import Scene


@dataclass
class CharacterContext:
    """The authorized context lines the character may see this turn."""

    environment_info: str = ""


def build_deepseek_context(scene: Scene) -> CharacterContext:
    """DeepSeek's authorized narrative context (docs/04 §20).

    Visual scene facts (wall_code, …) are deliberately never read into the
    context; only legal non-visual perceptions pass.
    """
    lines: list[str] = []
    if scene.sounds:
        lines.append("你听见：" + "、".join(scene.sounds))
    return CharacterContext(environment_info="\n".join(lines))


def build_claude_context(scene: Scene) -> CharacterContext:
    """Claude's authorized narrative context (docs/04 §35-39, docs/05 §28).

    Claude is not blind: unlike DeepSeek, she may know the scene's visual
    ground truth. She also perceives the same legal non-visual sounds.
    """
    lines: list[str] = []
    if scene.sounds:
        lines.append("你听见：" + "、".join(scene.sounds))
    lines.append(f"房间的墙上写着一个数字：{scene.wall_code}")
    return CharacterContext(environment_info="\n".join(lines))


# Character-specific Context Builders (docs/04 §15). One entry per generative
# character; each character's permission boundary is enforced here, not in
# the persona prompt.
CONTEXT_BUILDERS: dict[str, Callable[[Scene], CharacterContext]] = {
    "deepseek": build_deepseek_context,
    "claude": build_claude_context,
}
