#!/usr/bin/env python3
"""P0-2 试玩版 AI 效果对比 CLI（docs/25）。

双面版本对比：
  判定面  legacy（修订前冻结规则）vs revised（现役 TrialRuntime 规则）
          —— 确定性，100% 可复现，无需 API。
  聊天面  Prompt v1（基线）vs v2（基线+硬规则条款）
          —— 需要 DeepSeek；无 key 自动回落 mock（报告会标注 mock）。

三层评测分开：硬规则（确定性）→ 表达（LLM 评委三维 + 人工抽检 CSV）→
运行表现（延迟/token/调用次数/成本，逐行记录）。

用法：
  python scripts/eval_trial_p02.py --repeats 2 --workers 4 --out rows.jsonl
  python scripts/eval_trial_p02.py --repeats 2 --out rows.jsonl --review sample.csv
  DEEPSEEK_API_KEY=sk-xxx python scripts/eval_trial_p02.py --repeats 2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __file__ and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 与本机后端一致：gitignored backend/.env 提供 DEEPSEEK_API_KEY（不入库，
# 不覆盖真实环境变量；key 绝不进入报告/JSONL）。
from app.config import load_local_env  # noqa: E402

load_local_env(Path(__file__).resolve().parents[1] / ".env")

from app.eval.trial.cases import TRIAL_EVAL_CASES  # noqa: E402
from app.eval.trial.runner import (
    run_chat_row,
    run_deduction_row,
    export_review_csv,
    render_report,
    row_to_dict,
)
from app.eval.trial.scenario import TrialChatResponder
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider


def _provider():
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekProvider()
    print("（未检测到 DEEPSEEK_API_KEY：聊天面与评委都用 mock，报告会标注 mock）")
    return MockProvider()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=2, help="聊天面每用例重复次数（量化噪声）")
    parser.add_argument("--workers", type=int, default=4, help="并发任务数")
    parser.add_argument("--out", default=None, help="逐行 JSONL 输出路径")
    parser.add_argument("--review", default=None, help="人工抽检 CSV 输出路径")
    parser.add_argument("--cases", default=None, help="逗号分隔 case_id 子集（调试用）")
    parser.add_argument("--no-judge", action="store_true", help="跳过评委调用（快速迭代硬规则）")
    args = parser.parse_args()

    provider = _provider()
    judge = provider
    cases = list(TRIAL_EVAL_CASES)
    if args.cases:
        wanted = {item.strip() for item in args.cases.split(",") if item.strip()}
        cases = [case for case in cases if case.case_id in wanted]

    chat_cases = [case for case in cases if case.surface == "chat"]
    deduction_cases = [case for case in cases if case.surface == "deduction"]
    tasks: list[tuple] = []
    for case in chat_cases:
        for version_id in ("v1", "v2"):
            for repeat in range(args.repeats):
                tasks.append(("chat", version_id, case, repeat))
    for case in deduction_cases:
        tasks.append(("deduction", "legacy", case, 0))
        tasks.append(("deduction", "revised", case, 0))
    total = (len(chat_cases) * 2 * args.repeats) + len(deduction_cases) * 2

    _lock = threading.Lock()
    _progress = {"done": 0, "started_at": time.monotonic()}

    def _run(task):
        kind, version_id, case, repeat = task
        if kind == "chat":
            row = run_chat_row(
                TrialChatResponder(provider, version_id), judge, case, repeat,
                skip_judge=args.no_judge,
            )
        else:
            row = run_deduction_row(version_id, case)
        with _lock:
            _progress["done"] += 1
            done = _progress["done"]
            elapsed = time.monotonic() - _progress["started_at"]
        if done % 24 == 0 or done == total:
            print(f"  [progress] {done}/{total} 任务完成（已用 {elapsed / 60:.1f} min）")
        return row

    print(f"== 判定面 {len(deduction_cases)} 例（legacy+revised）+ 聊天面 "
          f"{len(chat_cases)} 例 × 2 版本 × {args.repeats} 重复 = {total} 任务 "
          f"（workers={args.workers}）==")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(_run, tasks):
            rows.append(row)
    rows.sort(key=lambda r: (r.case.surface, r.version, r.case.case_id, r.repeat))

    print()
    print(render_report(rows, provider))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row_to_dict(row), ensure_ascii=False) + "\n")
        print(f"\n逐行 JSONL 已写入 {args.out}")
    if args.review:
        export_review_csv(rows, args.review)
    return 0


if __name__ == "__main__":
    sys.exit(main())
