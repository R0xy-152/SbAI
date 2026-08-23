"""Co-presence deterministic parsing (docs/04 §60-62)."""

from app.game.interjection import (
    mentioned_character_ids,
    named_primary,
    pick_interjector,
)


def test_mentioned_matches_alias_case_insensitive():
    assert mentioned_character_ids("Claude，你怎么看？", {"deepseek", "claude"}) == ["claude"]
    assert mentioned_character_ids("DEEPSEEK 你来说", {"deepseek", "claude"}) == ["deepseek"]
    assert mentioned_character_ids("豆包 看到了什么", {"doubao", "claude"}) == ["doubao"]
    assert mentioned_character_ids("GPT 你怎么看", {"chatgpt", "deepseek"}) == ["chatgpt"]


def test_mentioned_returns_first_appearance_order():
    assert mentioned_character_ids("Claude 你先，DeepSeek 你后", {"deepseek", "claude"}) == [
        "claude",
        "deepseek",
    ]


def test_mentioned_ignores_absent_characters():
    assert mentioned_character_ids("Claude 和豆包", {"claude"}) == ["claude"]
    assert mentioned_character_ids("你好", {"deepseek", "claude"}) == []


def test_named_primary_returns_first_named_present_character():
    assert named_primary("Claude，你怎么看？", {"deepseek", "claude"}) == "claude"
    assert named_primary("你好", {"deepseek", "claude"}) is None


def test_pick_interjector_fires_only_when_primary_mentions_another():
    present = {"deepseek", "claude", "chatgpt"}
    # 主回应者 DeepSeek 提到了 Claude → Claude 接话
    assert pick_interjector("deepseek", "Claude 一直盯着我看", present) == "claude"
    # 主回应者没提任何人 → 无接话
    assert pick_interjector("deepseek", "今天天气不错", present) is None
    # 主回应者提到自己 → 不算接话
    assert pick_interjector("deepseek", "我 DeepSeek 很厉害", present) is None


def test_pick_interjector_requires_another_present_character():
    # 单角色在场 → 永远无接话
    assert pick_interjector("deepseek", "Claude 你好", {"deepseek"}) is None
