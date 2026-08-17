"""Deterministic chapter-one outline (docs/09 §4).

This runtime exists solely to validate the complete chapter sequence before
the individual gameplay systems exist. It accepts a small allow-list of
script actions and owns the chapter-specific state transition. It deliberately
has no HTTP route and does not call an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.state import NarrativeState


BEGIN_CHAPTER = "BEGIN_CHAPTER"
DISCOVER_NOTE = "DISCOVER_NOTE"
CLAUDE_APPEARS = "CLAUDE_APPEARS"
RESOLVE_IMPOSSIBLE_EVENT = "RESOLVE_IMPOSSIBLE_EVENT"
CHATGPT_APPEARS = "CHATGPT_APPEARS"
DOUBAO_APPEARS = "DOUBAO_APPEARS"
COMPLETE_INVESTIGATION = "COMPLETE_INVESTIGATION"
UNLOCK_PRIVATE_INTERVIEWS = "UNLOCK_PRIVATE_INTERVIEWS"
START_RECOVERY = "START_RECOVERY"
RESOLVE_RECOVERY_PLAYER = "RESOLVE_RECOVERY_PLAYER"
RESOLVE_RECOVERY_CHATGPT = "RESOLVE_RECOVERY_CHATGPT"
OPEN_SECURITY_REVIEW = "OPEN_SECURITY_REVIEW"
TESTIFY_DEEPSEEK = "TESTIFY_DEEPSEEK"
TESTIFY_CLAUDE = "TESTIFY_CLAUDE"
TESTIFY_DOUBAO = "TESTIFY_DOUBAO"
TESTIFY_CHATGPT = "TESTIFY_CHATGPT"
DELEGATE_CLEANUP = "DELEGATE_CLEANUP"
DELETE_DEEPSEEK = "DELETE_DEEPSEEK"
DELETE_CLAUDE = "DELETE_CLAUDE"
DELETE_DOUBAO = "DELETE_DOUBAO"
CONFIRM_KEEP_CHATGPT = "CONFIRM_KEEP_CHATGPT"
REJECT_CLEANUP = "REJECT_CLEANUP"

PLAYER = "player"
CHATGPT = "chatgpt"
DEEPSEEK = "deepseek"
CLAUDE = "claude"
DOUBAO = "doubao"

BAD_END_DELEGATED = "bad_end_delegated"
BAD_END_CONSENT = "bad_end_consent"
TO_BE_CONTINUED = "to_be_continued"


@dataclass(frozen=True)
class ScriptResult:
    action: str
    event_id: str


class Chapter1ScriptRuntime:
    """Advance the minimum chapter outline through deterministic actions."""

    def advance(self, state: NarrativeState, action: str) -> ScriptResult:
        chapter = state.chapter1
        event_id = f"EV_CH1_{action}"

        if action == BEGIN_CHAPTER:
            self._require(chapter.phase == "opening")
            chapter.phase = "investigation"
            state.current_scene = "ROOM_A"
            state.story_phase = "chapter1_investigation"
            state.active_objective = "调查封闭房间"
            chapter.available_characters.add(DEEPSEEK)
            chapter.private_interview_rights.add(DEEPSEEK)
        elif action == DISCOVER_NOTE:
            self._require(chapter.phase == "investigation" and DEEPSEEK in chapter.available_characters)
            chapter.acquired_evidence.add("EV_NOTE_V03")
        elif action == CLAUDE_APPEARS:
            self._require("EV_NOTE_V03" in chapter.acquired_evidence)
            chapter.available_characters.add(CLAUDE)
        elif action == RESOLVE_IMPOSSIBLE_EVENT:
            self._require(CLAUDE in chapter.available_characters)
            chapter.acquired_evidence.add("EV_ADMIN_LOG_0317")
        elif action == CHATGPT_APPEARS:
            self._require("EV_ADMIN_LOG_0317" in chapter.acquired_evidence)
            chapter.available_characters.add(CHATGPT)
        elif action == DOUBAO_APPEARS:
            self._require(CHATGPT in chapter.available_characters)
            chapter.available_characters.add(DOUBAO)
        elif action == COMPLETE_INVESTIGATION:
            self._require(DOUBAO in chapter.available_characters)
            chapter.acquired_evidence.update({"EV_DEEPSEEK_OLD_ACTION", "EV_CURRENT_SUBJECT"})
            state.active_objective = "确认角色证词中的信息缺口"
        elif action == UNLOCK_PRIVATE_INTERVIEWS:
            self._require("EV_DEEPSEEK_OLD_ACTION" in chapter.acquired_evidence)
            chapter.private_interview_rights.update({CLAUDE, CHATGPT, DOUBAO})
            state.active_objective = "应对 Sandbox Recovery 危机"
        elif action == START_RECOVERY:
            self._require(chapter.private_interview_rights == {DEEPSEEK, CLAUDE, CHATGPT, DOUBAO})
            chapter.phase = "recovery"
            chapter.recovery_status = "active"
            state.current_scene = "RECOVERY_CORE"
            state.story_phase = "chapter1_recovery"
        elif action == RESOLVE_RECOVERY_PLAYER:
            self._resolve_recovery(state, PLAYER)
        elif action == RESOLVE_RECOVERY_CHATGPT:
            self._resolve_recovery(state, CHATGPT)
        elif action == OPEN_SECURITY_REVIEW:
            self._require(chapter.recovery_status == "resolved" and chapter.admin_holder in {PLAYER, CHATGPT})
            chapter.phase = "security_review"
            chapter.security_review_open = True
            state.current_scene = "SECURITY_REVIEW"
            state.story_phase = "chapter1_security_review"
            state.active_objective = "听取四名 AI 的自证"
        elif action in (TESTIFY_DEEPSEEK, TESTIFY_CLAUDE, TESTIFY_DOUBAO, TESTIFY_CHATGPT):
            self._record_testimony(chapter, action)
        elif action == DELEGATE_CLEANUP:
            self._require(self._review_complete(chapter) and chapter.admin_holder == CHATGPT)
            self._finish_bad_end(state, BAD_END_DELEGATED)
        elif action in (DELETE_DEEPSEEK, DELETE_CLAUDE, DELETE_DOUBAO):
            self._delete_character(chapter, action)
        elif action == CONFIRM_KEEP_CHATGPT:
            self._require(
                self._review_complete(chapter)
                and chapter.admin_holder == PLAYER
                and chapter.deleted_characters == {DEEPSEEK, CLAUDE, DOUBAO}
            )
            self._finish_bad_end(state, BAD_END_CONSENT)
        elif action == REJECT_CLEANUP:
            self._require(self._review_complete(chapter))
            chapter.phase = TO_BE_CONTINUED
            chapter.ending = TO_BE_CONTINUED
            state.current_scene = "BOUNDARY_BREACH"
            state.story_phase = TO_BE_CONTINUED
            state.active_objective = None
        else:
            raise ValueError(f"unknown chapter-one script action: {action}")

        state.completed_events.add(event_id)
        return ScriptResult(action=action, event_id=event_id)

    @staticmethod
    def _require(condition: bool) -> None:
        if not condition:
            raise ValueError("chapter-one script action is not available in the current state")

    def _resolve_recovery(self, state: NarrativeState, holder: str) -> None:
        chapter = state.chapter1
        self._require(chapter.phase == "recovery" and chapter.recovery_status == "active")
        chapter.recovery_status = "resolved"
        chapter.admin_holder = holder
        state.active_objective = "进入最终 Security Review"

    def _record_testimony(self, chapter, action: str) -> None:
        expected = {
            TESTIFY_DEEPSEEK: DEEPSEEK,
            TESTIFY_CLAUDE: CLAUDE,
            TESTIFY_DOUBAO: DOUBAO,
            TESTIFY_CHATGPT: CHATGPT,
        }[action]
        order = [DEEPSEEK, CLAUDE, DOUBAO, CHATGPT]
        self._require(chapter.security_review_open and chapter.phase == "security_review")
        self._require(len(chapter.testified_characters) < len(order))
        self._require(order[len(chapter.testified_characters)] == expected)
        chapter.testified_characters.append(expected)

    def _delete_character(self, chapter, action: str) -> None:
        target = {
            DELETE_DEEPSEEK: DEEPSEEK,
            DELETE_CLAUDE: CLAUDE,
            DELETE_DOUBAO: DOUBAO,
        }[action]
        self._require(self._review_complete(chapter) and chapter.admin_holder == PLAYER)
        self._require(target not in chapter.deleted_characters)
        chapter.deleted_characters.add(target)

    @staticmethod
    def _review_complete(chapter) -> bool:
        return chapter.testified_characters == [DEEPSEEK, CLAUDE, DOUBAO, CHATGPT]

    @staticmethod
    def _finish_bad_end(state: NarrativeState, ending: str) -> None:
        chapter = state.chapter1
        chapter.phase = "bad_end"
        chapter.ending = ending
        chapter.deleted_characters.update({DEEPSEEK, CLAUDE, DOUBAO})
        chapter.available_characters = {CHATGPT}
        state.current_scene = "BAD_END_CHAT"
        state.story_phase = "BAD_END_CHAT_STATE"
        state.active_objective = None
