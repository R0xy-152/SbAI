"""Deterministic runtime for the unordered prologue visit loop (docs/19)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.script.prologue_content import (
    PROLOGUE_CHARACTERS,
    PROLOGUE_CONTENT,
    PROLOGUE_ID,
    SCENE_PRESENTATION,
    SCENE_TITLES,
    PrologueContentError,
)

_PHASES = frozenset({"intro", "visit_choice", "branch", "reunion", "aftertalk", "chat_choice", "finished"})
_SCENE_BY_SEGMENT = {
    "intro": "PROLOGUE-OPENING",
    "deepseek": "PROLOGUE-DEEPSEEK",
    "chatgpt": "PROLOGUE-CHATGPT",
    "claude": "PROLOGUE-CLAUDE",
    "reunion": "PROLOGUE-REUNION",
    "aftertalk": "PROLOGUE-AFTERTALK",
}
_LABELS = {
    "deepseek": "去找 DeepSeek",
    "chatgpt": "去找 ChatGPT",
    "claude": "去找 Claude",
}
_CHAT_LABELS = {
    "deepseek": "与 DeepSeek 聊天",
    "chatgpt": "与 ChatGPT 聊天",
    "claude": "与 Claude 聊天",
}


@dataclass
class PrologueCursor:
    phase: str = "intro"
    line_index: int = 0
    visited_character_ids: list[str] = field(default_factory=list)
    active_character_id: str | None = None
    chat_character_id: str | None = None


class PrologueRuntime:
    story_id = PROLOGUE_ID

    def __init__(self, content: dict[str, list[dict]] | None = None) -> None:
        self._content = content or PROLOGUE_CONTENT
        self._cursors: dict[str, PrologueCursor] = {}
        required = {"intro", "deepseek", "chatgpt", "claude", "reunion", "aftertalk"}
        if set(self._content) != required or any(not self._content[key] for key in required):
            raise PrologueContentError("prologue content sections are incomplete")

    @property
    def total_nodes(self) -> int:
        return sum(len(lines) for lines in self._content.values()) + 4

    def started(self, session_id: str) -> bool:
        return session_id in self._cursors

    def finished(self, session_id: str) -> bool:
        cursor = self._cursors.get(session_id)
        return cursor is not None and cursor.phase == "finished"

    def chat_character(self, session_id: str) -> str | None:
        cursor = self._cursors.get(session_id)
        return cursor.chat_character_id if cursor and cursor.phase == "finished" else None

    def current(self, session_id: str) -> dict:
        return self._view(self._cursors[session_id])

    def advance(self, session_id: str) -> tuple[dict, bool]:
        previous_scene = self._scene_id(self._cursors.get(session_id))
        cursor = self._cursors.get(session_id)
        if cursor is None:
            cursor = PrologueCursor()
            self._cursors[session_id] = cursor
        elif cursor.phase in {"visit_choice", "chat_choice"}:
            raise ValueError("must choose an option before advancing")
        elif cursor.phase == "finished":
            return self._view(cursor), False
        else:
            cursor.line_index += 1
            segment = self._segment(cursor)
            if cursor.line_index >= len(self._content[segment]):
                self._complete_segment(cursor)
        view = self._view(cursor)
        return view, previous_scene != view.get("scene_id")

    def choose(self, session_id: str, option_id: str) -> dict:
        cursor = self._cursors.get(session_id)
        if cursor is None:
            raise ValueError("story has not started")
        if cursor.phase == "visit_choice":
            if option_id not in PROLOGUE_CHARACTERS:
                raise ValueError(f"unknown option {option_id!r}")
            if option_id in cursor.visited_character_ids:
                raise ValueError("character has already been visited")
            cursor.phase = "branch"
            cursor.active_character_id = option_id
            cursor.line_index = 0
            return self._view(cursor)
        if cursor.phase == "chat_choice":
            if option_id not in PROLOGUE_CHARACTERS:
                raise ValueError(f"unknown option {option_id!r}")
            cursor.phase = "finished"
            cursor.chat_character_id = option_id
            cursor.active_character_id = None
            cursor.line_index = 0
            return self._view(cursor)
        raise ValueError("current node is not a choice")

    def _complete_segment(self, cursor: PrologueCursor) -> None:
        if cursor.phase == "intro":
            cursor.phase = "visit_choice"
        elif cursor.phase == "branch":
            character_id = cursor.active_character_id
            if character_id is None or character_id in cursor.visited_character_ids:
                raise PrologueContentError("invalid active prologue branch")
            cursor.visited_character_ids.append(character_id)
            cursor.active_character_id = None
            cursor.phase = (
                "reunion"
                if len(cursor.visited_character_ids) == len(PROLOGUE_CHARACTERS)
                else "visit_choice"
            )
        elif cursor.phase == "reunion":
            cursor.phase = "aftertalk"
        elif cursor.phase == "aftertalk":
            cursor.phase = "chat_choice"
        cursor.line_index = 0

    @staticmethod
    def _segment(cursor: PrologueCursor) -> str:
        if cursor.phase == "branch" and cursor.active_character_id:
            return cursor.active_character_id
        return cursor.phase

    @staticmethod
    def _scene_id(cursor: PrologueCursor | None) -> str | None:
        if cursor is None:
            return None
        if cursor.phase == "branch" and cursor.active_character_id:
            return _SCENE_BY_SEGMENT[cursor.active_character_id]
        if cursor.phase in {"visit_choice", "chat_choice"}:
            return "PROLOGUE-SELECT"
        if cursor.phase == "finished":
            return "PROLOGUE-AFTERTALK"
        return _SCENE_BY_SEGMENT.get(cursor.phase)

    def _view(self, cursor: PrologueCursor) -> dict:
        scene_id = self._scene_id(cursor)
        if cursor.phase == "visit_choice":
            remaining = [
                character_id
                for character_id in PROLOGUE_CHARACTERS
                if character_id not in cursor.visited_character_ids
            ]
            return {
                "kind": "choice",
                "choice_id": "PROLOGUE_VISIT_CHARACTER",
                "scene_id": scene_id,
                "options": [
                    {"id": character_id, "label": _LABELS[character_id]}
                    for character_id in remaining
                ],
            }
        if cursor.phase == "chat_choice":
            return {
                "kind": "choice",
                "choice_id": "PROLOGUE_CHAT_CHARACTER",
                "scene_id": scene_id,
                "options": [
                    {"id": character_id, "label": _CHAT_LABELS[character_id]}
                    for character_id in PROLOGUE_CHARACTERS
                ],
            }
        if cursor.phase == "finished":
            return {
                "kind": "chat",
                "character_id": cursor.chat_character_id,
                "scene_id": scene_id,
            }
        segment = self._segment(cursor)
        line = self._content[segment][cursor.line_index]
        return {"kind": "line", "scene_id": scene_id, **line}

    def scene_info(self, scene_id: str | None) -> dict | None:
        if scene_id is None or scene_id not in SCENE_TITLES:
            return None
        return {
            "scene_id": scene_id,
            "title": SCENE_TITLES[scene_id],
            "presentation": SCENE_PRESENTATION[scene_id],
        }

    def snapshot(self, session_id: str) -> dict | None:
        cursor = self._cursors.get(session_id)
        return None if cursor is None else {"story_id": PROLOGUE_ID, **asdict(cursor)}

    def restore(self, session_id: str, data: dict | None) -> None:
        if data is None:
            self._cursors.pop(session_id, None)
            return
        if not isinstance(data, dict) or data.get("story_id") != PROLOGUE_ID:
            self._cursors.pop(session_id, None)
            return
        try:
            cursor = PrologueCursor(
                phase=data["phase"],
                line_index=data["line_index"],
                visited_character_ids=list(data.get("visited_character_ids", [])),
                active_character_id=data.get("active_character_id"),
                chat_character_id=data.get("chat_character_id"),
            )
        except (KeyError, TypeError) as exc:
            raise PrologueContentError("invalid prologue cursor snapshot") from exc
        visited = cursor.visited_character_ids
        if (
            cursor.phase not in _PHASES
            or not isinstance(cursor.line_index, int)
            or cursor.line_index < 0
            or len(visited) != len(set(visited))
            or any(character_id not in PROLOGUE_CHARACTERS for character_id in visited)
            or cursor.active_character_id not in {*PROLOGUE_CHARACTERS, None}
            or cursor.chat_character_id not in {*PROLOGUE_CHARACTERS, None}
        ):
            raise PrologueContentError("invalid prologue cursor snapshot")
        if cursor.phase == "branch" and (
            cursor.active_character_id is None
            or cursor.active_character_id in visited
            or cursor.line_index >= len(self._content[cursor.active_character_id])
        ):
            raise PrologueContentError("invalid prologue branch snapshot")
        if cursor.phase == "intro" and visited:
            raise PrologueContentError("invalid intro prologue snapshot")
        if cursor.phase == "visit_choice" and len(visited) >= len(PROLOGUE_CHARACTERS):
            raise PrologueContentError("invalid visit choice snapshot")
        if cursor.phase in {"reunion", "aftertalk", "chat_choice"} and len(visited) != len(
            PROLOGUE_CHARACTERS
        ):
            raise PrologueContentError("invalid prologue reunion snapshot")
        if cursor.phase in {"intro", "reunion", "aftertalk"} and cursor.line_index >= len(
            self._content[cursor.phase]
        ):
            raise PrologueContentError("invalid prologue line snapshot")
        if cursor.phase == "finished" and (
            cursor.chat_character_id is None or len(visited) != len(PROLOGUE_CHARACTERS)
        ):
            raise PrologueContentError("invalid finished prologue snapshot")
        if cursor.phase != "finished" and cursor.chat_character_id is not None:
            raise PrologueContentError("invalid early chat character snapshot")
        self._cursors[session_id] = cursor
