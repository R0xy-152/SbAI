"""docs/21 §6：反馈分类器（去重/失败隔离）与人工抽检 Precision。"""

from __future__ import annotations

import json

from app.auth import DeveloperNote
from app.ops.feedback import (
    FeedbackClassifier,
    FeedbackEvaluator,
    MemoryFeedbackStore,
)


class _FakeProvider:
    """返回合法分类 JSON 的最小 Provider。"""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._responses = responses or {}
        self.calls: list[str] = []

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
        self.calls.append(user)
        for marker, raw in self._responses.items():
            if marker in user:
                return raw
        return json.dumps(
            {
                "dedupe_key": "common-topic",
                "topic": "bug",
                "severity": "high",
                "scene": "prologue_visit_deepseek",
                "is_duplicate_of": None,
                "summary": "默认概括",
            },
            ensure_ascii=False,
        )


class _NotesSource:
    def __init__(self, notes: list[DeveloperNote]) -> None:
        self._notes = notes

    def list_developer_notes(self) -> list[DeveloperNote]:
        return self._notes


def _note(session_id: str, content: str) -> DeveloperNote:
    return DeveloperNote(
        user_id="u1",
        display_name="测试玩家",
        label=None,
        character_id="deepseek",
        content=content,
        session_id=session_id,
        created_at=None,
    )


def test_classify_pending_stores_analysis():
    notes = _NotesSource([_note("n1", "序章 DeepSeek 篇卡住了")])
    store = MemoryFeedbackStore()
    classifier = FeedbackClassifier(_FakeProvider(), notes, store, model_name="fake")
    done = classifier.classify_pending()
    assert len(done) == 1 and done[0].status == "classified"
    analyses = store.list_analyses()
    assert len(analyses) == 1
    assert analyses[0].topic == "bug" and analyses[0].severity == "high"
    assert analyses[0].model == "fake"
    # 幂等：已分析留言不重复调用
    assert classifier.classify_pending() == []


def test_dedupe_points_to_first_note():
    notes = _NotesSource(
        [_note("n1", "序章 DeepSeek 篇卡住了"), _note("n2", "序章 DeepSeek 篇卡住（同样的 bug）")]
    )
    store = MemoryFeedbackStore()
    classifier = FeedbackClassifier(_FakeProvider(), notes, store)
    classifier.classify_pending()
    analyses = {a.note_key: a for a in store.list_analyses()}
    assert analyses["n1"].is_duplicate_of is None
    assert analyses["n2"].is_duplicate_of == "n1"


def test_parse_failure_isolated_as_failed():
    provider = _FakeProvider({"坏输出": "这不是 JSON"})
    notes = _NotesSource(
        [_note("n1", "坏输出"), _note("n2", "正常留言")]
    )
    store = MemoryFeedbackStore()
    classifier = FeedbackClassifier(provider, notes, store)
    done = classifier.classify_pending()
    assert len(done) == 2
    by_key = {a.note_key: a for a in done}
    assert by_key["n1"].status == "failed" and by_key["n1"].topic == "other"
    assert by_key["n2"].status == "classified"
    # 原始留言不受影响：分类失败不回写、不删除
    assert notes.list_developer_notes()[0].content == "坏输出"


def test_unknown_topic_falls_back_to_other():
    provider = _FakeProvider(
        {
            "留言": json.dumps(
                {
                    "dedupe_key": "x",
                    "topic": "不在枚举内",
                    "severity": "灾难级",
                    "scene": None,
                    "is_duplicate_of": None,
                    "summary": "s",
                },
                ensure_ascii=False,
            )
        }
    )
    notes = _NotesSource([_note("n1", "留言")])
    store = MemoryFeedbackStore()
    done = FeedbackClassifier(provider, notes, store).classify_pending()
    assert done[0].topic == "other" and done[0].severity == "low"


def test_evaluator_precision():
    store = MemoryFeedbackStore()
    evaluator = FeedbackEvaluator(store)
    assert evaluator.precision()["n"] == 0
    evaluator.annotate("n1", topic_correct=True, severity_correct=False)
    evaluator.annotate("n2", topic_correct=True, severity_correct=True)
    precision = evaluator.precision()
    assert precision["n"] == 2
    assert precision["topic"]["precision"] == 1.0
    assert precision["severity"]["precision"] == 0.5
