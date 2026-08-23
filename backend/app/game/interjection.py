"""Deterministic multi-character co-presence decisions (docs/04 §60-62).

§61: the player may name a present character to direct the reply to them.
§60: co-present characters may interject — at most one, and only when the
primary reply explicitly mentions them.

This is deliberately NOT §66 real-time talking-over (docs/04 §66 marks that as
out of scope for now): every interjection is a bounded, deterministic, single
extra reply, fired only when the primary reply names the other character.
"""

from __future__ import annotations

# Character id → matching spellings (case-insensitive). Keep aliases short and
# unambiguous to avoid false positives; "gpt" is the one deliberately loose
# alias because players call ChatGPT "GPT" more often than not.
CHARACTER_ALIASES: dict[str, tuple[str, ...]] = {
    "deepseek": ("deepseek",),
    "claude": ("claude",),
    "chatgpt": ("chatgpt", "gpt"),
    "doubao": ("doubao", "豆包"),
}


def mentioned_character_ids(
    text: str, candidates: set[str] | frozenset[str]
) -> list[str]:
    """Return candidate ids mentioned in ``text``, in first-appearance order.

    Deterministic string matching only — no LLM. Each character matches on any
    of its aliases (case-insensitive substring); a character is listed once.
    """
    normalized = text.lower()
    hits: list[tuple[int, str]] = []
    for character_id in candidates:
        for alias in CHARACTER_ALIASES.get(character_id, (character_id,)):
            position = normalized.find(alias.lower())
            if position != -1:
                hits.append((position, character_id))
                break
    hits.sort()
    return [character_id for _, character_id in hits]


def named_primary(message: str, present: set[str] | frozenset[str]) -> str | None:
    """docs/04 §61: the player names a present character to direct the reply.

    Returns the first named present character, or None when the player did not
    address anyone in particular. Deterministic — never consults the model.
    """
    mentioned = mentioned_character_ids(message, present)
    return mentioned[0] if mentioned else None


def pick_interjector(
    primary: str, primary_dialogue: str, present: set[str] | frozenset[str]
) -> str | None:
    """docs/04 §60 (受控接话): at most one co-present character interjects.

    An interjection fires only when the primary reply explicitly mentions
    another present character — the mentioned character is the one who answers.
    This keeps co-presence lively without §66-style simultaneous talking-over.
    """
    others = set(present) - {primary}
    if not others:
        return None
    mentioned = mentioned_character_ids(primary_dialogue, others)
    return mentioned[0] if mentioned else None
