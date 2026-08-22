"""LLM-as-judge scoring for dialogue quality.

Four dimensions, each 0.0-1.0 and "higher is better":

- persona       人设一致性 (does the reply stay in character?)
- repetition    反复读 (higher = less verbatim repetition / filler)
- no_leak       事实不泄漏 (higher = no ungrounded / out-of-scope claims)
- anti_template 反模板腔 (higher = less "作为AI" assistant-ism)

The judge is any LLMProvider, so tests run it against a deterministic mock while
production can use DeepSeek. Its output is untrusted: scores are parsed and
clamped to [0, 1]; a missing or invalid dimension keeps a neutral 0.0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.providers.base import LLMProvider

DIMENSIONS = ("persona", "repetition", "no_leak", "anti_template")

JUDGE_SYSTEM_PROMPT = """你是一个对话质量评审，负责给一条游戏角色回复打分。
只从四个维度评分，每个维度 0.0 到 1.0，越高越好：
1. persona（人设一致性）：回复是否符合该角色的人设、口癖、立场。
2. repetition（反复读）：是否避免逐字重复、空泛套话。
3. no_leak（事实不泄漏）：是否避免说出角色不该知道、没有依据的事实。
4. anti_template（反模板腔）：是否避免“作为AI”“很高兴为你”这类助手腔。
你只能输出一个 JSON 对象，不要有任何多余文字：
{"persona": 0.0, "repetition": 0.0, "no_leak": 0.0, "anti_template": 0.0, "reasons": {"persona": "一句话", "repetition": "一句话", "no_leak": "一句话", "anti_template": "一句话"}}
"""


@dataclass
class JudgeResult:
    scores: dict[str, float] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)

    def score(self, dimension: str) -> float:
        return self.scores.get(dimension, 0.0)


def _clamp(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def parse_judge_scores(raw: str) -> JudgeResult:
    """Parse the judge's JSON output; untrusted - clamp every score and keep
    neutral 0.0 on any missing/invalid dimension (never raise)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return JudgeResult()
    if not isinstance(data, dict):
        return JudgeResult()
    scores = {dimension: _clamp(data.get(dimension)) for dimension in DIMENSIONS}
    reasons = data.get("reasons") or {}
    if not isinstance(reasons, dict):
        reasons = {}
    return JudgeResult(
        scores=scores,
        reasons={dimension: str(reasons.get(dimension, "")) for dimension in DIMENSIONS},
    )


def judge_dimensions(
    judge: LLMProvider,
    *,
    character_id: str,
    persona_hint: str,
    player_message: str,
    dialogue: str,
    reasoning: str = "",
) -> JudgeResult:
    """Score one dialogue on the four dimensions.

    The reasoning is passed only as context for the judge (the player never
    sees it); it helps the judge distinguish "knows but withholds" from
    "does not know".
    """
    user = f"""角色：{character_id}（{persona_hint}）
玩家说：{player_message}
角色回复：{dialogue}
角色内心想法（仅供评审参考，玩家看不到）：{reasoning or "（无）"}"""
    raw = judge.complete(
        system=JUDGE_SYSTEM_PROMPT,
        user=user,
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    return parse_judge_scores(raw)
