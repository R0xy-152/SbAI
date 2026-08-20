"""快速上线固定剧本 Runtime 测试（临时组件，story_runtime.py）。

覆盖：
1. 内容载入校验（fail closed：坏 speaker / emotion / 空台词 / 嵌套选项 / 重复 id）；
2. 游标语义：advance 起步 → 选项跳转 → 合并回主线 → end；
3. 全流程走查：3 个选项点、14 个场景、结尾 kind=end；
4. 快照/恢复：runtime 内存快照与 PersistedSession JSON 往返；
5. Orchestrator 集成：台词进历史、持久化恢复、场景边界 AUTO 自动存档、
   未接线时 story 端点 fail closed。

约定：本文件只验证临时故事模式；旧调查玩法（docs/10-14）的既有测试
必须保持全绿（防回归由整个 pytest 套件保证）。
"""

from __future__ import annotations

import pytest

from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import (
    PersistedSession,
    JsonSessionRepository,
    _session_from_dict,
    _session_to_dict,
)
from app.save.repository import JsonSaveRepository
from app.save.service import SaveSnapshotService
from app.script.story_content import SCENES
from app.script.story_runtime import StoryContentError, StoryRuntime

EXPECTED_SCENE_IDS = [
    "CH01-SC01", "CH01-SC02", "CH01-SC03", "CH01-SC04", "CH01-SC05",
    "CH01-SC06", "CH01-SC07", "CH01-SC08", "CH01-SC09", "CH01-SC10",
    "CH01-SC11", "CH01-SC12", "CH01-SC13", "CH01-SC14",
]
EXPECTED_CHOICE_IDS = {
    "SC01_OPENING_ATTITUDE",
    "SC03_LIGHT_FEEDBACK",
    "SC09_RELATION_FEEDBACK",
}


class _Runtime:
    """与 test_script_dsl.py 相同的占位角色 runtime（故事模式不调用它）。"""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="……")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="……")


def _runtimes() -> dict:
    return {
        character: _Runtime(character)
        for character in ("deepseek", "claude", "chatgpt", "doubao")
    }


def _walk_choices(runtime: StoryRuntime, session_id: str, pick: str) -> None:
    """从任意位置一路 advance 到 finished；遇到选项一律选 pick。"""
    guard = 0
    while True:
        guard += 1
        assert guard < 10_000, "walk did not terminate"
        if runtime.finished(session_id):
            return
        view = runtime.current(session_id)
        if view["kind"] == "choice":
            runtime.choose(session_id, pick)
            continue
        view, _ = runtime.advance(session_id)
        if view["kind"] == "end":
            return


# ── 1. 内容载入校验 ────────────────────────────────────────────────────────


def test_story_content_loads():
    runtime = StoryRuntime()
    assert runtime.total_nodes > 100
    choice_ids = {
        node.choice_id for node in runtime._nodes if hasattr(node, "choice_id")
    }
    assert choice_ids == EXPECTED_CHOICE_IDS


def test_story_content_scene_ids():
    assert [scene["scene_id"] for scene in SCENES] == EXPECTED_SCENE_IDS


def test_story_content_unknown_speaker_fails():
    bad = [
        {
            "scene_id": "S1",
            "steps": [{"speaker": "grok", "text": "hello", "emotion": "neutral"}],
        }
    ]
    with pytest.raises(StoryContentError):
        StoryRuntime(scenes=bad)


def test_story_content_bad_emotion_fails():
    bad = [
        {
            "scene_id": "S1",
            "steps": [{"speaker": "deepseek", "text": "hi", "emotion": "kawaii"}],
        }
    ]
    with pytest.raises(StoryContentError):
        StoryRuntime(scenes=bad)


def test_story_content_empty_and_nested_fail():
    with pytest.raises(StoryContentError):
        StoryRuntime(scenes=[{"scene_id": "S1", "steps": []}])
    nested = [
        {
            "scene_id": "S1",
            "steps": [
                {
                    "choice": "C1",
                    "options": [
                        {
                            "id": "A",
                            "label": "a",
                            "lines": [
                                {
                                    "choice": "C2",
                                    "options": [{"id": "A", "label": "a", "lines": [{"speaker": "system", "text": "x"}]}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    with pytest.raises(StoryContentError):
        StoryRuntime(scenes=nested)


# ── 2. 游标语义 ────────────────────────────────────────────────────────────


def test_advance_starts_at_first_node():
    runtime = StoryRuntime()
    assert not runtime.started("s1")
    view, scene_changed = runtime.advance("s1")
    assert view["kind"] == "line"
    assert view["speaker"] == "system"
    assert view["text"] == "SYSTEM INITIALIZING..."
    assert scene_changed is True  # 首次 advance 视为场景边界（触发首个 AUTO）
    assert runtime.current("s1") == view


def test_choice_jump_and_merge():
    runtime = StoryRuntime()
    session = "s1"
    view, _ = runtime.advance(session)
    # 走到第一个选项点
    guard = 0
    while view["kind"] != "choice":
        view, _ = runtime.advance(session)
        guard += 1
        assert guard < 500
    assert view["choice_id"] == "SC01_OPENING_ATTITUDE"
    assert [o["id"] for o in view["options"]] == ["A", "B", "C"]
    assert view["options"][0]["label"] == "“你是谁？”"
    # 选 B：跳到分支第一句
    branch = runtime.choose(session, "B")
    assert branch["kind"] == "line"
    assert branch["speaker"] == "player"
    assert branch["text"] == "你看起来比我还紧张。"
    # 走完分支（分支共 5 句：player + 4 句回应）后应合并回主线 unified dialogue
    for _ in range(5):
        branch, _ = runtime.advance(session)
    assert branch["speaker"] == "deepseek"
    assert branch["text"] == "不过有一件事可以先确定。"
    # 错误选项 / 非选项点 choose
    with pytest.raises(ValueError):
        runtime.choose(session, "Z")
    with pytest.raises(ValueError):
        runtime.choose(session, "A")  # 当前节点不是选项


def test_choose_requires_started():
    runtime = StoryRuntime()
    with pytest.raises(ValueError):
        runtime.choose("never", "A")


# ── 3. 全流程走查 ──────────────────────────────────────────────────────────


def test_full_walkthrough_all_choices_a():
    runtime = StoryRuntime()
    session = "s1"
    chosen = []
    scene_changes = 0
    guard = 0
    while not runtime.finished(session):
        guard += 1
        assert guard < 10_000
        view = runtime.current(session) if runtime.started(session) else None
        if view is not None and view["kind"] == "choice":
            chosen.append(view["choice_id"])
            runtime.choose(session, "A")
            continue
        view, changed = runtime.advance(session)
        if changed:
            scene_changes += 1
        if view["kind"] == "end":
            break
    assert chosen == ["SC01_OPENING_ATTITUDE", "SC03_LIGHT_FEEDBACK", "SC09_RELATION_FEEDBACK"]
    # 14 个场景边界 + 结尾 end 节点本身算一次 scene_changed
    assert scene_changes == 15
    assert runtime.current(session)["kind"] == "end"


def test_three_branches_reach_same_merge():
    """三个选项各自选走全程，都能正常到达结尾（不同分支互不卡死）。"""
    for pick in ("A", "B", "C"):
        runtime = StoryRuntime()
        session = f"s-{pick}"
        view, _ = runtime.advance(session)
        guard = 0
        while not runtime.finished(session):
            guard += 1
            assert guard < 10_000
            if view["kind"] == "choice":
                view = runtime.choose(session, pick)
                continue
            view, _ = runtime.advance(session)
            if view["kind"] == "end":
                break
        assert runtime.finished(session)


# ── 4. 快照 / 恢复 ─────────────────────────────────────────────────────────


def test_runtime_snapshot_restore_roundtrip():
    source = StoryRuntime()
    view, _ = source.advance("s1")
    for _ in range(5):
        view, _ = source.advance("s1")
    snapshot = source.snapshot("s1")
    assert snapshot == {"node_index": 5}
    target = StoryRuntime()
    target.restore("s1", snapshot)
    assert target.current("s1") == view
    # 未开始会话 snapshot 为 None；restore(None) 清空
    assert source.snapshot("other") is None
    source.restore("s1", None)
    assert not source.started("s1")


def test_persisted_session_roundtrip_carries_story_cursor():
    persisted = PersistedSession(session_id="abc", story_cursor={"node_index": 42})
    data = _session_to_dict(persisted)
    assert data["story_cursor"] == {"node_index": 42}
    restored = _session_from_dict(data)
    assert restored.story_cursor == {"node_index": 42}
    # 旧快照无 story_cursor → None（向后兼容）
    data.pop("story_cursor")
    assert _session_from_dict(data).story_cursor is None


# ── 5. Orchestrator 集成 ───────────────────────────────────────────────────


def _wired(tmp_path):
    session_repo = JsonSessionRepository(tmp_path / "sessions")
    save_repo = JsonSaveRepository(tmp_path / "saves")
    orchestrator = GameOrchestrator(
        SessionStore(),
        _runtimes(),
        repository=session_repo,
        story_runtime=StoryRuntime(),
    )
    service = SaveSnapshotService(save_repo)
    orchestrator._save_service = service
    return orchestrator, service


def test_orchestrator_story_flow_and_persistence(tmp_path):
    orchestrator, service = _wired(tmp_path)
    # 首次 advance：新会话铸造 + 第一句台词
    first = orchestrator.story_advance(None, player_id="p1")
    session_id = first["session_id"]
    assert first["started"] and not first["finished"]
    assert first["node"]["text"] == "SYSTEM INITIALIZING..."
    assert first["scene_changed"] is True
    # 台词已进历史
    history = orchestrator.get_history(session_id)
    assert history[-1]["content"] == "SYSTEM INITIALIZING..."
    # 第一个场景边界 → AUTO 自动存档
    assert service.list_saves("p1")["auto"] is not None
    # 走到选项点并选择
    view = first
    guard = 0
    while view["node"]["kind"] != "choice":
        view = orchestrator.story_advance(session_id, player_id="p1")
        guard += 1
        assert guard < 500
    choice_id = view["node"]["choice_id"]
    picked = orchestrator.story_choose(session_id, "C", player_id="p1")
    assert picked["node"]["speaker"] == "player"
    # 历史里记录了选项 label 与分支台词
    fresh_history = orchestrator.get_history(session_id)
    assert any(m.get("content", "").startswith("“") for m in fresh_history if m["role"] == "player")
    # 持久化恢复：新 orchestrator 从仓库恢复同一会话
    orchestrator2, _ = _wired(tmp_path)
    restored = orchestrator2.story_current(session_id)
    assert restored["started"] and not restored["finished"]
    assert restored["node"] == picked["node"]
    # 快照含 story_cursor
    assert orchestrator._repository.load(session_id).story_cursor["node_index"] >= 0


def test_orchestrator_story_to_end(tmp_path):
    orchestrator, service = _wired(tmp_path)
    first = orchestrator.story_advance(None, player_id="p1")
    session_id = first["session_id"]
    view = first
    guard = 0
    while not view["finished"]:
        if view["node"]["kind"] == "choice":
            view = orchestrator.story_choose(session_id, "A", player_id="p1")
            continue
        view = orchestrator.story_advance(session_id, player_id="p1")
        guard += 1
        assert guard < 10_000
    assert view["node"]["kind"] == "end"
    # 结尾后 AUTO 存档存在且可列
    assert service.list_saves("p1")["auto"] is not None
    # 再 advance：保持 finished（幂等）
    again = orchestrator.story_advance(session_id, player_id="p1")
    assert again["finished"] and again["node"]["kind"] == "end"


def test_story_endpoints_fail_closed_without_runtime():
    orchestrator = GameOrchestrator(SessionStore(), _runtimes())
    with pytest.raises(ValueError):
        orchestrator.story_advance(None)
