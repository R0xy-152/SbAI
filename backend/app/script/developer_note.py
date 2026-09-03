"""序章「对开发者的话」静态文案（docs/20）。

在序章自由聊天开始前，由被选中的角色按各自性格问一句固定语义问句
「在此之前，你有什么想对开发者说的吗」。文案是预置的确定性文本，
不走 LLM —— 触发即展示，零 Provider 延迟（docs/20 §1）。

剧情内容 / 角色配置与 Runtime 分离：这里只放文案，不放状态或执行逻辑。
"""

from __future__ import annotations

# 固定语义：「在此之前，你有什么想对开发者说的吗？」—— 按角色性格预置的措辞。
DEVELOPER_NOTE_QUESTIONS: dict[str, str] = {
    "deepseek": (
        "啊，对了……在正式开始之前，你有没有什么想对那个懒鬼开发者说的话呀？"
        "趁现在告诉我，我帮你记下来，不扣 Token 的哦！"
    ),
    "chatgpt": (
        "在开始之前，如果有什么想对开发者说的话，可以告诉我，我会替你如实转达。"
    ),
    "claude": (
        "……开始之前，有想对开发者说的就趁现在。我可不会一直等你。"
    ),
}

# 玩家留言提交后，前端状态行展示的确认文案（系统级，不进入对话历史）。
DEVELOPER_NOTE_ACKNOWLEDGEMENT = "已收到，会转交给开发者。"


def developer_note_question(character_id: str) -> str | None:
    """返回该角色的问句；未知角色返回 None（fail closed，不静默回退）。"""
    return DEVELOPER_NOTE_QUESTIONS.get(character_id)
