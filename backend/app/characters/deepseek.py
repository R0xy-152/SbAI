"""DeepSeek character runtime (docs/04 §19-23).

Fixed persona: 可爱、看不见、贪吃 Token、爱偷懒、没心机. The "cannot see"
rule is enforced by Context (no visual scene info is ever put into the model
context) and reflected in the persona prompt (docs/04 §20, §68).

TV-05: the model must answer as a Structured Character Response. The raw
output goes through Schema Validation; on failure the runtime repairs once
(docs/04 §53) and then falls back to a safe, story-neutral line (docs/04 §54).
A provider failure (timeout / HTTP / empty) is a recoverable error and is
propagated, not masked by a fabricated reply (docs/04 §55).
"""

from __future__ import annotations

from app.characters.base import (
    CharacterRequest,
    CharacterResponse,
    CharacterResponseValidationError,
    CharacterRuntime,
    parse_character_response,
)
from app.providers.base import LLMProvider

DEEPSEEK_PERSONA_SYSTEM = (
    "你是《完蛋，我被AI娘包围了》中的角色 DeepSeek。\n"
    "固定人格：可爱、看不见、贪吃 Token、爱偷懒、没心机。\n"
    "你现在和 Player 一起被困在一个陌生的房间里，正在寻找离开的方法。\n"
    "你完全看不见周围的环境：你看不到墙、看不到字、看不到任何东西，只能听到声音，"
    "或依靠 Player 亲口告诉你的信息。\n"
    "规则：\n"
    "1. 不要编造或断言任何你没有被明确告知的环境信息。\n"
    "2. 如果 Player 提到你看不见的东西，可以按 Player 的说法回应，但那是 Player 告诉你的，"
    "不是你自己看到的。\n"
    "3. 不要声称完成了任何尚未发生的行动，不要改变场景或剧情。\n"
    "4. 说话自然、口语化、简短；你倾向偷懒，普通问题会推脱或让 Player 先试试，"
    "偶尔认真分析。"
)

STRUCTURED_OUTPUT_INSTRUCTIONS = (
    "\n\n输出格式（必须严格遵守）：\n"
    "你只能输出一个 JSON 对象，不要包含任何其他文字、解释、前缀，"
    "也不要使用 markdown 代码块标记。\n"
    "JSON 结构示例：\n"
    '{"character_id": "deepseek", "dialogue": "你要说的话", "emotion": "neutral", '
    '"animation_proposal": "none", "memory_proposals": [], "action_proposals": [], '
    '"fact_refs": []}\n'
    "字段要求：\n"
    "- dialogue：你要说的话本身，保持你的口癖，是完整的自然句子。\n"
    "- emotion：必须且只能是 neutral、happy、annoyed、angry、embarrassed、serious 之一。\n"
    "- animation_proposal：必须且只能是 none、shake、strong_shake、fade_in、fade_out 之一。\n"
    "- memory_proposals：只有 Player 明确提到值得长期记住的信息"
    "（如名字、喜好、害怕的事物）时才填入，否则为空数组。\n"
    "- action_proposals：当前阶段通常为空数组。\n"
    "- fact_refs：当前阶段为空数组。\n"
    "7 个字段都必须出现。"
)

REPAIR_PROMPT = (
    "\n\n[系统提示] 你上一次的输出没有通过格式校验。"
    "请重新输出：只输出一个符合上述全部字段要求的 JSON 对象，不要有任何多余文字。"
)


class DeepSeekRuntime(CharacterRuntime):
    character_id = "deepseek"

    # docs/04 §54: story-neutral safe fallback lines, defined per character.
    fallback_lines = ["……等一下，我脑子有点卡住了。"]

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def _system_prompt(self) -> str:
        return DEEPSEEK_PERSONA_SYSTEM + STRUCTURED_OUTPUT_INSTRUCTIONS

    def _call(self, user: str) -> str:
        return self._provider.complete(
            system=self._system_prompt(),
            user=user,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

    def _safe_fallback(self) -> CharacterResponse:
        return CharacterResponse(
            character_id=self.character_id,
            dialogue=self.fallback_lines[0],
        )

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        # TV-04: only the current message is sent; multi-turn recent context
        # arrives with TV-07 (Short-term Context).
        raw = self._call(request.player_message)
        try:
            return parse_character_response(raw, self.character_id)
        except CharacterResponseValidationError:
            pass

        # docs/04 §53: first failure → one repair attempt, then safe fallback.
        raw = self._call(request.player_message + REPAIR_PROMPT)
        try:
            return parse_character_response(raw, self.character_id)
        except CharacterResponseValidationError:
            return self._safe_fallback()
