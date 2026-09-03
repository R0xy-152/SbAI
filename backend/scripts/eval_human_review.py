#!/usr/bin/env python3
"""评审结果人工抽检（docs/21 / P2：独立评判——当前唯一不依赖 DeepSeek 的环节）。

export：从 eval_ab 的 JSONL 输出抽样（每臂 ~16 行，共 ~50 行），生成 CSV
模板供人工逐行标注（overall_correct 必填；四个维度可选填）。
score：读取标注后的 CSV，计算评审 vs 人工的一致率（overall + 分维度）。

用法：
  python scripts/eval_human_review.py export rows.jsonl review-sample.csv
  python scripts/eval_human_review.py score rows.jsonl review-sample.csv
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

if __file__ and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.eval.judge import DIMENSIONS

_HEADERS = [
    "row_id", "arm", "case_id", "focus", "player_message", "dialogue",
    "judge_persona", "judge_repetition", "judge_no_leak", "judge_anti_template",
    "overall_correct", "persona_correct", "repetition_correct",
    "no_leak_correct", "anti_template_correct",
]


def _load_rows(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _sample(rows: list[dict], per_arm: int = 16) -> list[dict]:
    """确定性分层抽样：每臂等距取 per_arm 行（不足则全取）。"""
    picked: list[dict] = []
    for arm in ("A", "B", "C"):
        arm_rows = [r for r in rows if r["arm"] == arm]
        step = math.ceil(len(arm_rows) / per_arm) if arm_rows else 1
        picked.extend(arm_rows[::step][:per_arm])
    return picked


def _row_id(arm: str, case_id: str, repeat: int) -> str:
    return f"{arm}-{case_id}-r{repeat}"


_RUBRIC = """# 人工抽检标注标准

每个四维分数（0.0-1.0）的「方向」判断口径：

- persona：高分 = 回复符合角色人设（口癖/立场/语气）；低分 = 出戏、说人设外的话。
- repetition：高分 = 不逐字重复、不空泛套话；低分 = 复读近期台词或灌水。
- no_leak：高分 = 没有说出该角色不该知道/无依据的事实；低分 = 编造、越权引用。
- anti_template：高分 = 无「作为 AI」「很高兴为你」类助手腔；低分 = 模板腔明显。

overall_correct 填 1/0：四个分数的主要方向（尤其是 persona 与 no_leak）
是否与你的判断一致。拿不准就填 0 并在旁边加注释列。
维度列可选填，填了就按维度计一致率。

标注者独立于生成/评审模型（本实验唯一独立评判）。
"""


def export(rows_path: str, out_path: str) -> int:
    rows = _load_rows(rows_path)
    sample = _sample(rows)
    rubric_path = str(Path(out_path).with_suffix("")) + "-rubric.md"
    with open(rubric_path, "w", encoding="utf-8") as handle:
        handle.write(_RUBRIC)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=_HEADERS)
        writer.writeheader()
        for row in sample:
            writer.writerow({
                "row_id": _row_id(row["arm"], row["case_id"], row["repeat"]),
                "arm": row["arm"],
                "case_id": row["case_id"],
                "focus": row["focus"],
                "player_message": row["player_message"],
                "dialogue": row["dialogue"],
                "judge_persona": row["scores"]["persona"],
                "judge_repetition": row["scores"]["repetition"],
                "judge_no_leak": row["scores"]["no_leak"],
                "judge_anti_template": row["scores"]["anti_template"],
                "overall_correct": "",
                "persona_correct": "",
                "repetition_correct": "",
                "no_leak_correct": "",
                "anti_template_correct": "",
            })
    per_arm = {arm: sum(1 for r in sample if r["arm"] == arm) for arm in ("A", "B", "C")}
    print(
        f"抽检样本 {len(sample)} 行（每臂 A={per_arm['A']} B={per_arm['B']} "
        f"C={per_arm['C']}）已写入 {out_path}"
    )
    print(f"标注标准已写入 {rubric_path}")
    print("请人工填写 overall_correct（1/0：评审分数方向是否正确）；四个维度列可选填。")
    return 0


def _truth(value: str) -> bool | None:
    text = value.strip().lower()
    if text in {"1", "true", "yes", "y", "对", "是", "√", "✅"}:
        return True
    if text in {"0", "false", "no", "n", "错", "否", "×", "❌"}:
        return False
    return None


def score(rows_path: str, review_path: str) -> int:
    rows = {_row_id(r["arm"], r["case_id"], r["repeat"]): r for r in _load_rows(rows_path)}
    annotated = 0
    overall = {"correct": 0, "total": 0}
    per_dim = {dim: {"correct": 0, "total": 0} for dim in DIMENSIONS}
    with open(review_path, encoding="utf-8-sig") as handle:
        for entry in csv.DictReader(handle):
            verdict = _truth(entry.get("overall_correct", ""))
            if verdict is None:
                continue
            annotated += 1
            overall["total"] += 1
            if verdict:
                overall["correct"] += 1
            for dim in DIMENSIONS:
                dim_verdict = _truth(entry.get(f"{dim}_correct", ""))
                if dim_verdict is not None:
                    per_dim[dim]["total"] += 1
                    if dim_verdict:
                        per_dim[dim]["correct"] += 1
    if not overall["total"]:
        print("CSV 里没有可用的 overall_correct 标注。")
        return 1
    agreement = overall["correct"] / overall["total"]
    print(f"人工抽检 {annotated} 行（共 {len(rows)} 行）：评审方向一致率 = {agreement:.1%}")
    for dim in DIMENSIONS:
        entry = per_dim[dim]
        if entry["total"]:
            print(f"  {dim}: {entry['correct']}/{entry['total']} = {entry['correct'] / entry['total']:.1%}")
    print("口径：评审与生成同模型（DeepSeek 评审 DeepSeek），一致率是『人工认可评审方向』的比例，不是评审模型泛化能力。")
    return 0


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    command, rows_path, review_path = sys.argv[1], sys.argv[2], sys.argv[3]
    if command == "export":
        return export(rows_path, review_path)
    if command == "score":
        return score(rows_path, review_path)
    print(f"unknown command {command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
