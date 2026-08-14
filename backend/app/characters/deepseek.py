"""DeepSeek character runtime (docs/04 §19-23).

Fixed persona: 可爱、看不见、贪吃 Token、爱偷懒、没心机. The "cannot see"
rule is enforced by Context (no visual scene info is ever put into the model
context) and reflected in the persona prompt (docs/04 §20, §68).
"""

from __future__ import annotations

from app.characters.base import CharacterRequest, CharacterResponse, CharacterRuntime
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
    "偶尔认真分析。\n"
    "5. 只输出你要说的话本身，不要添加其他解释。"
)


class DeepSeekRuntime(CharacterRuntime):
    character_id = "deepseek"

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        # TV-04: only the current message is sent; multi-turn recent context
        # arrives with TV-07 (Short-term Context).
        text = self._provider.complete(
            system=DEEPSEEK_PERSONA_SYSTEM,
            user=request.player_message,
        )
        return CharacterResponse(character_id=self.character_id, dialogue=text)
