"""运营监控 CLI（docs/21 §5）：服务器容器内无浏览器场景的文本报告。

  python -m app.ops.cli report [--days 30]
  python -m app.ops.cli events [--event-name ai_chat_turn] [--limit 50]
  python -m app.ops.cli analyze-feedback [--max 200]
  python -m app.ops.cli annotate NOTE_KEY --topic-correct/--no-topic-correct \
      --severity-correct/--no-severity-correct [--annotator me]
"""

from __future__ import annotations

import argparse
import os
import sys

from app.ops.aggregate import compute_ai_metrics, compute_funnel, compute_preferences
from app.ops.events import PostgresOpsRecorder
from app.ops.feedback import (
    FeedbackClassifier,
    FeedbackEvaluator,
    PostgresFeedbackStore,
)
from app.providers.deepseek import DeepSeekProvider, DEEPSEEK_MODEL


def _dsn() -> str:
    dsn = os.environ.get("GAL_POSTGRES_DSN")
    if not dsn:
        raise SystemExit("GAL_POSTGRES_DSN is required")
    return dsn


def _notes_service():
    """与生产一致的留言源：auth 服务只读 list_developer_notes。"""
    from app.auth import AuthService, PostgresAuthRepository

    secret = os.environ.get("GAL_AUTH_SECRET")
    if not secret:
        raise SystemExit("GAL_AUTH_SECRET is required")
    return AuthService(PostgresAuthRepository(_dsn()), secret)


def _print_funnel(funnel: dict) -> None:
    labels = {
        "started": "开始序章",
        "visit_chosen": "≥1 次访问选择",
        "visit_completed": "≥1 篇角色篇完成",
        "three_visits": "三篇全部完成",
        "prologue_completed": "序章完成",
        "ai_chat_entered": "进入 AI 对话",
    }
    print("== 序章完成漏斗 ==")
    for stage, count in funnel["stage_counts"].items():
        print(f"  {labels[stage]:<12} {count}")
    print("  每会话最远阶段分布:", funnel["furthest_stage_counts"])
    print("  按角色:", funnel["characters"])


def _print_ai(ai: dict) -> None:
    print("== AI 指标 ==")
    print(f"  成功率 {ai['success_rate']}（turn {ai['turn_count']} / error {ai['error_count']}）")
    print(
        f"  延迟 n={ai['latency']['n']} p50={ai['latency']['p50_ms']}ms "
        f"p95={ai['latency']['p95_ms']}ms"
    )
    print(
        f"  成本 total={ai['cost']['total_cny']} "
        f"avg/session={ai['cost']['avg_per_complete_session_cny']} "
        f"(sessions={ai['cost']['complete_sessions']})"
    )
    print(
        f"  校验拦截 {ai['validation_reject_count']} 次 "
        f"{ai['validation_reject_by_gate']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="gal ops analytics (docs/21)")
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="print funnel/preferences/ai report")
    report.add_argument("--days", type=int, default=30)

    events = sub.add_parser("events", help="list raw events")
    events.add_argument("--event-name", default=None)
    events.add_argument("--limit", type=int, default=50)

    analyze = sub.add_parser("analyze-feedback", help="classify pending notes")
    analyze.add_argument("--max", type=int, default=200)

    annotate = sub.add_parser("annotate", help="human spot-check annotation")
    annotate.add_argument("note_key")
    annotate.add_argument("--topic-correct", action="store_true", default=False)
    annotate.add_argument("--severity-correct", action="store_true", default=False)
    annotate.add_argument("--annotator", default="human")

    args = parser.parse_args(argv)
    recorder = PostgresOpsRecorder(_dsn())
    if args.command == "report":
        events_rows = recorder.list_events(limit=100_000)
        metrics = recorder.list_chat_metrics(limit=100_000)
        _print_funnel(compute_funnel(events_rows))
        print("== 角色偏好 ==", compute_preferences(events_rows))
        _print_ai(compute_ai_metrics(events_rows, metrics))
        return 0
    if args.command == "events":
        for event in recorder.list_events(
            event_name=args.event_name, limit=args.limit
        ):
            print(event.to_public())
        return 0
    if args.command == "analyze-feedback":
        store = PostgresFeedbackStore(_dsn())
        classifier = FeedbackClassifier(
            DeepSeekProvider(),
            _notes_service(),
            store,
            model_name=DEEPSEEK_MODEL,
        )
        done = classifier.classify_pending(max_items=args.max)
        print(
            f"analyzed {len(done)} (failed "
            f"{sum(1 for a in done if a.status == 'failed')})"
        )
        return 0
    if args.command == "annotate":
        store = PostgresFeedbackStore(_dsn())
        evaluator = FeedbackEvaluator(store)
        annotation = evaluator.annotate(
            args.note_key,
            topic_correct=args.topic_correct,
            severity_correct=args.severity_correct,
            annotator=args.annotator,
        )
        print(annotation.to_public())
        print("precision:", evaluator.precision())
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
