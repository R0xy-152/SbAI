"""Script layer: deterministic authored lines (剧本驱动固定台词).

The Generative Dialogue + Deterministic Narrative design (docs/03 §83) lets the
LLM write ordinary chat, but certain story beats must be *authored* — the
opening line, the line right after a clue is revealed, and so on. These beats
cannot depend on the model happening to say the right thing (docs/03 §37:
必要剧情不得依赖模型随机发挥).

This package is the "independent script-node table" (独立剧本节点表): a
ScriptNode says "when the game is at this state, THIS character says THIS exact
line". It decides *what line* a turn speaks — nothing more. It never mutates
Narrative State: flags / facts / scene transitions remain the Narrative Event
engine's job (docs/03 §28-29), so a scripted line and its state change stay
orthogonal.
"""

from __future__ import annotations

from dataclasses import dataclass

# Trigger kinds (docs/03 §13.3 Trigger, but for scripted *lines* rather than
# state changes). Only the two the MVP needs; ON_FLAG / ON_FACT can be added
# when the plot grows.
TRIGGER_OPENING = "opening"      # the active opening line, spoken without player input
TRIGGER_ON_EVENT = "on_event"    # spoken on the turn a Narrative Event is selected

# Repeat policies, matching narrative/events.py (docs/03 §13.7).
ONCE = "once"
REPEATABLE = "repeatable"


@dataclass(frozen=True)
class ScriptLine:
    """One authored line, aligned with CharacterResponse's structured fields.

    emotion / animation must be values from ALLOWED_EMOTIONS / ALLOWED_ANIMATIONS
    (characters/base.py); the frontend's galPresentation ignores unknown names.
    """

    dialogue: str
    emotion: str = "neutral"
    animation: str = "none"


@dataclass(frozen=True)
class ScriptNode:
    """A deterministic rule that replaces one turn's reply with an exact line.

    ``speaker`` must equal the character this turn is addressed to, otherwise
    the node is skipped (the player is talking to someone else). This keeps the
    script from ever deciding another character speaks, which would also let it
    bypass the Presence Gate (docs/03 §13.6).
    """

    node_id: str
    speaker: str
    line: ScriptLine
    trigger: str = TRIGGER_ON_EVENT
    # For TRIGGER_ON_EVENT: the event_id whose selection fires this line.
    event_id: str | None = None
    repeat_policy: str = ONCE
