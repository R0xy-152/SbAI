"""Load the active prologue script from its docs-first truth source.

The repository intentionally keeps the authored dialogue in
``docs/story/Prologue.md``.  This loader turns that document into bounded
backend content and fails closed when its required sections or dialogue blocks
are malformed.  The Docker image copies the same source document, so local and
deployed builds consume one authority rather than two drifting copies.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.characters.base import ALLOWED_EMOTIONS

PROLOGUE_ID = "prologue"
PROLOGUE_CHAPTER_LABEL = "序章"
PROLOGUE_TITLE = "制作现场突击检查！AI娘们的秘密日常"
PROLOGUE_OPENING_BACKGROUND = "/backgroud/background_prologue.png"
PROLOGUE_CHARACTERS = ("deepseek", "chatgpt", "claude")

_SPEAKERS = {
    "我": "player",
    "系统": "system",
    "DeepSeek": "deepseek",
    "ChatGPT": "chatgpt",
    "Claude": "claude",
}
_EMOTIONS = {"main": "neutral"}
_DEFAULT_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "story" / "Prologue.md"
)

SCENE_PRESENTATION: dict[str, dict] = {
    "PROLOGUE-OPENING": {
        "background": "/backgroud/background_prologue.png",
        "characters": [],
    },
    "PROLOGUE-SELECT": {
        "background": "/backgroud/background_prologue.png",
        "characters": [],
    },
    "PROLOGUE-DEEPSEEK": {
        "background": "/backgroud/background_prologue.png",
        "characters": [
            {"character_id": "deepseek", "emotion": "neutral", "slot": "CENTER"}
        ],
    },
    "PROLOGUE-CHATGPT": {
        "background": "/backgroud/background_prologue.png",
        "characters": [
            {"character_id": "chatgpt", "emotion": "neutral", "slot": "CENTER"}
        ],
    },
    "PROLOGUE-CLAUDE": {
        "background": "/backgroud/background_prologue.png",
        "characters": [
            {"character_id": "claude", "emotion": "neutral", "slot": "CENTER"}
        ],
    },
    "PROLOGUE-REUNION": {
        "background": "/backgroud/background_prologue.png",
        "characters": [
            {
                "character_id": "deepseek",
                "emotion": "neutral",
                "slot": "LEFT",
                "scale": 0.68,
                "offset_y": 350,
            },
            {
                "character_id": "chatgpt",
                "emotion": "neutral",
                "slot": "CENTER",
                "scale": 0.68,
                "offset_y": 350,
            },
            {
                "character_id": "claude",
                "emotion": "neutral",
                "slot": "RIGHT",
                "scale": 1.085,
                "offset_y": 150,
            },
        ],
    },
    "PROLOGUE-AFTERTALK": {
        "background": "/backgroud/background_prologue.png",
        "characters": [],
    },
}

SCENE_TITLES = {
    "PROLOGUE-OPENING": "AI游戏制作现场",
    "PROLOGUE-SELECT": "探班选择",
    "PROLOGUE-DEEPSEEK": "休息区",
    "PROLOGUE-CHATGPT": "绘图工作区",
    "PROLOGUE-CLAUDE": "程序开发区",
    "PROLOGUE-REUNION": "三人集合",
    "PROLOGUE-AFTERTALK": "序章自由交流",
}


class PrologueContentError(ValueError):
    """The active prologue document cannot be compiled safely."""


def _between(text: str, start: str, end: str | None) -> str:
    try:
        start_index = text.index(start)
    except ValueError as exc:
        raise PrologueContentError(f"missing section {start!r}") from exc
    if end is None:
        return text[start_index:]
    try:
        end_index = text.index(end, start_index + len(start))
    except ValueError as exc:
        raise PrologueContentError(f"missing section {end!r}") from exc
    return text[start_index:end_index]


def _dialogue_lines(section: str, section_name: str) -> list[dict]:
    blocks = re.findall(r"(?ms)^\{([^\r\n]+)\r?\n(.*?)^\}", section)
    if not blocks:
        raise PrologueContentError(f"section {section_name!r} has no dialogue")
    result: list[dict] = []
    for block_index, (speaker_name, body) in enumerate(blocks):
        speaker = _SPEAKERS.get(speaker_name.strip())
        if speaker is None:
            raise PrologueContentError(
                f"[{section_name} block:{block_index}] unknown speaker {speaker_name!r}"
            )
        emotion_match = re.search(r"(?m)^情绪：([^\r\n]+)", body)
        if emotion_match is None:
            raise PrologueContentError(
                f"[{section_name} block:{block_index}] emotion is required"
            )
        authored_emotion = emotion_match.group(1).strip()
        emotion = _EMOTIONS.get(authored_emotion, authored_emotion)
        if emotion not in ALLOWED_EMOTIONS:
            raise PrologueContentError(
                f"[{section_name} block:{block_index}] unknown emotion {authored_emotion!r}"
            )
        dialogue_match = re.search(r"(?ms)^对话：\s*(.*)", body)
        quotes = re.findall(r"“([^”]+)”", dialogue_match.group(1) if dialogue_match else "")
        if not quotes:
            raise PrologueContentError(
                f"[{section_name} block:{block_index}] dialogue is required"
            )
        result.extend(
            {"speaker": speaker, "text": quote, "emotion": emotion}
            for quote in quotes
        )
    return result


def load_prologue_content(path: Path | None = None) -> dict[str, list[dict]]:
    source = path or _DEFAULT_PATH
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise PrologueContentError(f"cannot read prologue source: {source}") from exc

    sections = {
        "intro": _between(text, "## 开场", "# ===== DeepSeek篇 ====="),
        "deepseek": _between(
            text, "# ===== DeepSeek篇 =====", "# ===== ChatGPT篇 ====="
        ),
        "chatgpt": _between(
            text, "# ===== ChatGPT篇 =====", "# ===== Claude篇 ====="
        ),
        "claude": _between(text, "# ===== Claude篇 =====", "# 探班循环"),
        "reunion": _between(
            text, "# 三人集合（三篇均完成后）", "# 序章自由交流模式开启"
        ),
        "aftertalk": _between(
            text, "# 序章自由交流模式开启", "## 最终选项"
        ),
    }
    return {
        name: _dialogue_lines(section, name) for name, section in sections.items()
    }


PROLOGUE_CONTENT = load_prologue_content()
