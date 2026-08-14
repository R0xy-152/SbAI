"""POC script-node fixtures (docs/06 §10: Fixture ≠ Production Content).

These two nodes validate the deterministic-authored-line mechanism only. They
are not real plot: the exact wording is a placeholder and the Claude tie-in
reuses the existing EV_POC_CLAUDE_APPEARS fixture event.
"""

from __future__ import annotations

from app.narrative.poc import EV_POC_CLAUDE_APPEARS
from app.script.node import ONCE, ScriptLine, ScriptNode, TRIGGER_ON_EVENT, TRIGGER_OPENING

SCRIPT_OPENING = "SCRIPT_OPENING"
SCRIPT_ON_CLAUDE_APPEARS = "SCRIPT_ON_CLAUDE_APPEARS"


def build_script_nodes() -> list[ScriptNode]:
    """The MVP script table: the active opening line + the Claude-appearance line."""
    return [
        ScriptNode(
            node_id=SCRIPT_OPENING,
            speaker="deepseek",
            line=ScriptLine(
                dialogue="……你醒了。别怕，我们先弄清楚这里发生了什么。",
                emotion="neutral",
                animation="none",
            ),
            trigger=TRIGGER_OPENING,
            repeat_policy=ONCE,
        ),
        ScriptNode(
            node_id=SCRIPT_ON_CLAUDE_APPEARS,
            speaker="deepseek",
            line=ScriptLine(
                dialogue="……你、你怎么会在这里？！",
                emotion="annoyed",
                animation="none",
            ),
            trigger=TRIGGER_ON_EVENT,
            event_id=EV_POC_CLAUDE_APPEARS,
            repeat_policy=ONCE,
        ),
    ]
