"""Game Orchestrator (docs/02 §13-14).

Coordinates one player interaction: load the session, determine the current
character runtime, call it, validate, commit, and persist. It does not contain
persona prompts, provider HTTP details, or any per-session storage of its own —
Narrative State, Important Memory and the current character live in services
(StateService / SessionStore / MemoryService) and the runtime map lives in a
CharacterRuntimeRegistry. When a SessionRepository is given (TV-14), each
successful turn saves a snapshot and a known session_id is restored into a
fresh process, so a refresh continues the same game.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.registry import CharacterRuntimeRegistry
from app.game.context import CONTEXT_BUILDERS
from app.game.evidence import EVIDENCE_REGISTRY, evidence_view
from app.game.deduction import CLAIM_REGISTRY, submit_deduction
from app.game.private_interview import submit_challenge
from app.game import recovery
from app.game.security_review import SELF_PROOFS
from app.narrative.chapter1_script import CONFIRM_KEEP_CHATGPT, DELEGATE_CLEANUP, DELETE_CLAUDE, DELETE_DEEPSEEK, DELETE_DOUBAO, OPEN_SECURITY_REVIEW, REJECT_CLEANUP, TESTIFY_CLAUDE, TESTIFY_CHATGPT, TESTIFY_DEEPSEEK, TESTIFY_DOUBAO
from app.game.investigation import InvestigationResult, InvestigationRuntime
from app.game.memory import (
    MemoryRejected,
    MemoryService,
    format_memories,
    validate_memory_proposal,
)
from app.game.state.character_state import CharacterStateService
from app.game.state.service import StateService
from app.game.state.session import GameSession, SessionStore
from app.game.scene import DEFAULT_SCENE, SceneRegistry
from app.game.validation import ResponseRejected, validate_response
from app.narrative.events import NarrativeDecision, NarrativeEngine, NarrativeEvent
from app.narrative.chapter1_script import BEGIN_CHAPTER, Chapter1ScriptRuntime
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.inquiry import Inquiry, NOOP as INQUIRY_NOOP, Chapter1InquiryInterpreter
from app.narrative.state import NarrativeState
from app.persistence.repository import PersistedSession, SessionRepository
from app.providers.base import ProviderError
from app.script.service import ScriptService

logger = logging.getLogger(__name__)

# docs/05 §8: Recent Conversation is a window of the last 10-20 rounds of
# messages, not the whole session history. 20 messages = 10 rounds.
RECENT_WINDOW_MESSAGES = 20
# docs/05 §38: deterministic retrieval LIMIT N — never all memories.
MEMORY_RETRIEVAL_LIMIT = 5


class CharacterUnavailable(Exception):
    """The requested character is not yet interactable (Presence Gate).

    Which characters the player may talk to is a deterministic backend fact
    (docs/03 §13.6 / §28): the orchestrator resolves it outside the Narrative
    Runtime from ``availability`` and the session's Narrative State, never
    trusting the Frontend. Deliberately *not* a ``ValueError`` subclass so the
    API layer can map it to 403 independently of the ``ValueError`` → 400
    mapping.
    """


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


@dataclass
class InvestigationActionResult:
    session_id: str
    outcome: str
    hotspot_id: str
    evidence_id: str | None
    state: dict
    presentation: tuple[str, ...] = ()


@dataclass
class PresentEvidenceResult:
    session_id: str
    event: str
    character_id: str
    evidence: dict


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
        # Presence Gate (docs/03 §13.6): character_id → narrative flag that
        # must be present in NarrativeState before the player may talk to that
        # character. None / empty = gate disabled (existing direct-construction
        # tests keep their pre-gate behaviour). Only the real app wires it.
        availability: dict[str, str] | None = None,
        # Script layer (docs/03 §37): when given, resolves which authored line
        # (if any) a turn must speak instead of the LLM. None keeps the
        # pre-script behaviour for existing direct-construction tests.
        script: ScriptService | None = None,
        inquiry_interpreter: Chapter1InquiryInterpreter | None = None,
    ) -> None:
        self._sessions = sessions
        # Character Runtime Registry owns the runtime map and the default
        # character; the orchestrator asks it who speaks this turn (docs/04 §61-62).
        self._characters = CharacterRuntimeRegistry(runtimes, default_character)
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
        # State / Memory are owned by services (docs/02 §21), not by the
        # orchestrator: it coordinates, it does not store per-session state.
        self._state = StateService()
        self._memory = MemoryService()
        # Per-character persistent state (docs/04 §9): the two-axis mood the
        # model proposes and the orchestrator commits/restores per session.
        self._character_state = CharacterStateService()
        # TV-14: optional persistence. Without a repository the orchestrator
        # is exactly the pre-TV-14 in-memory engine (existing tests unchanged);
        # with one, every successful turn saves a snapshot and a known
        # session_id is restored into a fresh process (Session Restore).
        self._repository = repository
        # Presence Gate map (docs/03 §13.6): empty means the gate is off.
        self._availability = availability if availability is not None else {}
        self._script = script
        self._inquiry_interpreter = inquiry_interpreter
        self._investigation = InvestigationRuntime()
        self._chapter1_script = Chapter1ScriptRuntime()

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
        character_id = self._characters.resolve(
            requested=character_id,
            last=session.current_character or None,
        )
        # Presence Gate (docs/03 §13.6): after the character is resolved, before
        # any state mutation, message recording or runtime call. An unavailable
        # character is rejected Fail Closed — no current_character, no history,
        # no state change.
        self._assert_available(session.session_id, character_id)
        session.current_character = character_id

        # TV-11: evaluate the narrative signal into a candidate event BEFORE
        # the character speaks, but commit it only AFTER the character's
        # output succeeds (Validate Before Commit, docs/03 §28). A failed
        # character output leaves state untouched, so the player can retry.
        decision = self._narrative_decision(session.session_id, message)

        runtime = self._characters.get(character_id)
        # TV-12: the Context Builder is the permission boundary for Narrative
        # State too (docs/04 §15-17). Without an interpreter there is no
        # narrative state, so the character receives no narrative context and
        # the scene falls back to the default.
        narrative_state = self._state.get(session.session_id)
        scene = self._scenes.resolve(
            narrative_state.current_scene if narrative_state is not None else DEFAULT_SCENE
        )
        context = CONTEXT_BUILDERS[character_id](scene, narrative_state)
        inquiry = self._inquiry(session.session_id, message, character_id)
        # TV-13: deterministic memory selection (docs/05 §37-38) — only this
        # character's memories, importance/recency ordered, LIMIT N.
        memories = self._memory.store_for(session.session_id).retrieve(
            character_id, limit=MEMORY_RETRIEVAL_LIMIT
        )
        # Script layer (docs/03 §37): a turn at a scripted beat speaks its
        # authored line instead of the LLM. The state change that beat depends
        # on (the Narrative Event) still commits below, exactly as on an
        # ordinary turn. A node whose speaker is not this turn's character was
        # already skipped by ScriptService.resolve.
        scripted = (
            self._script.resolve(
                session.session_id, character_id, narrative_state, decision
            )
            if self._script is not None
            else None
        )
        if scripted is not None:
            response = CharacterResponse(
                character_id=scripted.speaker,
                dialogue=scripted.line.dialogue,
                emotion=scripted.line.emotion,
                animation_proposal=scripted.line.animation,
            )
        else:
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
                    # Current Character State (docs/04 §9): the character's
                    # persistent mood, seeded into the prompt so replies stay
                    # emotionally continuous.
                    mood=self._character_state.mood_for(
                        session.session_id, character_id
                    ),
                    inquiry=inquiry,
                    presented_evidence=self._presented_evidence_for(
                        narrative_state, character_id
                    ),
                )
            )
        # Semantic Validation Gate (docs/04 §49-51): a well-formed but
        # impermissible response (wrong character, unauthorized fact, visual
        # leak, disallowed action) is rejected before it can touch history,
        # memory, state or the frontend, and replaced with a safe neutral line.
        presented_evidence = self._presented_evidence_for(narrative_state, character_id)
        try:
            validate_response(
                response,
                character_id=character_id,
                scene=scene,
                allowed_evidence_ids=frozenset(
                    item["evidence_id"] for item in presented_evidence
                ),
                allowed_observed_fact_ids=frozenset(
                    fact_id for item in presented_evidence for fact_id in item["facts"]
                ),
            )
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
        memory_store = self._memory.store_for(session.session_id)
        if approved:
            definitions = [CLAIM_REGISTRY.get(claim_id) for claim_id in response.claim_refs]
            if any(
                definition is None or definition.character_id != character_id
                for definition in definitions
            ):
                approved = False
                response = runtime.safe_fallback()
            else:
                for definition in definitions:
                    if definition is not None:
                        self._state.state_for(session.session_id).chapter1.claim_store.setdefault(
                            definition.claim_id,
                            {
                                "character_id": definition.character_id,
                                "fact_refs": list(definition.fact_refs),
                                "statement_type": "public",
                            },
                        )
            if response.evidence_refs:
                self._state.state_for(session.session_id).chapter1.evidence_selections.append(
                    {
                        "character_id": character_id,
                        "evidence_ids": list(response.evidence_refs),
                    }
                )
            if character_id == "doubao" and (
                response.observed_fact_refs or response.interpretation is not None
            ):
                self._state.state_for(session.session_id).chapter1.doubao_statements.append(
                    {
                        "observed_fact_refs": list(response.observed_fact_refs),
                        "interpretation": response.interpretation,
                    }
                )
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
        if approved and response.next_mood is not None:
            # Validate-Before-Commit (docs/04 §51): the model's mood is a
            # proposal that lands only after the reply passes validation, so a
            # rejected reply never changes the character's persistent state.
            self._character_state.commit_mood(
                session.session_id, character_id, response.next_mood
            )
        if approved and decision.kind == "event":
            self._engine.commit(self._state.state_for(session.session_id), decision)
        post_turn_state = self._state.get(session.session_id)
        chapter_presentation = (
            self._advance_after_character_turn(post_turn_state, character_id, approved)
            if post_turn_state is not None
            else ()
        )
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

        # A once script node is consumed only when its line was actually
        # presented (validate-before-commit also applies to the script table,
        # docs/03 §28): a rejected line must not burn the node. Consume before
        # persisting so the snapshot records it.
        if approved and scripted is not None:
            self._script.consume(session.session_id, scripted.node_id)

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
            ) + chapter_presentation,
        )

    def open_turn(self, session_id: str | None) -> TurnResult:
        """Speak the active opening line (docs/01 §4), without player input.

        The opening is a scripted beat: it fires once per session and is
        persisted, so a refresh never repeats it. Idempotent — a session that
        already opened returns an empty reply and never re-appends.
        """
        session = self._resolve_session(session_id)
        opening = self._script.opening_node() if self._script is not None else None
        if opening is None:
            return self._empty_turn(session)
        if self._script.is_consumed(session.session_id, opening.node_id) or session.messages:
            return self._empty_turn(session)
        response = CharacterResponse(
            character_id=opening.speaker,
            dialogue=opening.line.dialogue,
            emotion=opening.line.emotion,
            animation_proposal=opening.line.animation,
        )
        # Authored lines still pass the Semantic Validation Gate (docs/04 §51)
        # as defense-in-depth; a mis-authored line falls back like any reply.
        narrative_state = self._state.get(session.session_id)
        scene = self._scenes.resolve(
            narrative_state.current_scene if narrative_state is not None else DEFAULT_SCENE
        )
        try:
            validate_response(response, character_id=opening.speaker, scene=scene)
        except ResponseRejected as exc:
            logger.warning("opening line rejected (%s); using fallback", exc)
            response = self._characters.get(opening.speaker).safe_fallback()
        self._sessions.append_message(
            session.session_id,
            {
                "role": "character",
                "character_id": response.character_id,
                "content": response.dialogue,
            },
        )
        self._script.consume(session.session_id, opening.node_id)
        if self._repository is not None:
            self._repository.save(self._snapshot(session.session_id))
        return TurnResult(
            session_id=session.session_id,
            response=response,
            message_count=session.player_turn_count(),
        )

    def _empty_turn(self, session: GameSession) -> TurnResult:
        """A no-op turn result with an empty reply (already-opened session)."""
        return TurnResult(
            session_id=session.session_id,
            response=CharacterResponse(
                character_id=session.current_character
                or self._characters.default_character,
                dialogue="",
            ),
            message_count=session.player_turn_count(),
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

    def handle_investigation_action(
        self, session_id: str | None, action: str, hotspot_id: str
    ) -> InvestigationActionResult:
        """Commit one allow-listed physical scene interaction."""
        session = self._resolve_session(session_id)
        state = self._state.state_for(session.session_id)
        self._assert_chapter_actions_available(state)
        # The chapter outline starts when the player performs their first
        # physical interaction; this is not a frontend-selected state change.
        if state.chapter1.phase == "opening":
            self._chapter1_script.advance(state, BEGIN_CHAPTER)
        result: InvestigationResult = self._investigation.apply(
            state, action, hotspot_id
        )
        presentation = self._advance_first_case(state)
        if self._repository is not None:
            self._repository.save(self._snapshot(session.session_id))
        return InvestigationActionResult(
            session_id=session.session_id,
            outcome=result.outcome,
            hotspot_id=result.hotspot_id,
            evidence_id=result.evidence_id,
            state=self._investigation_state_view(state),
            presentation=presentation,
        )

    def get_investigation_state(self, session_id: str) -> dict:
        """Return hotspot state without minting a new session."""
        if self._repository is not None:
            persisted = self._repository.load(session_id)
            if persisted is not None:
                self._restore_session(persisted)
        if self._sessions.get(session_id) is None:
            raise ValueError(f"unknown session: {session_id}")
        return self._investigation_state_view(self._state.state_for(session_id))

    def get_evidence(self, session_id: str) -> list[dict]:
        """List only evidence the player has actually acquired."""
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        chapter = state.chapter1
        return [
            evidence_view(
                evidence_id,
                acquired=True,
                presented_to=chapter.presented_evidence.get(evidence_id, set()),
            )
            for evidence_id in sorted(chapter.acquired_evidence)
            if evidence_id in EVIDENCE_REGISTRY
        ]

    def submit_deduction(self, session_id: str, message: str) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        result = submit_deduction(state, message)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return result

    def submit_private_interview_challenge(self, session_id: str, **payload) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        result = submit_challenge(state, **payload)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return result

    def start_recovery(self, session_id: str) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        result = recovery.start(state)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return result

    def recovery_action(self, session_id: str, action: str, target: str, actor: str) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        result = recovery.act(state, action, target, actor)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return result

    def start_security_review(self, session_id: str) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        self._chapter1_script.advance(state, OPEN_SECURITY_REVIEW)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return {"status": "OPEN", "order": ["deepseek", "claude", "doubao", "chatgpt"]}

    def testify(self, session_id: str, character_id: str) -> dict:
        actions = {"deepseek": TESTIFY_DEEPSEEK, "claude": TESTIFY_CLAUDE, "doubao": TESTIFY_DOUBAO, "chatgpt": TESTIFY_CHATGPT}
        if character_id not in actions:
            raise ValueError("unknown Security Review character")
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        self._chapter1_script.advance(state, actions[character_id])
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return {"character_id": character_id, "statement": SELF_PROOFS[character_id], "completed": list(state.chapter1.testified_characters)}

    def cleanup(self, session_id: str, action: str) -> dict:
        actions = {"DELEGATE": DELEGATE_CLEANUP, "DELETE_DEEPSEEK": DELETE_DEEPSEEK, "DELETE_CLAUDE": DELETE_CLAUDE, "DELETE_DOUBAO": DELETE_DOUBAO, "CONFIRM_KEEP_CHATGPT": CONFIRM_KEEP_CHATGPT}
        if action not in actions:
            raise ValueError("unknown cleanup action")
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        self._chapter1_script.advance(state, actions[action])
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return {"phase": state.chapter1.phase, "ending": state.chapter1.ending, "available_characters": sorted(state.chapter1.available_characters)}

    def reject_cleanup(self, session_id: str) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        self._chapter1_script.advance(state, REJECT_CLEANUP)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return {"phase": state.chapter1.phase, "ending": state.chapter1.ending, "scene_id": state.current_scene}

    def present_evidence(
        self, session_id: str, character_id: str, evidence_id: str
    ) -> PresentEvidenceResult:
        """Record a presentation without letting it advance plot truth."""
        state = self._load_known_state(session_id)
        chapter = state.chapter1
        self._assert_chapter_actions_available(state)
        if evidence_id not in EVIDENCE_REGISTRY:
            raise ValueError(f"unknown evidence: {evidence_id}")
        if evidence_id not in chapter.acquired_evidence:
            raise ValueError("evidence has not been acquired")
        if character_id not in chapter.available_characters:
            raise ValueError("character is not available")
        presented_to = chapter.presented_evidence.setdefault(evidence_id, set())
        presented_to.add(character_id)
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return PresentEvidenceResult(
            session_id=session_id,
            event="PRESENT_EVIDENCE",
            character_id=character_id,
            evidence=evidence_view(evidence_id, acquired=True, presented_to=presented_to),
        )

    @staticmethod
    def _investigation_state_view(state: NarrativeState) -> dict:
        chapter = state.chapter1
        return {
            "scene_id": state.current_scene,
            "hotspots": dict(chapter.hotspot_states),
            "acquired_evidence": sorted(chapter.acquired_evidence),
            "claims": sorted(chapter.claim_store),
            "resolved_contradictions": sorted(chapter.resolved_contradictions),
            "private_interview_rights": sorted(chapter.private_interview_rights),
            "private_interview_challenges": {
                "claude": "CT01_CLAUDE_SOURCE_GAP" in chapter.resolved_contradictions
                and "claude" not in chapter.private_interview_completed,
            },
            "available_characters": sorted(chapter.available_characters),
        }

    def _load_known_state(self, session_id: str) -> NarrativeState:
        if self._repository is not None:
            persisted = self._repository.load(session_id)
            if persisted is not None:
                self._restore_session(persisted)
        if self._sessions.get(session_id) is None:
            raise ValueError(f"unknown session: {session_id}")
        return self._state.state_for(session_id)

    @staticmethod
    def _assert_chapter_actions_available(state: NarrativeState) -> None:
        if state.chapter1.phase == "bad_end":
            raise ValueError("chapter actions are unavailable in Bad End")
        if state.chapter1.phase == "to_be_continued":
            raise ValueError("chapter actions are unavailable after To Be Continued")

    def _advance_first_case(self, state: NarrativeState) -> tuple[str, ...]:
        """Connect real exploration to the first authored investigation beat.

        This is intentionally a tiny deterministic bridge: paper evidence
        reveals Claude; the terminal log then resolves the first impossible
        event. Neither step invokes a provider or unlocks later characters.
        """
        chapter = state.chapter1
        presentation: list[str] = []
        if "EV01_NOTE_V03" in chapter.acquired_evidence and "claude" not in chapter.available_characters:
            self._chapter1_script.advance(state, "CLAUDE_APPEARS")
            presentation.append("SHOW_CHARACTER claude")
        if (
            "claude" in chapter.available_characters
            and "EV02_ADMIN_SESSION_0317" in chapter.acquired_evidence
            and "EV_CH1_RESOLVE_IMPOSSIBLE_EVENT" not in state.completed_events
        ):
            self._chapter1_script.advance(state, "RESOLVE_IMPOSSIBLE_EVENT")
        return tuple(presentation)

    @staticmethod
    def _advance_after_character_turn(
        state: NarrativeState, character_id: str, approved: bool
    ) -> tuple[str, ...]:
        """Advance authored arrivals only after their prerequisite turn lands."""
        chapter = state.chapter1
        if (
            approved
            and character_id == "chatgpt"
            and "chatgpt" in chapter.available_characters
            and "doubao" not in chapter.available_characters
        ):
            chapter.available_characters.add("doubao")
            state.narrative_flags.add("doubao_has_appeared")
            return ("SHOW_CHARACTER doubao",)
        return ()

    @staticmethod
    def _presented_evidence_for(
        state: NarrativeState | None, character_id: str
    ) -> list[dict]:
        if state is None:
            return []
        chapter = state.chapter1
        return [
            evidence_view(evidence_id, acquired=True, presented_to={character_id})
            for evidence_id in sorted(chapter.acquired_evidence)
            if character_id in chapter.presented_evidence.get(evidence_id, set())
            and evidence_id in EVIDENCE_REGISTRY
        ]

    def _inquiry(self, session_id: str, message: str, character_id: str) -> Inquiry | None:
        """Interpret a question without making it a narrative event."""
        if self._inquiry_interpreter is None:
            return None
        state = self._state.state_for(session_id)
        try:
            inquiry = self._inquiry_interpreter.interpret(state, message)
        except ProviderError:
            return None
        if inquiry.intent == INQUIRY_NOOP:
            return None
        # A question addressed to another character must not leak into this
        # speaker's runtime; multi-character routing is a later phase.
        if inquiry.target is not None and inquiry.target != character_id:
            return None
        return inquiry

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

    def _assert_available(self, session_id: str, character_id: str) -> None:
        """Presence Gate (docs/03 §13.6): reject a not-yet-interactable character.

        Only characters listed in ``availability`` are gated; the required flag
        must be present in the session's Narrative State. A session with no
        state yet (fresh or not restored) has no flags, so a gated character is
        rejected until the flag is committed by a Narrative Event.
        """
        state = self._state.get(session_id)
        if state is not None and state.chapter1.phase == "bad_end":
            if character_id != "chatgpt":
                raise CharacterUnavailable("only chatgpt is available in Bad End")
            return
        if not self._availability:
            return
        required = self._availability.get(character_id)
        if required is None:
            return
        flags = state.narrative_flags if state is not None else set()
        if required not in flags:
            raise CharacterUnavailable(
                f"character {character_id} is not available yet"
            )

    def _restore_session(self, persisted: PersistedSession) -> GameSession:
        """Bring a persisted snapshot back into this process (docs/02 §21).

        Each service seeds its own slice from the snapshot: the SessionStore
        restores the messages and current character, the StateService the
        narrative state, the MemoryService the per-character memories. The
        scene is restored as part of `persisted.narrative_state` — its
        current_scene is the single authoritative source — so no separate
        shared Scene is stored on the orchestrator.
        """
        session = self._sessions.restore(
            persisted.session_id, persisted.messages, persisted.current_character
        )
        self._state.restore(session.session_id, persisted.narrative_state)
        self._memory.restore(session.session_id, persisted.memories)
        if self._script is not None:
            self._script.restore(
                session.session_id, persisted.consumed_script_nodes
            )
        self._character_state.restore(session.session_id, persisted.character_states)
        return session

    def _snapshot(self, session_id: str) -> PersistedSession:
        """Capture the current session for the repository (TV-14)."""
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"unknown session: {session_id}")
        state = self._state.get(session_id)
        if state is None:
            state = NarrativeState()
        store = self._memory.get(session_id)
        return PersistedSession(
            session_id=session_id,
            messages=list(session.messages),
            current_character=session.current_character
            or self._characters.default_character,
            narrative_state=state,
            memories=store.snapshot() if store is not None else {},
            consumed_script_nodes=(
                self._script.snapshot(session_id)
                if self._script is not None
                else set()
            ),
            character_states=self._character_state.snapshot(session_id),
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
        state = self._state.state_for(session_id)
        try:
            interpretation = self._interpreter.interpret(state, message)
        except ProviderError as exc:
            logger.warning(
                "narrative interpreter failed (%s); degrading turn to noop",
                exc,
            )
            return NarrativeDecision(kind="noop")
        return self._engine.evaluate(state, interpretation)
