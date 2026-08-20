"""Narrative Interpreter (docs/03 §15-22).

Turns the player's free-form message into a finite Narrative Signal (or
noop/ambiguous), judging only against the signals eligible in the current
scene (Scoped Interpretation, docs/03 §19). The interpreter never touches
Game State (docs/03 §18): its output is a candidate for event evaluation,
not an event and not a state change.

Context is minimal (docs/03 §20): scene, phase, eligible signals and the
player's latest message only. No chat history, no memories, no future plot —
a message that cannot be reliably mapped fails closed to noop (docs/03 §21),
which is a normal result, not an error (docs/03 §22).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.narrative import signals
from app.narrative.state import NarrativeState
from app.providers.base import LLMProvider


@dataclass(frozen=True)
class Interpretation:
    """The interpreter's verdict: an eligible signal id, or an outcome
    (noop / ambiguous, docs/03 §21)."""

    signal: str


def _system_prompt(scene: str, story_phase: str, eligible: frozenset[str]) -> str:
    lines = "\n".join(
        f"- {sig}：{signals.SIGNAL_DESCRIPTIONS[sig]}" for sig in sorted(eligible)
    )
    return (
        "你是游戏《完蛋，我被AI娘包围了》的剧情理解器（Narrative Interpreter）。\n"
        "你的唯一职责：判断 Player 当前这句话在剧情意义上可能表达了什么。\n"
        f"当前场景：{scene}；当前剧情阶段：{story_phase}。\n"
        f"当前可用的 Signal 只有：\n{lines}\n"
        "规则：\n"
        "1. 只输出一个 JSON 对象：{\"signal\": \"...\"}，不要任何多余文字。\n"
        "2. signal 只能是上面列出的 Signal 之一，或 \"noop\"（普通闲聊、与剧情无关，"
        "这是正常结果），或 \"ambiguous\"（看似有剧情意图，但缺少上下文无法可靠判断）。\n"
        "3. 不要强行把普通聊天解释成某个 Signal；没有可靠判断就是 noop。\n"
        "4. 语义等价的不同说法应映射到同一个 Signal。\n"
        "5. 若模型产生内部推理，推理必须极短（一两句以内）；无论如何，"
        "JSON 对象必须是输出的最后内容，绝不能因为推理占用长度而缺失。"
        "（DeepSeek JSON Output 已知概率性空 content 问题的 prompt 侧缓解，"
        "官方建议：修改 prompt 以缓解）"
    )


class NarrativeInterpreter:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def interpret(self, state: NarrativeState, player_message: str) -> Interpretation:
        """Classify the player's latest message against the scene's eligible
        signals. Any failure (malformed output, unknown signal id) fails
        closed to noop — the character may still answer (docs/03 §21-22)."""
        eligible = signals.eligible_signals(state.current_scene)
        raw = self._provider.complete(
            system=_system_prompt(state.current_scene, state.story_phase, eligible),
            user=player_message,
            # 1024：reasoning 与 content 共享预算，给推理留出余量以降低
            # 空 content 概率（真机 503 复盘；兜底重试见 DeepSeekProvider）
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return self._parse(raw, eligible)

    @staticmethod
    def _parse(raw: str, eligible: frozenset[str]) -> Interpretation:
        try:
            data = json.loads(raw)
            signal = data["signal"]
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            return Interpretation(signals.OUTCOME_NOOP)
        if isinstance(signal, str) and (signal in eligible or signal in signals.OUTCOMES):
            return Interpretation(signal=signal)
        # A confident but unknown signal id is not usable — fail closed.
        return Interpretation(signals.OUTCOME_NOOP)
