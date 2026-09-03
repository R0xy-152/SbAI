"""玩家反馈分类与人工抽检（docs/21 §6）。

诚实口径：这是 LLM 辅助的分类器，不是自主 Agent——分类结果一律保留原始
留言（developer_notes）与模型原始输出（raw_json）作证据，精度由人工抽检
（feedback_annotations）度量，不包装成端到端智能体。
"""

from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.auth import DeveloperNote
from app.providers.base import LLMProvider, ProviderError

logger = logging.getLogger(__name__)

# docs/21 §6：分类枚举。模型输出落在枚举外时回落默认值，不让脏数据进库。
TOPICS = frozenset(
    {
        "bug", "experience", "story_content", "character",
        "difficulty", "praise", "complaint", "suggestion", "other",
    }
)
SEVERITIES = frozenset({"low", "medium", "high"})

_CLASSIFY_SYSTEM = (
    "你是游戏《完蛋，我被AI娘包围了》的玩家反馈分类器。"
    "针对一条玩家留言输出一个 JSON 对象，字段如下："
    '{"dedupe_key": "主题+关键实体的归一化短串，同主题同实体的留言应产出相同串",'
    ' "topic": "bug、experience、story_content、character、difficulty、'
    'praise、complaint、suggestion、other 之一",'
    ' "severity": "low、medium、high 之一（对玩家体验的影响程度）",'
    ' "scene": "留言指向的游戏场景，如 prologue_visit_deepseek、'
    'ai_chat_claude、general",'
    ' "is_duplicate_of": "与已知留言实质重复时给出重复目标的一句话摘要，'
    '否则 null",'
    ' "summary": "一句话概括这条留言"}。'
    "只输出 JSON 对象，不要任何多余文字。"
)


@dataclass(frozen=True)
class FeedbackAnalysis:
    """一条留言的分类结果（docs/21 §3）。note_key = developer_notes.session_id。"""

    note_key: str
    dedupe_key: str | None
    topic: str
    severity: str
    scene: str | None = None
    is_duplicate_of: str | None = None
    summary: str | None = None
    model: str | None = None
    status: str = "classified"
    raw_json: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_public(self) -> dict:
        return {
            "note_key": self.note_key,
            "dedupe_key": self.dedupe_key,
            "topic": self.topic,
            "severity": self.severity,
            "scene": self.scene,
            "is_duplicate_of": self.is_duplicate_of,
            "summary": self.summary,
            "model": self.model,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class FeedbackAnnotation:
    """人工抽检标注（docs/21 §6）：逐字段判断分类是否正确。"""

    note_key: str
    topic_correct: bool
    severity_correct: bool
    annotator: str = "human"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_public(self) -> dict:
        return {
            "note_key": self.note_key,
            "topic_correct": self.topic_correct,
            "severity_correct": self.severity_correct,
            "annotator": self.annotator,
            "created_at": self.created_at.isoformat(),
        }


class FeedbackStore(ABC):
    """反馈分析/标注的读写接口（docs/21 §3）。"""

    @abstractmethod
    def upsert_analysis(self, analysis: FeedbackAnalysis) -> None: ...

    @abstractmethod
    def list_analyses(self) -> list[FeedbackAnalysis]: ...

    @abstractmethod
    def add_annotation(self, annotation: FeedbackAnnotation) -> None: ...

    @abstractmethod
    def list_annotations(self) -> list[FeedbackAnnotation]: ...


class MemoryFeedbackStore(FeedbackStore):
    """Thread-safe 内存实现；本地开发/测试用。"""

    def __init__(self) -> None:
        self._analyses: list[FeedbackAnalysis] = []
        self._annotations: list[FeedbackAnnotation] = []
        self._lock = threading.Lock()

    def upsert_analysis(self, analysis: FeedbackAnalysis) -> None:
        with self._lock:
            if any(a.note_key == analysis.note_key for a in self._analyses):
                return
            self._analyses.append(analysis)

    def list_analyses(self) -> list[FeedbackAnalysis]:
        with self._lock:
            return sorted(self._analyses, key=lambda a: a.created_at)

    def add_annotation(self, annotation: FeedbackAnnotation) -> None:
        with self._lock:
            self._annotations.append(annotation)

    def list_annotations(self) -> list[FeedbackAnnotation]:
        with self._lock:
            return sorted(self._annotations, key=lambda a: a.created_at)


class PostgresFeedbackStore(FeedbackStore):
    """生产实现：与 auth 仓库同库同 DSN（表结构见 OPS_SCHEMA_SQL）。"""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._initialized = False
        self._lock = threading.Lock()

    def _ensure_schema(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            import psycopg

            from app.ops.events import OPS_SCHEMA_SQL

            with psycopg.connect(self._dsn) as conn:
                conn.execute(OPS_SCHEMA_SQL)
            self._initialized = True

    def _conn(self):
        import psycopg

        self._ensure_schema()
        return psycopg.connect(self._dsn)

    def upsert_analysis(self, analysis: FeedbackAnalysis) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO feedback_analysis"
                " (note_key, dedupe_key, topic, severity, scene, is_duplicate_of,"
                "  summary, model, status, raw_json)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (note_key) DO NOTHING",
                (
                    analysis.note_key,
                    analysis.dedupe_key,
                    analysis.topic,
                    analysis.severity,
                    analysis.scene,
                    analysis.is_duplicate_of,
                    analysis.summary,
                    analysis.model,
                    analysis.status,
                    analysis.raw_json,
                ),
            )

    @staticmethod
    def _analysis(row) -> FeedbackAnalysis:
        return FeedbackAnalysis(
            note_key=row[1],
            dedupe_key=row[2],
            topic=row[3],
            severity=row[4],
            scene=row[5],
            is_duplicate_of=row[6],
            summary=row[7],
            model=row[8],
            status=row[9],
            raw_json=row[10],
            created_at=row[11],
        )

    def list_analyses(self) -> list[FeedbackAnalysis]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, note_key, dedupe_key, topic, severity, scene,"
                " is_duplicate_of, summary, model, status, raw_json, created_at"
                " FROM feedback_analysis ORDER BY created_at"
            ).fetchall()
        return [self._analysis(row) for row in rows]

    def add_annotation(self, annotation: FeedbackAnnotation) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO feedback_annotations"
                " (note_key, topic_correct, severity_correct, annotator)"
                " VALUES (%s, %s, %s, %s)",
                (
                    annotation.note_key,
                    annotation.topic_correct,
                    annotation.severity_correct,
                    annotation.annotator,
                ),
            )

    @staticmethod
    def _annotation(row) -> FeedbackAnnotation:
        return FeedbackAnnotation(
            note_key=row[1],
            topic_correct=row[2],
            severity_correct=row[3],
            annotator=row[4],
            created_at=row[5],
        )

    def list_annotations(self) -> list[FeedbackAnnotation]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, note_key, topic_correct, severity_correct, annotator,"
                " created_at FROM feedback_annotations ORDER BY created_at"
            ).fetchall()
        return [self._annotation(row) for row in rows]


class FeedbackClassifier:
    """把 developer_notes 逐条分类并落库（docs/21 §6）。

    去重确定性收敛：同 dedupe_key 的后续留言 is_duplicate_of 指向最早一条
    （按分析入库顺序），不依赖模型给出的重复目标文本。
    """

    def __init__(
        self,
        provider: LLMProvider,
        notes_source,  # AuthService：list_developer_notes()
        store: FeedbackStore,
        model_name: str | None = None,
    ) -> None:
        self._provider = provider
        self._notes = notes_source
        self._store = store
        self._model_name = model_name

    def classify_pending(self, max_items: int = 200) -> list[FeedbackAnalysis]:
        notes = self._notes.list_developer_notes()
        existing = {a.note_key for a in self._store.list_analyses()}
        done: list[FeedbackAnalysis] = []
        for note in notes:
            if note.session_id in existing or len(done) >= max_items:
                continue
            analysis = self._classify_one(note)
            self._store.upsert_analysis(analysis)
            existing.add(note.session_id)
            done.append(analysis)
        return done

    def _classify_one(self, note: DeveloperNote) -> FeedbackAnalysis:
        raw = ""
        try:
            raw = self._provider.complete(
                system=_CLASSIFY_SYSTEM,
                user=self._prompt(note),
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            data = json.loads(raw)
            topic = data.get("topic") if data.get("topic") in TOPICS else "other"
            severity = (
                data.get("severity")
                if data.get("severity") in SEVERITIES
                else "low"
            )
            dedupe_key = str(data.get("dedupe_key") or "").strip() or None
            scene = data.get("scene")
            summary = data.get("summary")
            return FeedbackAnalysis(
                note_key=note.session_id,
                dedupe_key=dedupe_key,
                topic=topic,
                severity=severity,
                scene=str(scene).strip() if scene else None,
                is_duplicate_of=self._resolve_duplicate(dedupe_key, note.session_id),
                summary=str(summary).strip() if summary else None,
                model=self._model_name,
                status="classified",
                raw_json=raw,
            )
        except (ValueError, TypeError, ProviderError) as exc:
            logger.warning(
                "feedback classification failed for note %s: %s",
                note.session_id,
                exc,
            )
            return FeedbackAnalysis(
                note_key=note.session_id,
                dedupe_key=None,
                topic="other",
                severity="low",
                model=self._model_name,
                status="failed",
                raw_json=raw or None,
            )

    def _resolve_duplicate(
        self, dedupe_key: str | None, note_key: str
    ) -> str | None:
        if not dedupe_key:
            return None
        for analysis in self._store.list_analyses():
            if analysis.dedupe_key == dedupe_key and analysis.note_key != note_key:
                return analysis.note_key
        return None

    @staticmethod
    def _prompt(note: DeveloperNote) -> str:
        return f"留言角色：{note.character_id}\n留言内容：\n{note.content}"


class FeedbackEvaluator:
    """人工抽检与 Precision 计算（docs/21 §6）。

    抽检集不足 50 条时按实际量全量标注，精度输出如实携带 n。
    """

    def __init__(self, store: FeedbackStore) -> None:
        self._store = store

    def annotate(
        self,
        note_key: str,
        *,
        topic_correct: bool,
        severity_correct: bool,
        annotator: str = "human",
    ) -> FeedbackAnnotation:
        annotation = FeedbackAnnotation(
            note_key=note_key,
            topic_correct=topic_correct,
            severity_correct=severity_correct,
            annotator=annotator,
        )
        self._store.add_annotation(annotation)
        return annotation

    def precision(self) -> dict:
        annotations = self._store.list_annotations()
        n = len(annotations)
        if n == 0:
            return {
                "n": 0,
                "topic": {"correct": 0, "total": 0, "precision": None},
                "severity": {"correct": 0, "total": 0, "precision": None},
            }
        topic_correct = sum(1 for a in annotations if a.topic_correct)
        severity_correct = sum(1 for a in annotations if a.severity_correct)
        return {
            "n": n,
            "topic": {
                "correct": topic_correct,
                "total": n,
                "precision": round(topic_correct / n, 4),
            },
            "severity": {
                "correct": severity_correct,
                "total": n,
                "precision": round(severity_correct / n, 4),
            },
        }
