"""docs/21 §4：7 个埋点点位的端到端事件序列（orchestrator 级）。"""

from __future__ import annotations

import json

from app.characters.base import CharacterRequest, CharacterResponse
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.ops.events import (
    EVENT_AI_CHAT_ENTER,
    EVENT_AI_CHAT_TURN,
    EVENT_PROLOGUE_CHOICE,
    EVENT_PROLOGUE_COMPLETED,
    EVENT_PROLOGUE_START,
    EVENT_PROLOGUE_VISIT_CHOSEN,
    EVENT_PROLOGUE_VISIT_COMPLETED,
    EVENT_VALIDATION_REJECT,
    MemoryOpsRecorder,
)
from app.persistence.repository import JsonSessionRepository
from app.script.prologue_content import PROLOGUE_CHARACTERS
from app.script.prologue_runtime import PrologueRuntime
from app.script.story_runtime import StoryRuntime


class _Runtime:
    """返回合法回复的测试 runtime（respond 签名不带 metrics，兼容 docs/21 前）。"""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="自由交流回复")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="……")


class _WrongCharacterRuntime(_Runtime):
    """回复里 character_id 与当前角色不符 → 确定性门必拒。"""

    def respond(self, request):
        return CharacterResponse(character_id="claude", dialogue="我是别的角色")


class _MetricProvider:
    """填充 metrics 出参的最小 Provider（docs/21 §4 累加约定）。"""

    supports_metrics = True

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
        thinking: dict | None = None,
        metrics: dict | None = None,
    ) -> str:
        if metrics is not None:
            metrics["latency_ms"] = metrics.get("latency_ms", 0.0) + 12.5
            metrics["prompt_tokens"] = metrics.get("prompt_tokens", 0) + 100
            metrics["completion_tokens"] = metrics.get("completion_tokens", 0) + 20
            metrics["cache_hit_tokens"] = metrics.get("cache_hit_tokens", 0) + 80
            metrics["cache_miss_tokens"] = metrics.get("cache_miss_tokens", 0) + 20
            metrics["model"] = "fake-model"
            metrics["calls"] = metrics.get("calls", 0) + 1
        return json.dumps(
            {
                "character_id": "deepseek",
                "dialogue": "带指标的测试回复",
                "emotion": "neutral",
                "animation_proposal": "none",
                "memory_proposals": [],
                "action_proposals": [],
                "fact_refs": [],
                "reasoning": "测试推理",
                "relationship": "familiar",
                "mood": {"positive": 0.0, "excitement": 0.0},
            },
            ensure_ascii=False,
        )


def _runtimes(kind: type = _Runtime) -> dict:
    return {cid: kind(cid) for cid in (*PROLOGUE_CHARACTERS, "doubao")}


def _wired(tmp_path, runtimes: dict | None = None) -> tuple[GameOrchestrator, MemoryOpsRecorder]:
    ops = MemoryOpsRecorder()
    orchestrator = GameOrchestrator(
        SessionStore(),
        runtimes or _runtimes(),
        repository=JsonSessionRepository(tmp_path / "sessions"),
        availability={
            "claude": "claude_has_appeared",
            "chatgpt": "chatgpt_has_appeared",
        },
        story_runtime=StoryRuntime(),
        prologue_runtime=PrologueRuntime(),
        ops=ops,
    )
    return orchestrator, ops


def _finish_prologue(orchestrator: GameOrchestrator) -> tuple[str, str]:
    view = orchestrator.story_advance(None, story_id="prologue")
    session_id = view["session_id"]
    for _ in range(2000):
        node = view["node"]
        if node["kind"] == "choice":
            option = node["options"][0]["id"]
            view = orchestrator.story_choose(session_id, option, story_id="prologue")
        else:
            view = orchestrator.story_advance(session_id, story_id="prologue")
        if view["finished"]:
            break
    return session_id, view["node"]["character_id"]


def _names(ops: MemoryOpsRecorder) -> list[str]:
    return [e.event_name for e in ops.list_events()]


def test_prologue_event_sequence(tmp_path):
    orchestrator, ops = _wired(tmp_path)
    session_id, chat_character = _finish_prologue(orchestrator)
    names = _names(ops)
    assert names.count(EVENT_PROLOGUE_START) == 1
    assert names.count(EVENT_PROLOGUE_CHOICE) == 4  # 3 次探班 + 1 次聊天选择
    assert names.count(EVENT_PROLOGUE_VISIT_CHOSEN) == 3
    assert names.count(EVENT_PROLOGUE_VISIT_COMPLETED) == 3
    assert names.count(EVENT_PROLOGUE_COMPLETED) == 1

    visit_orders = [
        e.payload["order"]
        for e in ops.list_events(event_name=EVENT_PROLOGUE_VISIT_CHOSEN)
    ]
    assert sorted(visit_orders) == [1, 2, 3]
    completed = ops.list_events(event_name=EVENT_PROLOGUE_COMPLETED)
    assert completed[0].payload["chat_character_id"] == chat_character
    # 事件携带会话 id，可按会话追溯
    assert all(e.session_id == session_id for e in ops.list_events())


def test_ai_chat_enter_once_and_turn_metric(tmp_path):
    orchestrator, ops = _wired(tmp_path)
    session_id, chat_character = _finish_prologue(orchestrator)
    orchestrator.handle_turn(session_id, "你好呀", player_id="player-1")
    orchestrator.handle_turn(session_id, "在吗", player_id="player-1")
    enters = ops.list_events(event_name=EVENT_AI_CHAT_ENTER)
    assert len(enters) == 1  # 每会话一次
    assert enters[0].payload["character_id"] == chat_character
    assert enters[0].user_id == "player-1"
    assert ops.list_events(event_name=EVENT_AI_CHAT_TURN)  # _Runtime 无指标 → 只记事件


def test_ai_chat_turn_metric_from_provider(tmp_path):
    runtimes = _runtimes()
    runtimes["deepseek"] = DeepSeekRuntime(_MetricProvider())
    orchestrator, ops = _wired(tmp_path, runtimes)
    session_id, _ = _finish_prologue(orchestrator)
    # 序章首位聊天角色按选项顺序是 deepseek（_finish_prologue 总是选第一个）。
    orchestrator.handle_turn(session_id, "你好", player_id="player-1")
    turns = ops.list_events(event_name=EVENT_AI_CHAT_TURN)
    assert len(turns) == 1
    assert turns[0].payload["provider"] == "fake-model"
    assert turns[0].payload["validation"] == "approved"
    metrics = ops.list_chat_metrics()
    assert len(metrics) == 1
    metric = metrics[0]
    assert metric.provider == "fake-model"
    assert metric.latency_ms == 12.5
    assert metric.prompt_tokens == 100 and metric.completion_tokens == 20
    assert metric.cache_hit_tokens == 80 and metric.cache_miss_tokens == 20
    assert metric.user_id == "player-1"


def test_validation_reject_recorded(tmp_path):
    runtimes = _runtimes(_WrongCharacterRuntime)
    orchestrator, ops = _wired(tmp_path, runtimes)
    session_id, _ = _finish_prologue(orchestrator)
    result = orchestrator.handle_turn(session_id, "你好", player_id="player-1")
    assert result.response.dialogue == "……"  # safe fallback
    rejects = ops.list_events(event_name=EVENT_VALIDATION_REJECT)
    assert len(rejects) == 1
    assert rejects[0].payload["gate"] == "deterministic"
    assert "character_id" in rejects[0].payload["reason"]
    turns = ops.list_events(event_name=EVENT_AI_CHAT_TURN)
    assert turns[0].payload["validation"] == "rejected"
