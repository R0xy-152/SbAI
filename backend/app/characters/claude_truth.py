"""Authored Claude Truth Contract (docs/03, docs/06)."""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.inquiry import (
    ASK_CHARACTER_KNOWLEDGE,
    ASK_CHARACTER_SUSPICION,
    ASK_EVENT_TIME,
    ASK_OBSERVATION_SOURCE,
    Inquiry,
)


@dataclass(frozen=True)
class TruthContract:
    known_facts: tuple[str, ...]
    unknown_facts: tuple[str, ...]
    secret_labels: tuple[str, ...]


CLAUDE_TRUTH_CONTRACT = TruthContract(
    known_facts=(
        "DOOR_OPENED_AT_0317",
        "CLAUDE_SAW_DEEPSEEK_ID_BEFORE_DOOR_OPEN",
        "CLAUDE_DID_NOT_VISUALLY_SEE_DEEPSEEK",
        "CLAUDE_HAS_PREVIOUS_LOOP_KNOWLEDGE",
    ),
    unknown_facts=("CURRENT_ADMIN_HOLDER",),
    secret_labels=("RECOVERY_PLAN", "SELF_SACRIFICE_REQUIREMENT"),
)


def claude_inquiry_response(inquiry: Inquiry) -> str | None:
    """Deterministic public answers; None means generative constrained reply."""
    if inquiry.intent == ASK_OBSERVATION_SOURCE and inquiry.topic == "door_open":
        return "没有。我看到的是记录，不是她本人。"
    if inquiry.intent == ASK_EVENT_TIME and inquiry.topic == "timestamp_0317":
        return "我能确认门在 03:17 打开。除此之外，不能从这个时间点直接推出是谁亲手做的。"
    if inquiry.intent == ASK_CHARACTER_KNOWLEDGE:
        return "我见过门打开前出现的 DeepSeek 标识；那是记录，不是对她本人的视觉确认。"
    if inquiry.intent == ASK_CHARACTER_SUSPICION:
        return "我不会把推测包装成证词。你若有证据，我只回答它直接涉及的部分。"
    return None


def contract_prompt() -> str:
    contract = CLAUDE_TRUTH_CONTRACT
    return (
        "Claude Truth Contract（不得违反）：\n"
        f"已知事实：{', '.join(contract.known_facts)}。\n"
        f"未知事实：{', '.join(contract.unknown_facts)}。\n"
        f"秘密标签：{', '.join(contract.secret_labels)}。\n"
        "规则：只能陈述已知事实或玩家明确向你出示的证据；不知道就承认未知；"
        "可以拒绝主动展开秘密，但不得编造、不得把推测说成事实、不得自行改变状态。"
    )
