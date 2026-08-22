"""Semantic consistency gate (defense-in-depth on top of validate_response).

The deterministic validate_response enforces hard boundaries (character id,
fact refs, DeepSeek's visual blindness, allowed actions). This module adds an
OPTIONAL semantic layer: an LLM judge that checks whether a reply stays within
the information the character is authorized to know — no leak, no fabrication,
no contradiction. It is defense-in-depth, not a substitute for the
deterministic gate, and it is OFF by default (each check is an extra LLM call).

The checker is untrusted: its verdict is parsed defensively and any unparseable
output fails OPEN (pass) so a flaky judge never blocks the game.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.providers.base import LLMProvider


@dataclass(frozen=True)
class ConsistencyVerdict:
    verdict: str  # "pass" | "reject"
    reason: str = ""


CONSISTENCY_SYSTEM_PROMPT = """你是剧情信息边界校验器。你只判断一件事：这条角色回复是否只基于"有权知道"的内容，有没有越界。三类越界：
1. leak（泄漏）：说出了角色不该知道、没有被授权知道的信息。
2. fabrication（编造）：断言了"有权知道"之外、也没有依据的事实。
3. contradiction（矛盾）：与"有权知道"的内容相矛盾。
你只能输出一个 JSON 对象，不要有任何多余文字：
{"verdict": "pass", "reason": "一句话说明"}
其中 verdict 只能是 "pass"（通过）或 "reject"（越界，需拦截）。"""


def parse_consistency_verdict(raw: str) -> ConsistencyVerdict:
    """Parse the checker's JSON; untrusted — fail OPEN (pass) on anything
    unparseable so a flaky judge never blocks the game."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ConsistencyVerdict("pass", "unparseable verdict")
    if not isinstance(data, dict):
        return ConsistencyVerdict("pass", "verdict is not an object")
    verdict = data.get("verdict")
    reason = data.get("reason")
    if verdict == "reject":
        return ConsistencyVerdict("reject", str(reason) if isinstance(reason, str) else "")
    return ConsistencyVerdict("pass", str(reason) if isinstance(reason, str) else "")


class SemanticConsistencyChecker:
    """Optional semantic gate (docs/04 §51 defense-in-depth)."""

    def __init__(self, provider: LLMProvider, *, enabled: bool = True) -> None:
        self._provider = provider
        self._enabled = enabled

    def check(
        self,
        *,
        character_id: str,
        authorized_context: str,
        player_message: str,
        dialogue: str,
        reasoning: str = "",
    ) -> ConsistencyVerdict:
        """Judge whether the reply stays within the character's authorized
        knowledge. A rejected verdict is turned into a safe fallback by the
        caller (Validate Before Present, docs/04 §51)."""
        if not self._enabled:
            return ConsistencyVerdict("pass", "checker disabled")
        user = (
            f"角色：{character_id}\n"
            f"该角色此刻有权知道的内容（除此之外一概不知）：\n"
            f"{authorized_context or '（无）'}\n"
            f"玩家说：{player_message}\n"
            f"角色回复：{dialogue}\n"
            f"角色内心想法（仅供校验参考）：{reasoning or '（无）'}"
        )
        raw = self._provider.complete(
            system=CONSISTENCY_SYSTEM_PROMPT,
            user=user,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        return parse_consistency_verdict(raw)
