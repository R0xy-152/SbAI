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
import threading
import uuid
from dataclasses import dataclass

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.characters.registry import CharacterRuntimeRegistry
from app.game.context import CONTEXT_BUILDERS
from app.game.evidence import EVIDENCE_REGISTRY, evidence_view
from app.game.deduction import CLAIM_REGISTRY, submit_deduction
from app.game.private_interview import submit_challenge
from app.game.speaker_selector import SpeakerSelector
from app.game import recovery
from app.game.security_review import SELF_PROOFS
from app.narrative.chapter1_script import CONFIRM_KEEP_CHATGPT, DELEGATE_CLEANUP, DELETE_CLAUDE, DELETE_DEEPSEEK, DELETE_DOUBAO, OPEN_SECURITY_REVIEW, REJECT_CLEANUP, TESTIFY_CLAUDE, TESTIFY_CHATGPT, TESTIFY_DEEPSEEK, TESTIFY_DOUBAO
from app.game.investigation import InvestigationResult, InvestigationRuntime
from app.game.options import build_options
from app.game.memory import (
    MemoryRejected,
    MemoryService,
    format_memories,
    validate_memory_proposal,
)
from app.game.knowledge import KnowledgeService
from app.game.state.character_state import CharacterStateService
from app.game.state.service import StateService
from app.game.state.session import GameSession, SessionStore
from app.game.scene import DEFAULT_SCENE, SceneRegistry
from app.game.validation import ResponseRejected, validate_response
from app.game.consistency import SemanticConsistencyChecker
from app.game.interjection import named_primary, pick_interjector
from app.narrative.chapter1_script import BEGIN_CHAPTER, Chapter1ScriptRuntime
from app.narrative.events import NarrativeDecision, NarrativeEngine, NarrativeEvent
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.inquiry import Inquiry, NOOP as INQUIRY_NOOP, Chapter1InquiryInterpreter
from app.narrative.state import NarrativeState
from app.persistence.repository import PersistedSession, SessionRepository
from app.presentation.actions import PresentationAction, directive_to_actions
from app.providers.base import ProviderError
from app.script.chapter1 import PHASE_TRANSITIONS
from app.script.chapter1_content import CH1_N03_CLAUDE_INCIDENT_SEQUENCE, ScriptSequenceLine
from app.script.runtime import ScriptIntent, ScriptPlan, ScriptRuntime
from app.script.schema import ScriptError
from app.script.service import ScriptService
from app.script.story_runtime import StoryRuntime
from app.script.prologue_content import PROLOGUE_CHARACTERS, PROLOGUE_ID
from app.script.prologue_runtime import PrologueRuntime

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
    script_sequence: tuple[ScriptSequenceLine, ...] = ()
    # docs/12 §13: the structured presentation channel produced directly by the
    # Script Runtime / legacy directive mapping. Frontends prefer this over the
    # flat legacy strings.
    presentation_actions: tuple[PresentationAction, ...] = ()
    # Co-presence interjections (docs/04 §60): supplementary replies from other
    # present characters, generated after the primary reply. Empty when no one
    # interjects (single-character scenes, or the primary named nobody).
    interjections: tuple[CharacterResponse, ...] = ()


@dataclass
class InvestigationActionResult:
    session_id: str
    outcome: str
    hotspot_id: str
    evidence_id: str | None
    state: dict
    presentation: tuple[str, ...] = ()
    presentation_actions: tuple[PresentationAction, ...] = ()


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
        # Script Runtime (docs/12 §32-33): when given, the fixed beats (03:17
        # incident, GPT/豆包 arrivals, final reveal) are driven by Script
        # Sequences instead of the programmatic checks. None keeps the legacy
        # programmatic path for existing direct-construction tests.
        script_runtime: ScriptRuntime | None = None,
        inquiry_interpreter: Chapter1InquiryInterpreter | None = None,
        speaker_selector: SpeakerSelector | None = None,
        # Auto Save (docs/13 §21, Task 8): when given, the orchestrator fires
        # the checkpoint side effect after narrative commits. The player_id is
        # the browser-localStorage namespace (docs/13 §15), supplied by the API
        # layer (the frontend owns it, not the orchestrator).
        save_service: SaveSnapshotService | None = None,
        # 快速上线固定剧本（story_runtime.py，临时组件）：None 保持旧行为
        #（既有直接构造测试不受影响），由 main.py 在运行应用中注入。
        story_runtime: StoryRuntime | None = None,
        # docs/19：新的序章固定剧本；与 legacy story runtime 分开，保证既有
        # 第一章 story_cursor={node_index} 存档仍按原内容恢复。
        prologue_runtime: PrologueRuntime | None = None,
        # Semantic consistency gate (defense-in-depth, optional): when given,
        # an LLM judge checks each approved reply for subtle leaks/fabrications
        # beyond the deterministic validate_response. None keeps the existing
        # behaviour (no extra LLM call per turn).
        consistency_checker: SemanticConsistencyChecker | None = None,
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
        self._knowledge = KnowledgeService()
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
        self._script_runtime = script_runtime
        self._inquiry_interpreter = inquiry_interpreter
        self._speaker_selector = speaker_selector
        self._investigation = InvestigationRuntime()
        self._chapter1_script = Chapter1ScriptRuntime()
        # Auto Save side effect (docs/13 §21, Task 8): None keeps the
        # pre-Task-8 behaviour for existing direct-construction tests.
        self._save_service = save_service
        self._story_runtime = story_runtime
        self._prologue_runtime = prologue_runtime
        self._consistency_checker = consistency_checker
        self._player_by_session: dict[str, str] = {}
        # T2review P1-3：per-session 锁——Turn 的 Provider 读取、状态提交、
        # 消息写入与持久化必须串行化，不允许交错。
        self._turn_locks: dict[str | None, threading.Lock] = {}
        self._turn_locks_guard = threading.Lock()

    def handle_turn(
        self,
        session_id: str | None,
        message: str,
        character_id: str | None = None,
        *,
        player_id: str | None = None,
    ) -> TurnResult:
        """One complete turn under the session's atomic boundary (P1-3)."""
        with self._session_lock(session_id):
            return self._handle_turn(
                session_id, message, character_id, player_id=player_id
            )

    def _session_lock(self, session_id: str | None) -> threading.Lock:
        with self._turn_locks_guard:
            return self._turn_locks.setdefault(session_id, threading.Lock())

    def _handle_turn(
        self,
        session_id: str | None,
        message: str,
        character_id: str | None = None,
        *,
        player_id: str | None = None,
    ) -> TurnResult:
        # TV-14: a known persisted session_id is restored into this process
        # (Session Restore); an unknown id behaves exactly as before — a fresh
        # session is minted, never trusting a stale client id.
        session = self._resolve_session(session_id)
        self._bind_player(session.session_id, player_id)
        postlude_character = self._prologue_chat_character(session.session_id)
        if postlude_character is not None and character_id is None:
            character_id = postlude_character
        if character_id is None and postlude_character is None:
            # 在场角色 = 叙事状态里的 available_characters；无叙事时用 get 读取
            # （不创建状态，保持「无叙事即无状态」不变式）。
            existing_state = self._state.get(session.session_id)
            available = (
                set(existing_state.chapter1.available_characters)
                if existing_state is not None
                else set()
            ) or {self._characters.default_character}
            # docs/04 §61: the player may name a present character to direct
            # the reply — deterministic, and it beats the LLM speaker proposal.
            character_id = named_primary(message, available)
            if character_id is None and self._speaker_selector is not None:
                character_id = self._speaker_selector.choose(message, available)
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
            "prologue_aftertalk"
            if postlude_character is not None
            else (narrative_state.current_scene if narrative_state is not None else DEFAULT_SCENE)
        )
        context = CONTEXT_BUILDERS[character_id](scene, narrative_state)
        inquiry = self._inquiry(session.session_id, message, character_id)
        # TV-13: deterministic memory selection (docs/05 §37-38) — only this
        # character's memories, importance/recency ordered, LIMIT N.
        memory_store = self._memory.store_for(session.session_id)
        turn = session.player_turn_count()
        memories = memory_store.retrieve(
            character_id, limit=MEMORY_RETRIEVAL_LIMIT, query=message, now=turn
        )
        # Recall reinforces (docs/05 §66): the memories actually returned this
        # turn get their decay reset, so relevant memories stay fresh while
        # never-recalled ones fade.
        for memory in memories:
            memory_store.reinforce(character_id, memory.memory_id, turn)
        # docs/05 §31: the player-model notes this character formed about the
        # Player from its own player_* memories (owner-scoped, never others').
        player_notes = format_memories(
            memory_store.retrieve_player_notes(character_id)
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
                    # Current Character State (docs/04 §9): the character's own
                    # reasoning from the previous turn, fed back so its train of
                    # thought stays continuous across turns.
                    last_reasoning=self._character_state.reasoning_for(
                        session.session_id, character_id
                    ),
                    # Current Character State (docs/05 §45): the committed
                    # relationship stage toward the Player, fed back for
                    # attitude continuity.
                    relationship_stage=self._character_state.relationship_stage_for(
                        session.session_id, character_id
                    ),
                    player_notes=player_notes,
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
        if approved and self._consistency_checker is not None:
            # Semantic consistency gate (defense-in-depth): the deterministic
            # gate above is the hard boundary; this LLM judge catches subtler
            # leaks/fabrications/contradictions. A rejected reply falls back.
            authorized_parts: list[str] = []
            if context.environment_info:
                authorized_parts.append("环境：" + context.environment_info)
            if context.narrative_context:
                authorized_parts.append("剧情：" + context.narrative_context)
            if memories:
                authorized_parts.append("记忆：" + format_memories(memories))
            if player_notes:
                authorized_parts.append("对Player的了解：" + player_notes)
            if presented_evidence:
                authorized_parts.append(
                    "已出示证据："
                    + "、".join(item["evidence_id"] for item in presented_evidence)
                )
            verdict = self._consistency_checker.check(
                character_id=character_id,
                authorized_context="\n".join(authorized_parts),
                player_message=message,
                dialogue=response.dialogue,
                reasoning=response.reasoning,
            )
            if verdict.verdict == "reject":
                logger.warning(
                    "semantic consistency rejected (%s): %s",
                    character_id,
                    verdict.reason,
                )
                response = runtime.safe_fallback()
                approved = False
        # The character output succeeded, so its memory proposals may pass the
        # Write Gate (docs/05 §34) and a selected event may commit atomically
        # (docs/03 §28-29). A rejected response proposes and commits nothing.
        if approved:
            definitions = [CLAIM_REGISTRY.get(claim_id) for claim_id in response.claim_refs]
            if any(
                definition is None or definition.character_id != character_id
                for definition in definitions
            ):
                approved = False
                response = runtime.safe_fallback()
            else:
                live_state = None
                for definition in definitions:
                    if definition is None:
                        continue
                    # 惰性取 state：无证词的普通回合不得创建 NarrativeState
                    #（保持既有「无叙事即无状态」不变式）
                    if live_state is None:
                        live_state = self._state.state_for(session.session_id)
                    # T2review P1-1：disclosure gate——CL_CLAUDE_05（Recovery
                    # 访问披露）只有在剧情开启 claude_recovery_disclosure_open
                    # 后才能成立；不可信 LLM 不得提前解锁 EV07。被拒的 claim
                    # 只剔除、不否决整轮回复。
                    if (
                        definition.claim_id == "CL_CLAUDE_05"
                        and "claude_recovery_disclosure_open"
                        not in live_state.narrative_flags
                    ):
                        logger.warning(
                            "claim %s blocked by disclosure gate", definition.claim_id
                        )
                        continue
                    live_state.chapter1.claim_store.setdefault(
                        definition.claim_id,
                        {
                            "character_id": definition.character_id,
                            "fact_refs": list(definition.fact_refs),
                            "statement_type": "public",
                        },
                    )
                    if definition.claim_id == "CL_CLAUDE_05":
                        live_state.chapter1.acquired_evidence.add(
                            "EV07_CLAUDE_RECOVERY_ACCESS"
                        )
                current_state = self._state.get(session.session_id)
                if current_state is not None:
                    chapter = current_state.chapter1
                    if {
                        "EV06_SESSION_REPLAY_MARKER",
                        "EV07_CLAUDE_RECOVERY_ACCESS",
                        "EV08_GPT_RECOVERY_SERVICE",
                    }.issubset(chapter.acquired_evidence):
                        chapter.acquired_evidence.add("EV11_GPT_SECOND_SUMMARY")
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
        if approved:
            # Validate-Before-Commit (docs/04 §51): the model's reasoning is a
            # proposal that lands only after the reply passes validation, so a
            # rejected reply never changes the character's train of thought.
            self._character_state.commit_reasoning(
                session.session_id, character_id, response.reasoning
            )
        if approved and response.next_relationship_stage is not None:
            # Validate-Before-Commit (docs/04 §51): the relationship stage is a
            # proposal that lands only after the reply passes validation, so a
            # rejected reply never changes the relationship.
            self._character_state.commit_relationship_stage(
                session.session_id, character_id, response.next_relationship_stage
            )
        if approved and decision.kind == "event":
            self._engine.commit(self._state.state_for(session.session_id), decision)
        post_turn_state = self._state.get(session.session_id)
        # Script layer (docs/12 §32-33): with a ScriptRuntime wired, the fixed
        # beats run through Script Sequences; the legacy programmatic checks
        # below are preserved verbatim when no runtime is given (transitional
        # fallback for existing direct-construction tests).
        chapter_presentation: tuple[str, ...] = ()
        if self._script_runtime is None and post_turn_state is not None:
            chapter_presentation = self._advance_after_character_turn(
                post_turn_state, character_id, approved
            )
        # Only a completed turn records messages: the player message and the
        # character reply enter history together, after the character output
        # succeeded, so a failed turn (provider timeout, invalid output) leaves
        # history untouched and a retry never duplicates the player message.
        # Public player speech is audible to every character present *at this
        # moment*. The recorded audience prevents a character who appears
        # later from receiving earlier dialogue retroactively.
        audience = self._public_audience(session.session_id, character_id)
        self._sessions.append_message(
            session.session_id,
            {
                "role": "player",
                "content": message,
                "character_id": character_id,
                "heard_by": sorted(audience),
            },
        )

        incident_sequence: tuple[ScriptSequenceLine, ...] = ()
        incident_presentation: tuple[str, ...] = ()
        script_plan: ScriptPlan | None = None
        if approved and post_turn_state is not None:
            if self._script_runtime is not None:
                # DSL path (docs/12 §32-33): one script window per approved
                # turn. Narrative counts still tick the 03:17 A/B counter
                # (docs/12 §29) and chatgpt's first landed turn opens the
                # doubao arrival trigger (docs/12 §39 Task 6).
                self._script_window_tick(post_turn_state, message)
                if (
                    character_id == "chatgpt"
                    and "chatgpt" in post_turn_state.chapter1.available_characters
                ):
                    post_turn_state.narrative_flags.add("chatgpt_first_turn_done")
                script_plan = self._run_script_tick(
                    session.session_id, post_turn_state, message
                )
            else:
                incident_sequence = self._maybe_start_0317_incident(
                    post_turn_state, message
                )
                if incident_sequence:
                    incident_presentation = ("SHOW_CHARACTER claude",)
        self._sessions.append_message(
            session.session_id,
            {
                "role": "character",
                "character_id": response.character_id,
                "content": response.dialogue,
                # T2review P2-1：公开台词同样记录听众——同场其他角色能听到
                # 公开回复（玩家消息已带 heard_by，角色消息此前缺失）。
                "heard_by": sorted(audience),
            },
        )
        for line in incident_sequence + (script_plan.lines if script_plan is not None else ()):
            self._sessions.append_message(
                session.session_id,
                {
                    "role": "character",
                    "character_id": line.speaker,
                    "content": line.dialogue,
                },
            )

        # Co-presence interjection (docs/04 §60): after the primary reply is
        # recorded, at most one other present character may interject — only
        # when the primary reply named them. Interjections never advance the
        # plot (no Narrative Event, no claim/evidence refs) and are dropped on
        # any validation failure, exactly like a rejected primary reply.
        interjections: list[CharacterResponse] = []
        if approved and response.dialogue:
            present = set(audience)
            interjector = pick_interjector(character_id, response.dialogue, present)
            if interjector is not None and interjector != character_id:
                interjection = self._respond_interjection(
                    session,
                    message,
                    interjector,
                    scene,
                    narrative_state,
                    memory_store,
                    turn,
                )
                if interjection is not None:
                    interjections.append(interjection)
                    self._sessions.append_message(
                        session.session_id,
                        {
                            "role": "character",
                            "character_id": interjector,
                            "content": interjection.dialogue,
                            "heard_by": sorted(audience),
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
        # docs/13 §21.3: Auto Save runs AFTER the state commit and AFTER the
        # session is persisted — never save-then-update (Task 8).
        self.auto_save_if_reached(session.session_id)

        return TurnResult(
            session_id=session.session_id,
            response=response,
            message_count=session.player_turn_count(),
            presentation=(
                decision.presentation
                if approved and decision.kind == "event"
                else ()
            ) + chapter_presentation + incident_presentation
            + (script_plan.legacy_presentation if script_plan is not None else ()),
            script_sequence=incident_sequence
            + (script_plan.lines if script_plan is not None else ()),
            presentation_actions=tuple(
                directive_to_actions(
                    (decision.presentation if approved and decision.kind == "event" else ())
                    + chapter_presentation
                    + incident_presentation
                )
                + list(script_plan.actions if script_plan is not None else ())
            ),
            interjections=tuple(interjections),
        )

    def _respond_interjection(
        self,
        session: GameSession,
        player_message: str,
        interjector: str,
        scene,
        narrative_state,
        memory_store,
        turn: int,
    ) -> CharacterResponse | None:
        """Generate one bounded interjection (docs/04 §60).

        Mirrors the primary reply's request-building and validation gate, but
        commits only memory / mood / reasoning / relationship — never
        claim/evidence refs and never a Narrative Event. Returns None when the
        interjection is rejected, so the caller drops it silently.
        """
        runtime = self._characters.get(interjector)
        context = CONTEXT_BUILDERS[interjector](scene, narrative_state)
        memories = memory_store.retrieve(
            interjector,
            limit=MEMORY_RETRIEVAL_LIMIT,
            query=player_message,
            now=turn,
        )
        for memory in memories:
            memory_store.reinforce(interjector, memory.memory_id, turn)
        player_notes = format_memories(
            memory_store.retrieve_player_notes(interjector)
        )
        response = runtime.respond(
            CharacterRequest(
                character_id=interjector,
                player_message=player_message,
                # The player message and the primary reply are already recorded,
                # so the interjector hears both through _heard_messages.
                recent_conversation=self._heard_messages(
                    session.messages, interjector
                )[-RECENT_WINDOW_MESSAGES:],
                environment_info=context.environment_info,
                narrative_context=context.narrative_context,
                memory_context=format_memories(memories),
                narrative_directive="",
                mood=self._character_state.mood_for(session.session_id, interjector),
                last_reasoning=self._character_state.reasoning_for(
                    session.session_id, interjector
                ),
                relationship_stage=self._character_state.relationship_stage_for(
                    session.session_id, interjector
                ),
                player_notes=player_notes,
                inquiry=None,
                presented_evidence=self._presented_evidence_for(
                    narrative_state, interjector
                ),
            )
        )
        presented_evidence = self._presented_evidence_for(narrative_state, interjector)
        try:
            validate_response(
                response,
                character_id=interjector,
                scene=scene,
                allowed_evidence_ids=frozenset(
                    item["evidence_id"] for item in presented_evidence
                ),
                allowed_observed_fact_ids=frozenset(
                    fact_id
                    for item in presented_evidence
                    for fact_id in item["facts"]
                ),
            )
        except ResponseRejected as exc:
            logger.warning("interjection rejected (%s); dropping it", exc)
            return None
        if self._consistency_checker is not None:
            authorized_parts: list[str] = []
            if context.environment_info:
                authorized_parts.append("环境：" + context.environment_info)
            if context.narrative_context:
                authorized_parts.append("剧情：" + context.narrative_context)
            if memories:
                authorized_parts.append("记忆：" + format_memories(memories))
            if player_notes:
                authorized_parts.append("对Player的了解：" + player_notes)
            verdict = self._consistency_checker.check(
                character_id=interjector,
                authorized_context="\n".join(authorized_parts),
                player_message=player_message,
                dialogue=response.dialogue,
                reasoning=response.reasoning,
            )
            if verdict.verdict == "reject":
                logger.warning(
                    "semantic consistency rejected interjection (%s): %s",
                    interjector,
                    verdict.reason,
                )
                return None
        # Write Gate + persistent state, exactly as the primary reply (docs/05
        # §34-35, docs/04 §51). No claim/evidence/doubao side effects.
        for proposal in response.memory_proposals:
            try:
                validate_memory_proposal(
                    proposal, character_id=interjector, scene=scene
                )
            except MemoryRejected as exc:
                logger.warning(
                    "interjection memory proposal rejected (%s): %r",
                    exc,
                    proposal.content,
                )
                continue
            memory_store.propose(interjector, proposal)
        if response.next_mood is not None:
            self._character_state.commit_mood(
                session.session_id, interjector, response.next_mood
            )
        self._character_state.commit_reasoning(
            session.session_id, interjector, response.reasoning
        )
        if response.next_relationship_stage is not None:
            self._character_state.commit_relationship_stage(
                session.session_id, interjector, response.next_relationship_stage
            )
        return response

    def open_turn(
        self, session_id: str | None, *, player_id: str | None = None
    ) -> TurnResult:
        """Speak the active opening line (docs/01 §4), without player input.

        The opening is a scripted beat: it fires once per session and is
        persisted, so a refresh never repeats it. Idempotent — a session that
        already opened returns an empty reply and never re-appends.
        """
        session = self._resolve_session(session_id)
        self._bind_player(session.session_id, player_id)
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
        # docs/13 §21.3: the opening checkpoint fires only after the session
        # is persisted (Task 8).
        self.auto_save_if_reached(session.session_id)
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
            state=self._investigation_state_view(state, session.session_id),
            presentation=presentation,
            presentation_actions=tuple(directive_to_actions(presentation)),
        )

    def get_investigation_state(self, session_id: str) -> dict:
        """Return hotspot state without minting a new session."""
        if self._repository is not None:
            persisted = self._repository.load(session_id)
            if persisted is not None:
                self._restore_session(persisted)
        if self._sessions.get(session_id) is None:
            raise ValueError(f"unknown session: {session_id}")
        return self._investigation_state_view(
            self._state.state_for(session_id), session_id
        )

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

    def submit_deduction(
        self, session_id: str, message: str, *, player_id: str | None = None
    ) -> dict:
        state = self._load_known_state(session_id)
        self._assert_chapter_actions_available(state)
        self._bind_player(session_id, player_id)
        result = submit_deduction(state, message)
        # docs/12 §33: an accepted deduction may open an arrival/final beat in
        # the same response (GPT after INF01, final reveal after INF03). The
        # Script Runtime only proposes; Narrative committed already.
        if self._script_runtime is not None and result.get("outcome") == "ACCEPTED":
            plan = self._run_script_tick(session_id, state, message)
            if plan is not None:
                if plan.lines:
                    result["script_sequence"] = [line.__dict__ for line in plan.lines]
                if plan.legacy_presentation:
                    result["presentation"] = [" ".join(plan.legacy_presentation)]
                if plan.actions:
                    result["presentation_actions"] = [
                        action.model_dump() for action in plan.actions
                    ]
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        # docs/13 §21.3: INF01 / INF03 checkpoints fire after the deduction
        # committed and the session is persisted (Task 8).
        self.auto_save_if_reached(session_id)
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
        if "FIRST_IMPOSSIBLE_EVENT_RESOLVED" not in state.revealed_facts:
            raise ValueError("evidence presentation is not unlocked yet")
        if character_id not in chapter.available_characters:
            raise ValueError("character is not available")
        presented_to = chapter.presented_evidence.setdefault(evidence_id, set())
        presented_to.add(character_id)
        # Knowledge ledger (who-knows-what): presenting evidence is a legal
        # information transfer — the character now knows this evidence. It is
        # never auto-shared to other characters (docs/05 §51).
        session = self._sessions.get(session_id)
        turn = session.player_turn_count() if session is not None else 0
        self._knowledge.ledger_for(session_id).record(
            character_id, evidence_id, source="presented_evidence", turn=turn
        )
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        return PresentEvidenceResult(
            session_id=session_id,
            event="PRESENT_EVIDENCE",
            character_id=character_id,
            evidence=evidence_view(evidence_id, acquired=True, presented_to=presented_to),
        )

    @staticmethod
    def _mood_emotion(mood) -> str:
        """T2review P1-8/P1-9：把持久化 mood 映射回 named emotion，
        presentation_state 不再固定返回 neutral（Save/Load 后表情可恢复）。"""
        if mood is None:
            return "neutral"
        positive = getattr(mood, "positive", 0.5)
        excitement = getattr(mood, "excitement", 0.2)
        if excitement > 0.7:
            return "surprised"
        if excitement > 0.45:
            return "happy" if positive >= 0.5 else "angry"
        if positive < 0.35:
            # 吃醋：不高兴但情绪起伏；低落极点归 sad；平缓的不悦归 annoyed
            if excitement > 0.25:
                return "jealous"
            return "sad" if excitement <= -0.2 else "annoyed"
        if positive < 0.5 and excitement < 0.45:
            # 紧张：微低积极 + 不亢奋
            return "nervous"
        return "neutral"

    def _character_emotion(self, session_id: str | None, character_id: str) -> str:
        if session_id is None:
            return "neutral"
        states = self._character_state.snapshot(session_id) or {}
        state = states.get(character_id)
        return self._mood_emotion(state.mood if state is not None else None)

    def _investigation_state_view(
        self, state: NarrativeState, session_id: str | None = None
    ) -> dict:
        postlude_character = (
            self._prologue_chat_character(session_id) if session_id is not None else None
        )
        if postlude_character is not None:
            return {
                "scene_id": "prologue_aftertalk",
                "available_hotspots": [],
                "hotspots": {},
                "acquired_evidence": [],
                "claims": [],
                "resolved_contradictions": [],
                "private_interview_rights": [],
                "private_interview_challenges": {},
                "available_characters": [postlude_character],
                "options": [],
                "evidence_presentation": {"unlocked": False, "character_ids": []},
                "chat_character_id": postlude_character,
                "presentation_state": {
                    "scene": "prologue_aftertalk",
                    "background_effect": None,
                    "characters": [
                        {
                            "character_id": postlude_character,
                            "visible": True,
                            "emotion": self._character_emotion(session_id, postlude_character),
                            "slot": "CENTER",
                        }
                    ],
                    "input_mode": "investigation",
                },
            }
        chapter = state.chapter1
        presentation_unlocked = "FIRST_IMPOSSIBLE_EVENT_RESOLVED" in state.revealed_facts
        # T2review P1-10：在场角色 = available_characters；唯一例外是 opening
        # 阶段（BEGIN_CHAPTER 前 deepseek 已登台说开场词）。
        stage_characters = set(chapter.available_characters)
        if chapter.phase == "opening":
            stage_characters.add(self._characters.default_character)
        return {
            "scene_id": state.current_scene,
            "available_hotspots": InvestigationRuntime.available_hotspots(state),
            "hotspots": dict(chapter.hotspot_states),
            "acquired_evidence": sorted(chapter.acquired_evidence),
            "claims": sorted(chapter.claim_store),
            "resolved_contradictions": sorted(chapter.resolved_contradictions),
            "private_interview_rights": sorted(chapter.private_interview_rights),
            "private_interview_challenges": {
                "claude": "CT01_CLAUDE_SOURCE_GAP" in chapter.resolved_contradictions
                and "claude" not in chapter.private_interview_completed,
                "doubao": "doubao" in chapter.available_characters
                and "CL_DB_01" in chapter.claim_store
                and "doubao" not in chapter.private_interview_completed,
                "chatgpt": "CT04_GPT_SUMMARY_OMISSION" in chapter.resolved_contradictions
                and "chatgpt" not in chapter.private_interview_completed,
            },
            "available_characters": sorted(chapter.available_characters),
            # docs/14 T1：当前合法选项（D3 未解锁不下发）；payload 由前端回传
            "options": [
                o.to_dict()
                for o in build_options(state, self._characters.default_character)
            ],
            "evidence_presentation": {
                "unlocked": presentation_unlocked,
                "character_ids": sorted(chapter.available_characters)
                if presentation_unlocked
                else [],
            },
            # docs/12 §39 Task 1: authoritative on-stage presentation state, so
            # the Frontend never infers who is on stage from plot conditions.
            # T2review P1-10：Bad End 权威状态不再自相矛盾——在场角色就是
            # available_characters（bad_end 只剩 ChatGPT，与 docs/08 保留 GPT
            # 对话一致，不强行加回 DeepSeek）；Bad End 聊天继续，只有
            # to_be_continued 结局锁定输入（stage_characters 见函数头）。
            "presentation_state": {
                "scene": state.current_scene,
                # docs/15 §6.1：场景粒子氛围层由 Backend 权威下发（Frontend 不对
                # effect 做剧情推断）；经 SceneRegistry 按 current_scene 解析。
                "background_effect": self._scenes.resolve(
                    state.current_scene
                ).background_effect,
                "characters": [
                    {
                        "character_id": cid,
                        "visible": True,
                        "emotion": self._character_emotion(session_id, cid),
                        "slot": None,
                    }
                    for cid in sorted(stage_characters)
                ],
                "input_mode": (
                    "locked"
                    if chapter.phase == "to_be_continued"
                    else "investigation"
                ),
            },
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

        Paper evidence opens the formal pre-03:17 window. Claude's appearance
        is deliberately deferred to the deterministic trigger in
        ``_maybe_start_0317_incident`` (docs/12 §13-14).
        """
        chapter = state.chapter1
        presentation: list[str] = []
        if (
            "EV01_NOTE_V03" in chapter.acquired_evidence
            and "claude" not in chapter.available_characters
            and "PRE_0317_WINDOW" not in state.narrative_flags
        ):
            state.narrative_flags.add("PRE_0317_WINDOW")
            chapter.pre_0317_player_turns = 0
        if (
            "claude" in chapter.available_characters
            and "EV02_ADMIN_SESSION_0317" in chapter.acquired_evidence
            and "EV_CH1_RESOLVE_IMPOSSIBLE_EVENT" not in state.completed_events
        ):
            self._chapter1_script.advance(state, "RESOLVE_IMPOSSIBLE_EVENT")
        return tuple(presentation)

    def _maybe_start_0317_incident(
        self, state: NarrativeState, player_message: str
    ) -> tuple[ScriptSequenceLine, ...]:
        """Start CH1-N03 after its A/B authored trigger, once only."""
        chapter = state.chapter1
        if (
            "PRE_0317_WINDOW" not in state.narrative_flags
            or "EV01_NOTE_V03" not in chapter.acquired_evidence
            or "claude" in chapter.available_characters
            or "EV_CH1_CLAUDE_APPEARS" in state.completed_events
        ):
            return ()
        normalized = player_message.lower().replace(" ", "")
        discusses_0317 = any(token in normalized for token in ("03:17", "0317", "三点十七"))
        chapter.pre_0317_player_turns += 1
        if not discusses_0317 and chapter.pre_0317_player_turns < 2:
            return ()

        self._chapter1_script.advance(state, "CLAUDE_APPEARS")
        state.narrative_flags.discard("PRE_0317_WINDOW")
        return CH1_N03_CLAUDE_INCIDENT_SEQUENCE

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

    def _script_available(self, state: NarrativeState | None, character_id: str) -> bool:
        """Character Availability predicate for script beats (docs/12 §17, §40.3).

        system (narration) and the default character are always on stage;
        everyone else must be legally unlocked in Narrative State. The Script
        Runtime re-checks this before a character_show so a script can never
        conjure an unavailable character (fail closed, docs/12 §40.3).
        """
        if state is None:
            return False
        if character_id == "system":
            return True
        if character_id == self._characters.default_character:
            return True
        return character_id in state.chapter1.available_characters

    @staticmethod
    def _script_window_tick(state: NarrativeState, player_message: str) -> None:
        """Tick the authored 03:17 A/B counter (docs/12 §29).

        Mirrors the legacy ``_maybe_start_0317_incident`` guard: inside the
        PRE_0317_WINDOW, before Claude appeared, every approved player turn
        counts. The trigger either fires on an explicit 03:17 ask or once the
        counter reaches two — a player can never soft-lock by not asking the
        exact question.
        """
        chapter = state.chapter1
        if (
            "PRE_0317_WINDOW" not in state.narrative_flags
            or "EV01_NOTE_V03" not in chapter.acquired_evidence
            or "claude" in chapter.available_characters
            or "EV_CH1_CLAUDE_APPEARS" in state.completed_events
        ):
            return
        chapter.pre_0317_player_turns += 1

    def _route_script_intent(self, state: NarrativeState, intent: ScriptIntent) -> None:
        """Route one Script Intent through the Narrative Runtime (docs/12 §33).

        The script only declares *what it wants*; the Narrative State Machine
        validates and commits. chatgpt's unlock is deliberately unroutable —
        his availability belongs to the deduction runtime alone (docs/12 §33
        boundary demonstration). An intent the Narrative Runtime rejects
        (ScriptError) propagates before commit, leaving the cursor untouched.
        """
        if intent.kind == "unlock":
            if intent.target == "claude":
                self._chapter1_script.advance(state, "CLAUDE_APPEARS")
                return
            if intent.target == "doubao":
                self._chapter1_script.advance(state, "DOUBAO_APPEARS")
                return
            raise ScriptError(
                intent.script_id,
                intent.step_index,
                f"unlock {intent.target!r} is not routable (narrative-owned)",
            )
        if intent.kind == "phase_transition":
            transition = PHASE_TRANSITIONS.get(intent.target)
            if transition is None:
                raise ScriptError(
                    intent.script_id,
                    intent.step_index,
                    f"unknown phase transition {intent.target!r}",
                )
            transition(state)
            return
        raise ScriptError(
            intent.script_id,
            intent.step_index,
            f"unknown script intent {intent.kind!r}",
        )

    def _run_script_tick(
        self, session_id: str, state: NarrativeState, player_message: str
    ) -> ScriptPlan | None:
        """Run one script window for the session (docs/12 §32-33).

        maybe_start → advance (read-only plan) → route intents through the
        Narrative Runtime → commit. Advance never mutates; commit only advances
        the cursor after routing succeeded, so a rejected intent leaves the
        cursor untouched and the next turn retries cleanly (docs/12 §33).
        """
        runtime = self._script_runtime
        if runtime is None:
            return None
        runtime.maybe_start(session_id, state, player_message)
        if not runtime.is_active(session_id):
            return None
        plan = runtime.advance(
            session_id,
            state,
            player_message=player_message,
            available=lambda ch: self._script_available(state, ch),
        )
        for intent in plan.intents:
            self._route_script_intent(state, intent)
        runtime.commit(session_id, plan)
        return plan

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

    def _bind_player(self, session_id: str, player_id: str | None) -> None:
        """Remember which player owns a session (docs/13 §15, Task 8).

        player_id is the browser-localStorage namespace the API layer forwards
        (anonymous, not a security boundary). The orchestrator stores it only to
        fire the Auto Save side effect — the session itself carries no identity.
        """
        if player_id and player_id not in self._player_by_session:
            self._player_by_session[session_id] = player_id

    def auto_save_if_reached(self, session_id: str) -> None:
        """docs/13 §21.3 / Task 8: the Auto Save side effect after a commit.

        No save service → no-op (pre-Task-8 tests). No bound player → the save
        service is unreachable and the side effect is skipped (the player_id is
        a Frontend concept, docs/13 §15). Never raises: a checkpoint capture
        failure must not fail the turn the checkpoint rides on.
        """
        if self._save_service is None:
            return
        player_id = self._player_by_session.get(session_id)
        if player_id is None:
            return
        try:
            self._save_service.auto_save_pending(self, player_id, session_id)
        except Exception:  # pragma: no cover - defensive; a side effect must not
            # crash the gameplay turn it follows (docs/13 §21.3).
            logger.warning(
                "auto save failed for session %s", session_id, exc_info=True
            )

    def _assert_available(self, session_id: str, character_id: str) -> None:
        """Presence Gate (docs/03 §13.6): reject a not-yet-interactable character.

        Only characters listed in ``availability`` are gated; the required flag
        must be present in the session's Narrative State. A session with no
        state yet (fresh or not restored) has no flags, so a gated character is
        rejected until the flag is committed by a Narrative Event.
        """
        postlude_character = self._prologue_chat_character(session_id)
        if postlude_character is not None:
            if character_id != postlude_character:
                raise CharacterUnavailable(
                    f"only {postlude_character} is available in prologue aftertalk"
                )
            return
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

    def _prologue_chat_character(self, session_id: str | None) -> str | None:
        if session_id is None or self._prologue_runtime is None:
            return None
        character_id = self._prologue_runtime.chat_character(session_id)
        return character_id if character_id in PROLOGUE_CHARACTERS else None

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
        self._knowledge.restore(session.session_id, persisted.knowledge)
        if self._script is not None:
            self._script.restore(
                session.session_id, persisted.consumed_script_nodes
            )
        if self._script_runtime is not None:
            self._script_runtime.restore(session.session_id, persisted.script_cursor)
        if self._story_runtime is not None:
            legacy_cursor = persisted.story_cursor
            if isinstance(legacy_cursor, dict) and legacy_cursor.get("story_id"):
                legacy_cursor = None
            self._story_runtime.restore(session.session_id, legacy_cursor)
        if self._prologue_runtime is not None:
            self._prologue_runtime.restore(session.session_id, persisted.story_cursor)
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
            knowledge=(
                self._knowledge.get(session_id).snapshot()
                if self._knowledge.get(session_id) is not None
                else {}
            ),
            consumed_script_nodes=(
                self._script.snapshot(session_id)
                if self._script is not None
                else set()
            ),
            script_cursor=(
                self._script_runtime.snapshot(session_id)
                if self._script_runtime is not None
                else None
            ),
            character_states=self._character_state.snapshot(session_id),
            story_cursor=self._active_story_snapshot(session_id),
        )

    def import_snapshot(self, snapshot: dict) -> str:
        """docs/13 §19.1: create a NEW Active Session from a saved snapshot.

        The saved session is never edited in place: a fresh id is minted, the
        snapshot is restored into it, and it is persisted so a refresh after
        Load continues the restored game. Post-restore integrity validation
        (docs/13 §19.3) is the SaveSnapshotService's responsibility.
        """
        from app.persistence.repository import _session_from_dict

        persisted = _session_from_dict(snapshot)
        new_session_id = uuid.uuid4().hex
        persisted.session_id = new_session_id
        if self._repository is not None:
            self._repository.save(persisted)
        self._restore_session(persisted)
        return new_session_id

    def gameview_state(self, session_id: str) -> dict:
        """docs/13 §20.3: the initial GameViewState a Load returns the Frontend.

        The same authoritative view the Frontend fetches from /api/game/state
        (presentation_state: scene / present characters / input mode), plus the
        message history so the last displayed line can be re-rendered.
        """
        state = self._load_known_state(session_id)
        return {
            "state": self._investigation_state_view(state, session_id),
            # Frontend LoadResult contract (docs/13 §20.3)：history 携带
            # session_id + messages，与 GET /api/chat/history 同形，
            # 供 GameView 恢复最后一句已显示台词。
            "history": {
                "session_id": session_id,
                "messages": self.get_history(session_id),
            },
        }

    # ---- 快速上线固定剧本（story_runtime.py，临时组件） -------------------

    def _story_runtime_for(self, story_id: str | None = None):
        if story_id == PROLOGUE_ID:
            if self._prologue_runtime is None:
                raise ValueError("prologue story mode is not wired")
            return self._prologue_runtime
        if story_id not in {None, "legacy"}:
            raise ValueError(f"unknown story_id {story_id!r}")
        if self._story_runtime is None:
            raise ValueError("story mode is not wired")
        return self._story_runtime

    def _active_story_snapshot(self, session_id: str) -> dict | None:
        if self._prologue_runtime is not None:
            cursor = self._prologue_runtime.snapshot(session_id)
            if cursor is not None:
                return cursor
        if self._story_runtime is not None:
            return self._story_runtime.snapshot(session_id)
        return None

    def story_progress(self, session_id: str) -> dict:
        """故事进度摘要（存档路由用）：游标快照 + 是否已走到结局。
        仅读操作；story_cursor 为 None 表示该会话从未开始故事模式。
        未接线 story runtime 的部署（旧玩法测试环境）优雅降级为全 None。"""
        cursor = self._active_story_snapshot(session_id)
        if cursor is None:
            return {"story_cursor": None, "story_finished": False}
        runtime = (
            self._prologue_runtime
            if cursor.get("story_id") == PROLOGUE_ID
            else self._story_runtime
        )
        return {
            "story_cursor": cursor,
            "story_finished": bool(runtime and runtime.finished(session_id)),
        }

    def story_current(self, session_id: str | None, *, story_id: str | None = None) -> dict:
        """读取当前展示节点（不移动游标）。未知会话经 _resolve_session 造新
        会话但不动游标，前端用 started 判断是否需要 advance。"""
        session = self._resolve_session(session_id)
        runtime = self._story_runtime_for(story_id)
        started = runtime.started(session.session_id)
        node = runtime.current(session.session_id) if started else None
        return {
            "session_id": session.session_id,
            "started": started,
            "finished": runtime.finished(session.session_id),
            "node": node,
            "scene": runtime.scene_info(node.get("scene_id") if node else None),
            "chapter_opening": runtime.chapter_opening(),
        }

    def story_advance(
        self,
        session_id: str | None,
        *,
        player_id: str | None = None,
        story_id: str | None = None,
    ) -> dict:
        """移动到下一节点并返回（首次 advance 即「开始游戏」）。

        提交顺序与 handle_turn 同构：游标移动 → 台词进会话历史 → 持久化 →
        自动存档（场景边界时）。台词历史写入使 History 面板对故事模式同样
        可用。"""
        session = self._resolve_session(session_id)
        self._bind_player(session.session_id, player_id)
        runtime = self._story_runtime_for(story_id)
        node, scene_changed = runtime.advance(session.session_id)
        self._record_story_node(session.session_id, node, chosen_label=None)
        self._persist_story_turn(
            session.session_id, player_id, autosave=scene_changed
        )
        return {
            "session_id": session.session_id,
            "started": True,
            "finished": runtime.finished(session.session_id),
            "node": node,
            "scene": runtime.scene_info(node.get("scene_id")),
            "scene_changed": scene_changed,
            "chapter_opening": runtime.chapter_opening(),
        }

    def story_choose(
        self,
        session_id: str,
        option_id: str,
        *,
        player_id: str | None = None,
        story_id: str | None = None,
    ) -> dict:
        """提交一个 A/B/C 选项：游标跳到该选项的第一句台词并返回。"""
        session = self._resolve_session(session_id)
        self._bind_player(session.session_id, player_id)
        runtime = self._story_runtime_for(story_id)
        current = runtime.current(session.session_id)
        previous_scene_id = current.get("scene_id")
        label = next(
            (
                option["label"]
                for option in current.get("options", [])
                if option["id"] == option_id
            ),
            None,
        )
        if label is None:
            raise ValueError(f"unknown option {option_id!r}")
        node = runtime.choose(session.session_id, option_id)
        self._record_story_node(session.session_id, node, chosen_label=label)
        self._persist_story_turn(session.session_id, player_id, autosave=True)
        return {
            "session_id": session.session_id,
            "started": True,
            "finished": runtime.finished(session.session_id),
            "node": node,
            "scene": runtime.scene_info(node.get("scene_id")),
            "scene_changed": previous_scene_id != node.get("scene_id"),
            "chapter_opening": runtime.chapter_opening(),
        }

    def _record_story_node(
        self, session_id: str, node: dict, chosen_label: str | None
    ) -> None:
        """把展示的台词/选项写进会话历史（History 面板数据源）。"""
        if chosen_label is not None:
            self._sessions.append_message(
                session_id, {"role": "player", "content": chosen_label}
            )
        if node.get("kind") != "line":
            return
        speaker = node["speaker"]
        self._sessions.append_message(
            session_id,
            {
                "role": "player" if speaker == "player" else "character",
                "character_id": None if speaker == "player" else speaker,
                "content": node["text"],
            },
        )

    def _persist_story_turn(
        self, session_id: str, player_id: str | None, *, autosave: bool
    ) -> None:
        """故事回合收尾：先持久化会话，再（必要时）写 AUTO 自动存档。

        与 auto_save_if_reached 同约定：存档是副作用，失败只记日志，绝不让
        剧本回合本身失败。"""
        if self._repository is not None:
            self._repository.save(self._snapshot(session_id))
        if autosave and self._save_service is not None:
            bound = self._player_by_session.get(session_id)
            if bound is None:
                return
            try:
                self._save_service.auto_save_story(self, bound, session_id)
            except Exception:  # pragma: no cover - defensive side effect
                logger.warning(
                    "story auto save failed for session %s", session_id, exc_info=True
                )

    def _public_audience(self, session_id: str, character_id: str) -> set[str]:
        """Return the authoritative audience for one public player turn."""
        state = self._state.get(session_id)
        present = set(state.chapter1.available_characters) if state is not None else set()
        # DeepSeek is available from the opening but is not represented by a
        # chapter flag. The selected responder is necessarily present too.
        return present | {character_id}

    def _heard_messages(self, messages: list[dict], character_id: str) -> list[dict]:
        """Return public lines heard while present plus this character's replies."""
        return [
            message
            for message in messages
            if (
                message.get("role") == "player"
                and character_id
                in message.get("heard_by", {message.get("character_id")})
            )
            or message.get("character_id") == character_id
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
