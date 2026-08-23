"""Character mood + reasoning tests (docs/04 §9, §47).

Covers the two improvements adopted from the reference "拟人AI逻辑链拷打" template:
the persistent two-axis mood (positive/excitement) and the explicit reasoning
field, plus their wiring through parse → prompt → orchestrator commit → persistence.
"""

from __future__ import annotations

import json

from app.characters.base import (
    CharacterMood,
    CharacterRequest,
    CharacterState,
    parse_character_response,
)
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository, PersistedSession
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider


def _structured_json(dialogue: str = "好的。", **extra) -> str:
    data = {
        "character_id": "deepseek",
        "dialogue": dialogue,
        "emotion": "neutral",
        "animation_proposal": "none",
        "memory_proposals": [],
        "action_proposals": [],
        "fact_refs": [],
    }
    data.update(extra)
    return json.dumps(data, ensure_ascii=False)


# ---- parse_character_response (schema: tolerant optional fields) ----


def test_mood_parsed():
    response = parse_character_response(
        _structured_json(mood={"positive": 0.7, "excitement": -0.3}), "deepseek"
    )
    assert response.next_mood.positive == 0.7
    assert response.next_mood.excitement == -0.3


def test_mood_clamped_to_range():
    response = parse_character_response(
        _structured_json(mood={"positive": 3.0, "excitement": -5.0}), "deepseek"
    )
    assert response.next_mood.positive == 1.0
    assert response.next_mood.excitement == -1.0


def test_mood_absent_is_none():
    response = parse_character_response(_structured_json(), "deepseek")
    assert response.next_mood is None


def test_mood_non_numeric_is_none():
    response = parse_character_response(
        _structured_json(mood={"positive": "happy", "excitement": 0.0}), "deepseek"
    )
    assert response.next_mood is None


def test_reasoning_parsed():
    response = parse_character_response(
        _structured_json(reasoning="因为这是当前语境下最自然的回应。"), "deepseek"
    )
    assert response.reasoning == "因为这是当前语境下最自然的回应。"


def test_reasoning_absent_is_empty():
    response = parse_character_response(_structured_json(), "deepseek")
    assert response.reasoning == ""


# ---- prompt injection ----


def test_mood_injected_into_prompt():
    runtime = DeepSeekRuntime(MockProvider())
    user = runtime._build_user_message(
        CharacterRequest(
            character_id="deepseek",
            player_message="你好",
            mood=CharacterMood(positive=0.5, excitement=-0.2),
        )
    )
    assert "积极0.5" in user
    assert "激动-0.2" in user


def test_no_mood_keeps_clean_first_turn():
    runtime = DeepSeekRuntime(MockProvider())
    user = runtime._build_user_message(
        CharacterRequest(character_id="deepseek", player_message="你好")
    )
    assert user == "你好"


# ---- orchestrator commit + cross-turn continuity ----


class _MoodProvider(LLMProvider):
    """Returns a valid structured reply; optionally a fixed next mood."""

    def __init__(self, mood: dict | None = None) -> None:
        self._mood = mood
        self.users: list[str] = []
        self.last_thinking: dict | None = "unset"

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
    ) -> str:
        self.users.append(user)
        self.last_thinking = thinking
        extra = {"reasoning": "测试推理。"}
        if self._mood is not None:
            extra["mood"] = self._mood
        return _structured_json(**extra)


def _orchestrator(provider):
    return GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(provider)}
    )


def test_mood_commits_and_reaches_next_turn():
    provider = _MoodProvider(mood={"positive": 0.9, "excitement": 0.4})
    orchestrator = _orchestrator(provider)
    first = orchestrator.handle_turn(None, "你好")
    # First turn has no committed mood yet → no mood line in the prompt.
    assert "积极" not in provider.users[0]
    # The model's mood is committed and injected into the next turn.
    orchestrator.handle_turn(first.session_id, "你好呀")
    # mood 经确定性情绪演化（evolve_mood：衰减 + 平滑）后提交，不再是逐字值
    assert "积极0.5" in provider.users[1]
    assert "激动0.2" in provider.users[1]


def test_no_mood_output_keeps_no_mood():
    provider = _MoodProvider(mood=None)
    orchestrator = _orchestrator(provider)
    first = orchestrator.handle_turn(None, "你好")
    orchestrator.handle_turn(first.session_id, "你好呀")
    assert "积极" not in provider.users[1]


def test_reasoning_commits_and_reaches_next_turn():
    # The character's own "why I replied this way" is fed back next turn, so its
    # train of thought stays continuous (docs/04 §9 CharacterState.last_reasoning).
    provider = _MoodProvider(mood=None)
    orchestrator = _orchestrator(provider)
    first = orchestrator.handle_turn(None, "你好")
    # First turn has no committed reasoning yet → no inner-thought line.
    assert "心里想" not in provider.users[0]
    orchestrator.handle_turn(first.session_id, "你好呀")
    assert "心里想" in provider.users[1]
    assert "测试推理。" in provider.users[1]


def test_reasoning_absent_keeps_no_reasoning_line():
    class _NoReasoningProvider(LLMProvider):
        def __init__(self) -> None:
            self.users: list[str] = []

        def complete(self, **kwargs) -> str:
            self.users.append(kwargs["user"])
            return _structured_json()  # no reasoning field

    provider = _NoReasoningProvider()
    orchestrator = _orchestrator(provider)
    first = orchestrator.handle_turn(None, "你好")
    orchestrator.handle_turn(first.session_id, "你好呀")
    assert "心里想" not in provider.users[1]


def test_runtime_does_not_disable_thinking():
    # The shared runtime used to pass thinking={"type": "disabled"}; it now
    # leaves thinking to the provider default (on for DeepSeek), so the model
    # reasons before answering ("逻辑链拷打").
    provider = _MoodProvider(mood=None)
    runtime = DeepSeekRuntime(provider)
    runtime.respond(CharacterRequest(character_id="deepseek", player_message="你好"))
    assert provider.last_thinking is None


# ---- persistence ----


def test_character_states_persist_round_trip(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    repo.save(
        PersistedSession(
            session_id="s1",
            character_states={
                "deepseek": CharacterState(mood=CharacterMood(0.4, -0.6))
            },
        )
    )
    loaded = repo.load("s1")
    assert loaded.character_states["deepseek"].mood.positive == 0.4
    assert loaded.character_states["deepseek"].mood.excitement == -0.6


def test_reasoning_persists_round_trip(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    repo.save(
        PersistedSession(
            session_id="s1",
            character_states={
                "deepseek": CharacterState(
                    mood=CharacterMood(0.4, -0.6),
                    last_reasoning="她好像有点可疑。",
                )
            },
        )
    )
    loaded = repo.load("s1")
    assert loaded.character_states["deepseek"].last_reasoning == "她好像有点可疑。"


def test_legacy_flat_mood_snapshot_loads_as_character_state(tmp_path):
    # Backward compatible: snapshots written before CharacterState existed
    # stored character_states as a flat mood dict; they must still load.
    repo = JsonSessionRepository(tmp_path)
    repo.save(PersistedSession(session_id="legacy"))
    path = tmp_path / "legacy.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["character_states"] = {"deepseek": {"positive": 0.4, "excitement": -0.6}}
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = repo.load("legacy")
    state = loaded.character_states["deepseek"]
    assert state.mood.positive == 0.4
    assert state.mood.excitement == -0.6
    assert state.last_reasoning == ""


def test_mood_survives_session_restore(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    provider1 = _MoodProvider(mood={"positive": 0.8, "excitement": 0.1})
    orchestrator1 = GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(provider1)}, repository=repo
    )
    result = orchestrator1.handle_turn(None, "你好")

    # A "fresh process": new SessionStore, same repository on disk.
    provider2 = _MoodProvider(mood={"positive": 0.0, "excitement": 0.0})
    orchestrator2 = GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(provider2)}, repository=repo
    )
    orchestrator2.handle_turn(result.session_id, "你好呀")
    # The restored mood is injected into the first prompt of the new process.
    # (0.8 经 evolve_mood 平滑后约为 0.5)
    assert "积极0.5" in provider2.users[0]
    assert "激动0.1" in provider2.users[0]


def test_snapshot_without_character_states_loads_empty(tmp_path):
    # Backward compatible: a snapshot written before the mood state existed has
    # no "character_states" key and must load with an empty dict, not crash.
    repo = JsonSessionRepository(tmp_path)
    repo.save(PersistedSession(session_id="legacy"))
    path = tmp_path / "legacy.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["character_states"]
    path.write_text(json.dumps(data), encoding="utf-8")

    loaded = repo.load("legacy")
    assert loaded.character_states == {}
