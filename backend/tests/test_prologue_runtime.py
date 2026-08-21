"""docs/19 prologue: unordered visits, persistence and free-chat routing."""

from __future__ import annotations

from itertools import permutations

import pytest

from app.characters.base import CharacterResponse
from app.game.orchestrator import CharacterUnavailable, GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository
from app.script.prologue_content import (
    PROLOGUE_CHARACTERS,
    PROLOGUE_CONTENT,
    SCENE_PRESENTATION,
    SCENE_TITLES,
)
from app.script.prologue_runtime import PrologueRuntime
from app.script.story_runtime import StoryRuntime


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="自由交流回复")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="……")


def _runtimes() -> dict:
    return {character_id: _Runtime(character_id) for character_id in (*PROLOGUE_CHARACTERS, "doubao")}


def _advance_to_choice(runtime: PrologueRuntime, session_id: str) -> dict:
    view = runtime.current(session_id) if runtime.started(session_id) else None
    for _ in range(1000):
        if view is not None and view["kind"] == "choice":
            return view
        view, _ = runtime.advance(session_id)
    raise AssertionError("prologue did not reach a choice")


def test_docs_first_content_is_compiled_and_main_maps_to_neutral():
    assert set(PROLOGUE_CONTENT) == {
        "intro", "deepseek", "chatgpt", "claude", "reunion", "aftertalk"
    }
    assert sum(len(lines) for lines in PROLOGUE_CONTENT.values()) > 100
    assert all(
        line["emotion"] != "main"
        for lines in PROLOGUE_CONTENT.values()
        for line in lines
    )
    assert PROLOGUE_CONTENT["intro"][0]["text"] == "今天难得有空。"
    assert all(
        "后日谈" not in line["text"]
        for lines in PROLOGUE_CONTENT.values()
        for line in lines
    )
    assert SCENE_TITLES["PROLOGUE-AFTERTALK"] == "序章自由交流"

    reunion = PrologueRuntime().scene_info("PROLOGUE-REUNION")
    characters = reunion["presentation"]["characters"]
    assert [character["character_id"] for character in characters] == list(
        PROLOGUE_CHARACTERS
    )
    # 与前期单人探班一致：三人集合不再缩小/下沉立绘（scale/offset_y 缺省 = 原尺寸同基线）
    assert all("scale" not in character for character in characters)
    assert all("offset_y" not in character for character in characters)
    assert [character["slot"] for character in characters] == ["LEFT", "CENTER", "RIGHT"]
    assert all(
        scene["background"] == "/backgroud/background_prologue.png"
        for scene in SCENE_PRESENTATION.values()
    )
    assert PrologueRuntime.chapter_opening() == {
        "chapter_label": "序章",
        "title": "制作现场突击检查！AI娘们的秘密日常",
        "background": "/backgroud/background_prologue.png",
    }


@pytest.mark.parametrize("order", list(permutations(PROLOGUE_CHARACTERS)))
def test_all_six_visit_orders_only_offer_remaining_characters(order):
    runtime = PrologueRuntime()
    session_id = "session"
    for index, character_id in enumerate(order):
        choice = _advance_to_choice(runtime, session_id)
        assert choice["choice_id"] == "PROLOGUE_VISIT_CHARACTER"
        assert [option["id"] for option in choice["options"]] == [
            candidate
            for candidate in PROLOGUE_CHARACTERS
            if candidate not in order[:index]
        ]
        first_line = runtime.choose(session_id, character_id)
        assert first_line["scene_id"] == f"PROLOGUE-{character_id.upper()}"

    final_choice = _advance_to_choice(runtime, session_id)
    assert final_choice["choice_id"] == "PROLOGUE_CHAT_CHARACTER"
    assert [option["id"] for option in final_choice["options"]] == list(PROLOGUE_CHARACTERS)
    chat = runtime.choose(session_id, "chatgpt")
    assert chat == {
        "kind": "chat",
        "character_id": "chatgpt",
        "scene_id": "PROLOGUE-AFTERTALK",
    }
    assert runtime.finished(session_id)


def test_visit_choice_rejects_advance_unknown_and_repeat():
    runtime = PrologueRuntime()
    choice = _advance_to_choice(runtime, "s")
    assert choice["kind"] == "choice"
    with pytest.raises(ValueError, match="must choose"):
        runtime.advance("s")
    with pytest.raises(ValueError, match="unknown option"):
        runtime.choose("s", "doubao")
    runtime.choose("s", "deepseek")
    next_choice = _advance_to_choice(runtime, "s")
    assert "deepseek" not in {option["id"] for option in next_choice["options"]}
    with pytest.raises(ValueError, match="already been visited"):
        runtime.choose("s", "deepseek")


def test_snapshot_restore_keeps_visited_set_and_branch_line():
    source = PrologueRuntime()
    _advance_to_choice(source, "s")
    source.choose("s", "claude")
    source.advance("s")
    snapshot = source.snapshot("s")
    assert snapshot is not None and snapshot["story_id"] == "prologue"

    target = PrologueRuntime()
    target.restore("restored", snapshot)
    assert target.current("restored") == source.current("s")
    assert target.snapshot("restored")["active_character_id"] == "claude"


@pytest.mark.parametrize("character_id", PROLOGUE_CHARACTERS)
def test_final_choice_accepts_each_ai_character(character_id):
    runtime = PrologueRuntime()
    runtime.restore(
        "s",
        {
            "story_id": "prologue",
            "phase": "chat_choice",
            "line_index": 0,
            "visited_character_ids": list(PROLOGUE_CHARACTERS),
            "active_character_id": None,
            "chat_character_id": None,
        },
    )
    node = runtime.choose("s", character_id)
    assert node["kind"] == "chat"
    assert node["character_id"] == character_id
    assert runtime.chat_character("s") == character_id


def _wired(tmp_path) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        _runtimes(),
        repository=JsonSessionRepository(tmp_path / "sessions"),
        availability={
            "claude": "claude_has_appeared",
            "chatgpt": "chatgpt_has_appeared",
        },
        story_runtime=StoryRuntime(),
        prologue_runtime=PrologueRuntime(),
    )


def test_orchestrator_persists_prologue_and_locks_aftertalk_character(tmp_path):
    orchestrator = _wired(tmp_path)
    view = orchestrator.story_advance(None, story_id="prologue")
    session_id = view["session_id"]
    order = ("deepseek", "claude", "chatgpt")
    visit_index = 0
    for _ in range(2000):
        node = view["node"]
        if node["kind"] == "choice":
            option = (
                order[visit_index]
                if node["choice_id"] == "PROLOGUE_VISIT_CHARACTER"
                else "claude"
            )
            if node["choice_id"] == "PROLOGUE_VISIT_CHARACTER":
                visit_index += 1
            view = orchestrator.story_choose(
                session_id, option, story_id="prologue"
            )
        else:
            view = orchestrator.story_advance(session_id, story_id="prologue")
        if view["finished"]:
            break
    assert view["node"]["character_id"] == "claude"
    persisted = orchestrator._repository.load(session_id)
    assert persisted.story_cursor["story_id"] == "prologue"
    assert persisted.story_cursor["visited_character_ids"] == list(order)

    restored = _wired(tmp_path)
    current = restored.story_current(session_id, story_id="prologue")
    assert current["finished"] and current["node"]["character_id"] == "claude"
    state = restored.get_investigation_state(session_id)
    assert state["chat_character_id"] == "claude"
    assert state["available_characters"] == ["claude"]

    result = restored.handle_turn(session_id, "你好", character_id="claude")
    assert result.response.character_id == "claude"
    with pytest.raises(CharacterUnavailable):
        restored.handle_turn(session_id, "你好", character_id="deepseek")
