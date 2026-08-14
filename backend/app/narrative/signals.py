"""Narrative Signal definitions (docs/03 §16, §19).

A Signal is what the player's message *may express* in story terms — it is a
candidate for event evaluation, never Game State itself (docs/03 §18).

Scoped Interpretation (docs/03 §19): the interpreter only judges against the
signals currently eligible in the scene, so it never needs (or leaks) later
plot signals. The binding room's set follows the docs/03 §19.1 example.
"""

from __future__ import annotations

SIG_ASK_CAPTOR = "SIG_ASK_CAPTOR"
SIG_ASK_LOCATION = "SIG_ASK_LOCATION"
SIG_ASK_ESCAPE = "SIG_ASK_ESCAPE"

# Interpreter outcomes that are not signals (docs/03 §21):
#   noop      — ordinary chat, nothing story-relevant (a normal result)
#   ambiguous — looks story-relevant but cannot be reliably mapped without
#               more context; fail closed rather than force an event
OUTCOME_NOOP = "noop"
OUTCOME_AMBIGUOUS = "ambiguous"
OUTCOMES = frozenset({OUTCOME_NOOP, OUTCOME_AMBIGUOUS})

# One-line semantic descriptions shown to the interpreter, so it maps
# paraphrases to the right signal instead of guessing from the id alone
# (docs/03 §36.1 Semantic Trigger).
SIGNAL_DESCRIPTIONS: dict[str, str] = {
    SIG_ASK_CAPTOR: "Player 在询问或怀疑是谁把大家抓来、绑来或弄到这个房间的，"
    "包括“是不是某人干的”这类追问",
    SIG_ASK_LOCATION: "Player 在询问这是哪里 / 当前身处何处",
    SIG_ASK_ESCAPE: "Player 在询问怎么出去 / 如何逃离 / 离开的方法",
}

SIGNALS_BY_SCENE: dict[str, frozenset[str]] = {
    "binding_room": frozenset({SIG_ASK_CAPTOR, SIG_ASK_LOCATION, SIG_ASK_ESCAPE}),
}


def eligible_signals(scene: str) -> frozenset[str]:
    """The signals the interpreter may judge against in `scene` (docs/03 §19)."""
    return SIGNALS_BY_SCENE.get(scene, frozenset())
