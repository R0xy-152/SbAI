"""Game Orchestrator (docs/02 §13-14).

Coordinates one player interaction: resolve the session, determine the current
character runtime, call it, and persist the messages. It does not contain
persona prompts or provider HTTP details. When a SessionRepository is given
(TV-14), each successful turn saves a snapshot and a known session_id is
restored into a fresh process, so a refresh continues the same game.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.game.context import CONTEXT_BUILDERS
from app.game.memory import (
    MemoryRejected,
    MemoryStore,
    format_memories,
    validate_memory_proposal,
)
from app.game.state.session import GameSession, SessionStore
from app.game.scene import DEFAULT_SCENE, SceneRegistry
from app.game.validation import ResponseRejected, validate_response
from app.narrative.events import NarrativeDecision, NarrativeEngine, NarrativeEvent
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.state import NarrativeState
from app.persistence.repository import PersistedSession, SessionRepository
from app.providers.base import ProviderError

logger = logging.getLogger(__name__)

# docs/05 §8: Recent Conversation is a window of the last 10-20 rounds of
# messages, not the whole session history. 20 messages = 10 rounds.
RECENT_WINDOW_MESSAGES = 20
# docs/05 §38: deterministic retrieval LIMIT N — never all memories.
MEMORY_RETRIEVAL_LIMIT = 5


@dataclass
class TurnResult:
    session_id: str
    response: CharacterResponse
    message_count: int
    # TV-16: the committed event's story-semantic Presentation Directives
    # (docs/03 §13.6), e.g. ("SHOW_CHARACTER", "claude") — surfaced so the
    # Frontend can render "Claude appears". Empty on noop turns. These are
    # deterministic backend facts, separate from the model's animation
    # proposal.
    presentation: tuple[str, ...] = ()


class GameOrchestrator:
    def __init__(
        self,
        sessions: SessionStore,
        runtimes: dict[str, CharacterRuntime],
        default_character: str = "deepseek",
        scenes: SceneRegistry | None = None,
        interpreter: NarrativeInterpreter | None = None,
        events: list[NarrativeEvent] = (),
        repository: SessionRepository | None = None,
    ) -> None:
        self._sessions = sessions
        self._runtimes = runtimes
        self._default_character = default_character
        # TV-08: the backend owns the current Scene (docs/03 §5.1). The single
        # authoritative scene source is NarrativeState.current_scene, resolved
        # per session through a SceneRegistry of static scene config. The Scene
        # itself never reaches a character — only the Context Builder's
        # filtered output does.
        self._scenes = scenes if scenes is not None else SceneRegistry()
        # TV-11: the narrative pipeline is optional. When an interpreter is
        # given, each turn runs Interpreter → Event Evaluation → character
        # output → State Commit (docs/03 §28); without one (tests that do not
        # exercise narrative) the decision is always noop and no state is kept.
        self._interpreter: NarrativeInterpreter | None = interpreter
        self._engine = NarrativeEngine(list(events))
        self._narrative_states: dict[str, NarrativeState] = {}
        # TV-13: per-session Important Memory scopes (docs/05 §17, §57).
        self._memory_stores: dict[str, MemoryStore] = {}
        # TV-14: the last character that spoke in each session (docs/02 §21
        # current_character) — used when the client sends no character_id.
        self._session_characters: dict[str, str] = {}
        # TV-14: optional persistence. Without a repository the orchestrator
        # is exactly the pre-TV-14 in-memory engine (existing tests unchanged);
        # with one, every successful turn saves a snapshot and a known
        # session_id is restored into a fresh process (Session Restore).
        self._repository = repository

    def handle_turn(
        self,
        session_id: str | None,
        message: str,
        character_id: str | None = None,
    ) -> TurnResult:
        # TV-14: a known persisted session_id is restored into this process
        # (Session Restore); an unknown id behaves exactly as before — a fresh
        # session is minted, never trusting a stale client id.
        session = self._resolve_session(session_id)
        character_id = (
            character_id
            or self._session_characters.get(session.session_id)
            or self._default_character
        )
        if character_id not in self._runtimes:
            raise ValueError(f"unknown character: {character_id}")
        self._session_characters[session.session_id] = character_id

        # TV-11: evaluate the narrative signal into a candidate event BEFORE
        # the character speaks, but commit it only AFTER the character's
        # output succeeds (Validate Before Commit, docs/03 §28). A failed
        # character output leaves state untouched, so the player can retry.
        decision = self._narrative_decision(session.session_id, message)

        runtime = self._runtimes[character_id]
        # TV-12: the Context Builder is the permission boundary for Narrative
        # State too (docs/04 §15-17). Without an interpreter there is no
        # narrative state, so the character receives no narrative context and
        # the scene falls back to the default.
        narrative_state = self._narrative_states.get(session.session_id)
        scene = self._scenes.resolve(
            narrative_state.current_scene if narrative_state is not None else DEFAULT_SCENE
        )
        context = CONTEXT_BUILDERS[character_id](scene, narrative_state)
        # TV-13: deterministic memory selection (docs/05 §37-38) — only this
        # character's memories, importance/recency ordered, LIMIT N.
        memories = self._memory_store(session.session_id).retrieve(
            character_id, limit=MEMORY_RETRIEVAL_LIMIT
        )
        response = runtime.respond(
            CharacterRequest(
                character_id=character_id,
                player_message=message,
                # TV-07: short-term context = the last window of prior messages
                # (docs/05 §8), excluding the current player message — which is
                # not yet recorded (it is committed only after the turn
                # succeeds, so a failed turn never pollutes the window); TV-09:
                # filtered to what this character actually heard.
                recent_conversation=self._heard_messages(
                    session.messages, character_id
                )[-RECENT_WINDOW_MESSAGES:],
                # TV-08: authorized, visual-filtered environment context
                # (docs/04 §15, §20) built per character.
                environment_info=context.environment_info,
                # TV-12: the authorized narrative context (relevant flags/facts,
                # docs/04 §8) rendered by the same permission boundary.
                narrative_context=context.narrative_context,
                # TV-13: the selected long-term memories the character may use.
                memory_context=format_memories(memories),
                # Narrative Directive (docs/03 §24): the selected event's
                # per-turn story goal, handed to the character when this turn
                # carries plot purpose. Empty on ordinary turns.
                narrative_directive=decision.directive,
            )
        )
        # Semantic Validation Gate (docs/04 §49-51): a well-formed but
        # impermissible response (wrong character, unauthorized fact, visual
        # leak, disallowed action) is rejected before it can touch history,
        # memory, state or the frontend, and replaced with a safe neutral line.
        try:
            validate_response(response, character_id=character_id, scene=scene)
            approved = True
        except ResponseRejected as exc:
            logger.warning(
                "character response rejected (%s); using safe fallback", exc
            )
            response = runtime.safe_fallback()
            approved = False
        # The character output succeeded, so its memory proposals may pass the
        # Write Gate (docs/05 §34) and a selected event may commit atomically
        # (docs/03 §28-29). A rejected response proposes and commits nothing.
        memory_store = self._memory_store(session.session_id)
        if approved:
            for proposal in response.memory_proposals:
                # Memory Write Gate (docs/05 §34-35): a proposal is a Proposal,
                # not a Memory, until it passes the permission gate. Rejected
                # proposals are logged for debug and never saved, so they cannot
                # re-enter the character's context via recall.
                try:
                    validate_memory_proposal(
                        proposal, character_id=character_id, scene=scene
                    )
                except MemoryRejected as exc:
                    logger.warning(
                        "memory proposal rejected (%s): %r", exc, proposal.content
                    )
                    continue
                memory_store.propose(character_id, proposal)
        if approved and decision.kind == "event":
            self._engine.commit(self._state_for(session.session_id), decision)
        # Only a completed turn records messages: the player message and the
        # character reply enter history together, after the character output
        # succeeded, so a failed turn (provider timeout, invalid output) leaves
        # history untouched and a retry never duplicates the player message
        # (docs/05 §8). TV-09: the player message records who it was addressed
        # to, so each character only hears its own thread (docs/04 §59-60).
        self._sessions.append_message(
            session.session_id,
            {"role": "player", "content": message, "character_id": character_id},
        )
        self._sessions.append_message(
            session.session_id,
            {
                "role": "character",
                "character_id": response.character_id,
                "content": response.dialogue,
            },
        )

        # TV-14: only a completed turn is persisted, so a failure never writes
        # half a turn into the snapshot (validate-before-commit also applies
        # to persistence).
        if self._repository is not None:
            self._repository.save(self._snapshot(session.session_id))

        return TurnResult(
            session_id=session.session_id,
            response=response,
            message_count=session.player_turn_count(),
            presentation=(
                decision.presentation
                if approved and decision.kind == "event"
                else ()
            ),
        )

    def get_history(self, session_id: str) -> list[dict]:
        """The session's messages in order, for the Frontend History view
        (docs/01 §18, docs/02 §7). Non-mutating: a known persisted session is
        read from the repository; otherwise the in-memory store. Unknown ids
        are an error — never a fresh mint (docs/06 §24: UI must not invent
        state).
        """
        if session_id and self._repository is not None:
            persisted = self._repository.load(session_id)
            if persisted is not None:
                return list(persisted.messages)
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"unknown session: {session_id}")
        return list(session.messages)

    def _resolve_session(self, session_id: str | None) -> GameSession:
        """Restore a persisted session, or fall back to the in-memory store.

        A session_id that the repository knows is restored into this process
        (Session Restore); any other id flows to `get_or_create`, which mints
        a fresh session for unknown ids exactly as before TV-14.
        """
        if session_id is not None and self._repository is not None:
            persisted = self._repository.load(session_id)
            if persisted is not None:
                return self._restore_session(persisted)
        return self._sessions.get_or_create(session_id)

    def _restore_session(self, persisted: PersistedSession) -> GameSession:
        """Bring a persisted snapshot back into this process (docs/02 §21).

        The scene is restored as part of `persisted.narrative_state` — its
        current_scene is the single authoritative source — so no separate
        shared Scene is stored on the orchestrator.
        """
        session = self._sessions.restore(persisted.session_id, persisted.messages)
        self._narrative_states[session.session_id] = persisted.narrative_state
        self._memory_stores[session.session_id] = MemoryStore.from_snapshot(
            persisted.memories
        )
        self._session_characters[session.session_id] = persisted.current_character
        return session

    def _snapshot(self, session_id: str) -> PersistedSession:
        """Capture the current session for the repository (TV-14)."""
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"unknown session: {session_id}")
        state = self._narrative_states.get(session_id)
        if state is None:
            state = NarrativeState()
        store = self._memory_stores.get(session_id)
        return PersistedSession(
            session_id=session_id,
            messages=list(session.messages),
            current_character=self._session_characters.get(
                session_id, self._default_character
            ),
            narrative_state=state,
            memories=store.snapshot() if store is not None else {},
        )

    def _heard_messages(self, messages: list[dict], character_id: str) -> list[dict]:
        """The messages a character is entitled to hear (TV-09).

        A message is audible to a character when it is that character's own
        reply, or a player message addressed to that character. A player
        privately talking to one character is not heard by the others;
        co-presence audibility ("同场默认可听见") is a later refinement
        (docs/05 §21-22).
        """
        return [
            message
            for message in messages
            if message.get("character_id") == character_id
        ]

    def _state_for(self, session_id: str) -> NarrativeState:
        """Per-session Narrative State (docs/03 §5), created on first use."""
        state = self._narrative_states.get(session_id)
        if state is None:
            state = NarrativeState()
            self._narrative_states[session_id] = state
        return state

    def _memory_store(self, session_id: str) -> MemoryStore:
        """Per-session Important Memory scope (docs/05 §17, §57), created on
        first use."""
        store = self._memory_stores.get(session_id)
        if store is None:
            store = MemoryStore()
            self._memory_stores[session_id] = store
        return store

    def _narrative_decision(
        self, session_id: str, message: str
    ) -> NarrativeDecision:
        """Interpret the message and select a candidate event (no commit yet).

        Without an interpreter the pipeline is skipped entirely and the
        decision is always noop. A recoverable interpreter failure (provider
        timeout / HTTP / empty content) degrades the turn to noop: no signal,
        no event, no state change — but the character still answers (docs/03
        §21-22, §28). Only ProviderError is caught; an unexpected exception
        still propagates.
        """
        if self._interpreter is None:
            return NarrativeDecision(kind="noop")
        state = self._state_for(session_id)
        try:
            interpretation = self._interpreter.interpret(state, message)
        except ProviderError as exc:
            logger.warning(
                "narrative interpreter failed (%s); degrading turn to noop",
                exc,
            )
            return NarrativeDecision(kind="noop")
        return self._engine.evaluate(state, interpretation)
