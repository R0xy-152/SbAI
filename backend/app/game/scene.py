"""Scene model — the room's facts owned by the backend (docs/03 §5.1).

A Scene holds ground truth about the current room, including visual facts
such as `wall_code`. Visual facts are forbidden knowledge for DeepSeek
(docs/04 §20): the Character Context Builder must filter them before any
character context is assembled. The Scene itself is never handed to a
generative character — only the context builder's output is.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    scene_id: str
    # Visual ground truth — the backend knows it, DeepSeek must never receive
    # it (docs/04 §20). The default is the TV-08 validation fixture.
    wall_code: str = "0317"
    # Legal non-visual perceptions (docs/04 §20.1), e.g. sounds she can hear.
    sounds: tuple[str, ...] = ()
