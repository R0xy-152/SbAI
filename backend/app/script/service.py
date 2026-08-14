"""ScriptService (docs/03 §37, docs/02 §19 Script Runtime, applied to lines).

Owns the per-session set of consumed script nodes (once semantics) and resolves
which authored line, if any, this turn must speak. Like StateService /
MemoryService it is a plain per-session container, not a gate: it does not
change Narrative State, it only picks a line.

Resolve is read-only — it selects a node but does NOT mark it consumed. The
orchestrator marks it consumed only after the turn succeeds (validate-before-
commit also applies to the script table: a failed turn must not burn a once
node), mirroring how Narrative Events commit only after the character output
succeeds (docs/03 §28).
"""

from __future__ import annotations

from app.narrative.events import NarrativeDecision
from app.narrative.state import NarrativeState
from app.script.node import ONCE, ScriptNode, TRIGGER_ON_EVENT, TRIGGER_OPENING


class ScriptService:
    def __init__(self, nodes: list[ScriptNode]) -> None:
        self._nodes = list(nodes)
        self._consumed: dict[str, set[str]] = {}

    def opening_node(self) -> ScriptNode | None:
        """The active opening line node, if any (spoken without player input)."""
        for node in self._nodes:
            if node.trigger == TRIGGER_OPENING:
                return node
        return None

    def resolve(
        self,
        session_id: str,
        character_id: str,
        state: NarrativeState | None,
        decision: NarrativeDecision,
    ) -> ScriptNode | None:
        """The highest-priority unconsumed node that fires for this turn, or None.

        ``state`` is accepted for future trigger kinds (ON_FLAG / ON_FACT) but
        the two MVP triggers (opening / on_event) do not read it.
        """
        consumed = self._consumed.get(session_id, set())
        for node in self._nodes:  # list order = priority (docs/03 §31)
            if node.repeat_policy == ONCE and node.node_id in consumed:
                continue
            if node.speaker != character_id:
                continue
            if not self._matches(node, decision):
                continue
            return node
        return None

    @staticmethod
    def _matches(node: ScriptNode, decision: NarrativeDecision) -> bool:
        if node.trigger == TRIGGER_ON_EVENT:
            return decision.kind == "event" and decision.event_id == node.event_id
        # OPENING is not reachable through a normal turn: it fires in the
        # orchestrator's active-opening path (open_turn), never mid-conversation.
        if node.trigger == TRIGGER_OPENING:
            return False
        return False

    def is_consumed(self, session_id: str, node_id: str) -> bool:
        return node_id in self._consumed.get(session_id, set())

    def consume(self, session_id: str, node_id: str) -> None:
        self._consumed.setdefault(session_id, set()).add(node_id)

    def snapshot(self, session_id: str) -> set[str]:
        return set(self._consumed.get(session_id, set()))

    def restore(self, session_id: str, consumed: set[str]) -> None:
        """Seed a persisted session's consumed nodes (Session Restore)."""
        self._consumed[session_id] = set(consumed)
