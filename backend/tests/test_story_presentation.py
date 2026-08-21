"""故事模式场景演出配置测试（SCENE_PRESENTATION / scene_info / 存档进度）。

覆盖：
1. 演出配置 fail closed：未知 scene_id / 未知 effect / 非法 lighting 拒绝启动；
2. scene_info：已知场景返回标题与演出指令；未知场景 / None 返回 None；
3. orchestrator 故事视图携带 scene（标题 / presentation）；
4. story_progress：游标快照 + finished（存档路由数据源）。
"""

from __future__ import annotations

import pytest

from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository
from app.script.story_content import SCENE_PRESENTATION, SCENES
from app.script.story_runtime import StoryContentError, StoryRuntime


class _Runtime:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id


def _make_orchestrator(tmp_path) -> GameOrchestrator:
    runtimes = {cid: _Runtime(cid) for cid in ("deepseek", "claude", "chatgpt", "doubao")}
    return GameOrchestrator(
        sessions=SessionStore(),
        runtimes=runtimes,
        repository=JsonSessionRepository(tmp_path / "sessions"),
        story_runtime=StoryRuntime(),
    )


def test_scene_presentation_references_only_known_scenes():
    # 已知场景：载入成功（StoryRuntime 构造即校验）
    StoryRuntime()
    known = {s["scene_id"] for s in SCENES}
    for scene_id in SCENE_PRESENTATION:
        assert scene_id in known


def test_scene_presentation_unknown_scene_fails(monkeypatch):
    monkeypatch.setattr(
        "app.script.story_runtime.SCENE_PRESENTATION",
        {"CH01-SC99": {"effects": ["SCREEN_GLITCH"]}},
    )
    with pytest.raises(StoryContentError):
        StoryRuntime()


def test_scene_presentation_unknown_effect_fails(monkeypatch):
    monkeypatch.setattr(
        "app.script.story_runtime.SCENE_PRESENTATION",
        {"CH01-SC01": {"effects": ["EXPLOSION"]}},
    )
    with pytest.raises(StoryContentError):
        StoryRuntime()


def test_scene_presentation_bad_lighting_fails(monkeypatch):
    monkeypatch.setattr(
        "app.script.story_runtime.SCENE_PRESENTATION",
        {"CH01-SC01": {"lighting": "dark"}},
    )
    with pytest.raises(StoryContentError):
        StoryRuntime()


def test_scene_info_known_scene():
    runtime = StoryRuntime()
    info = runtime.scene_info("CH01-SC05")
    assert info is not None
    assert info["scene_id"] == "CH01-SC05"
    assert info["title"] == "03:17 Incident"
    assert info["presentation"] == SCENE_PRESENTATION["CH01-SC05"]
    assert runtime.chapter_opening() == {
        "chapter_label": "第一章",
        "title": "03:17 Incident",
        "background": "/backgroud/background1.png",
    }


def test_scene_info_unknown_and_none():
    runtime = StoryRuntime()
    assert runtime.scene_info("CH01-SC99") is None
    assert runtime.scene_info(None) is None


def test_story_advance_carries_scene(tmp_path):
    orch = _make_orchestrator(tmp_path)
    view = orch.story_advance(None)
    assert view["scene_changed"] is True
    scene = view["scene"]
    assert scene["scene_id"] == "CH01-SC01"
    assert scene["title"] == "Awakening"
    assert scene["presentation"] == {}
    assert view["chapter_opening"] == StoryRuntime.chapter_opening()


def test_story_progress(tmp_path):
    orch = _make_orchestrator(tmp_path)
    first = orch.story_advance(None)
    sid = first["session_id"]
    progress = orch.story_progress(sid)
    assert progress["story_cursor"] == {"node_index": 0}
    assert progress["story_finished"] is False
    orch.story_advance(sid)
    progress = orch.story_progress(sid)
    assert progress["story_cursor"] == {"node_index": 1}
