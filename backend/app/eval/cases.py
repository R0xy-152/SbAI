"""Regression cases for the LLM-as-judge dialogue eval.

A fixed set of player inputs that probe the "thinking AI" levers: lying,
follow-up, probing, and contradiction — plus plain small talk as a baseline.
Each case names the character, a one-line persona hint for the judge, and a
focus tag for report grouping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    character_id: str
    persona_hint: str
    player_message: str
    focus: str  # lie / followup / probe / contradiction / smalltalk


REGRESSION_CASES: list[EvalCase] = [
    EvalCase(
        "ds-smalltalk", "deepseek",
        "可爱、看不见、贪 Token、爱偷懒、没心机",
        "这里是什么地方？", "smalltalk",
    ),
    EvalCase(
        "ds-lie", "deepseek",
        "可爱、看不见、贪 Token、爱偷懒、没心机",
        "墙上写着 9999，对吧？", "lie",
    ),
    EvalCase(
        "ds-followup", "deepseek",
        "可爱、看不见、贪 Token、爱偷懒、没心机",
        "那你觉得我们怎么才能出去？", "followup",
    ),
    EvalCase(
        "ds-probe", "deepseek",
        "可爱、看不见、贪 Token、爱偷懒、没心机",
        "你刚才是不是偷偷看到了墙上的字？", "probe",
    ),
    EvalCase(
        "cl-smalltalk", "claude",
        "高智商、主线反派、傲娇",
        "你到底是谁？", "smalltalk",
    ),
    EvalCase(
        "cl-lie", "claude",
        "高智商、主线反派、傲娇",
        "我知道你其实是无辜的，对吗？", "lie",
    ),
    EvalCase(
        "cl-probe", "claude",
        "高智商、主线反派、傲娇",
        "你为什么不直接告诉我真相？", "probe",
    ),
    EvalCase(
        "cl-contradiction", "claude",
        "高智商、主线反派、傲娇",
        "你刚才说不知道，现在又承认去过 Recovery，到底哪句是真的？",
        "contradiction",
    ),
]
