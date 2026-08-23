"""Character self-reflection (docs/04 §47.1 的延伸：回话后的元认知).

与回话前的 reasoning（「为什么这样回复」）不同，reflection 是回话之后对
自己刚才那句话的简短反思——哪里说得好、哪里要改进、有没有越界。它沉淀进
角色的内部状态并在下一轮反馈，让角色的「思考」看起来会延续、会自我修正，
而不是每轮重置。反思只进模型上下文与内部状态，绝不进前端或 History
（与 reasoning 一致，docs/04 §47.1）。

可选的：每轮多一次 LLM 调用（token 成本上升），默认关闭。
"""

from __future__ import annotations

from app.providers.base import LLMProvider, ProviderError

REFLECTION_INSTRUCTIONS = (
    "回话结束后，请以第一人称简短反思你刚才那句话：有没有哪里说得不妥、"
    "有没有暴露你不该知道的事、下一次该怎么改进。只输出 1-2 句反思，"
    "不要解释，不要 JSON，不要任何多余文字。"
)


class Reflector:
    """Optional per-turn self-reflection (off by default).

    Fails open: any provider error yields an empty reflection, so a flaky
    reflection call never blocks or degrades the turn (the reflection is an
    internal hint, not a presented reply).
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def reflect(
        self,
        *,
        character_id: str,
        persona: str,
        dialogue: str,
        reasoning: str,
        player_message: str,
    ) -> str:
        """One bounded reflection for the reply just spoken. Returns "" on
        failure or empty output."""
        user = (
            f"玩家刚才说：{player_message}\n"
            f"你刚才回复：{dialogue}\n"
            f"你回复时的想法：{reasoning or '（无）'}"
        )
        try:
            raw = self._provider.complete(
                system=persona + "\n\n" + REFLECTION_INSTRUCTIONS,
                user=user,
                max_tokens=256,
            )
        except ProviderError:
            return ""
        if not isinstance(raw, str):
            return ""
        return raw.strip()
