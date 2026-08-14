"""Game Orchestrator (docs/02 §13-14).

Coordinates one player interaction: resolve the session, determine the current
character runtime, call it, and persist the messages. It does not contain
persona prompts or provider HTTP details.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
from app.game.context import CONTEXT_BUILDERS
from app.game.state.session import SessionStore
from app.game.scene import Scene

# docs/05 §8: Recent Conversation is a window of the last 10-20 rounds of
# messages, not the whole session history. 20 messages = 10 rounds.
RECENT_WINDOW_MESSAGES = 20


@dataclass
class TurnResult:
    session_id: str
    response: CharacterResponse
    message_count: int


class GameOrchestrator:
    def __init__(
        self,
        sessions: SessionStore,
        runtimes: dict[str, CharacterRuntime],
        default_character: str = "deepseek",
        scene: Scene | None = None,
    ) -> None:
        self._sessions = sessions
        self._runtimes = runtimes
        self._default_character = default_character
        # TV-08: the backend owns the current Scene (docs/03 §5.1). The
        # default is the binding-room validation fixture, which carries a
        # visual ground truth (wall_code=0317) that DeepSeek must never
        # receive (docs/04 §20). The Scene itself never reaches a character —
        # only the Context Builder's filtered output does.
        self._scene = scene if scene is not None else Scene(scene_id="binding_room")

    def handle_turn(self, session_id: str | None, message: str) -> TurnResult:
        session = self._sessions.get_or_create(session_id)
        self._sessions.append_message(
            session.session_id, {"role": "player", "content": message}
        )

        # TV-04: the current responding character is fixed to the default.
        # Character selection from natural language is an Orchestrator /
        # Narrative decision (docs/04 §61), deferred to later TV items.
        runtime = self._runtimes[self._default_character]
        context = CONTEXT_BUILDERS[self._default_character](self._scene)
        response = runtime.respond(
            CharacterRequest(
                character_id=self._default_character,
                player_message=message,
                # TV-07: short-term context = the last window of prior messages
                # (docs/05 §8), excluding the current player message.
                recent_conversation=session.messages[:-1][-RECENT_WINDOW_MESSAGES:],
                # TV-08: authorized, visual-filtered environment context
                # (docs/04 §15, §20).
                environment_info=context.environment_info,
            )
        )
        self._sessions.append_message(
            session.session_id,
            {
                "role": "character",
                "character_id": response.character_id,
                "content": response.dialogue,
            },
        )

        return TurnResult(
            session_id=session.session_id,
            response=response,
            message_count=session.player_turn_count(),
        )
