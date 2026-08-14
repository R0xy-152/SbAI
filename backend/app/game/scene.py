"""Scene model — the room's facts owned by the backend (docs/03 §5.1).

A Scene holds ground truth about the current room, including visual facts
such as `wall_code`. Visual facts are forbidden knowledge for DeepSeek
(docs/04 §20): the Character Context Builder must filter them before any
character context is assembled. The Scene itself is never handed to a
generative character — only the context builder's output is.
"""

from __future__ import annotations

from dataclasses import dataclass

# The scene a session starts in when no Narrative State exists yet (docs/03
# §5.1). NarrativeState.current_scene defaults to the same value.
DEFAULT_SCENE = "binding_room"


@dataclass(frozen=True)
class Scene:
    scene_id: str
    # Visual ground truth — the backend knows it, DeepSeek must never receive
    # it (docs/04 §20). The default is the TV-08 validation fixture.
    wall_code: str = "0317"
    # Legal non-visual perceptions (docs/04 §20.1), e.g. sounds she can hear.
    sounds: tuple[str, ...] = ()


class SceneRegistry:
    """Maps a scene_id to its Scene config (docs/02 §992-994 Content → Scene
    Config; docs/03 §5.1).

    The registry is static scene *configuration*, not per-session state: the
    single authoritative scene source remains NarrativeState.current_scene, and
    this registry only resolves that id into the concrete Scene facts the
    Context Builder needs. Resolving an unknown id yields a neutral Scene with
    no invented ground truth (fail safe — never leak visual facts into a scene
    that was not defined).
    """

    def __init__(self, scenes: dict[str, Scene] | None = None) -> None:
        scenes = dict(scenes or {})
        scenes.setdefault(DEFAULT_SCENE, Scene(scene_id=DEFAULT_SCENE))
        self._scenes = scenes

    def resolve(self, scene_id: str) -> Scene:
        """The Scene for `scene_id`, or a neutral Scene for an unknown id."""
        return self._scenes.get(
            scene_id, Scene(scene_id=scene_id, wall_code="", sounds=())
        )
