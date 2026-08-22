"""Conversation-style rules + persona voice (docs/04 §18.1, §19-39).

The shared style block (CONVERSATION_STYLE_RULES) makes every generative reply
read like a person with their own intent and knowledge blind spots, not an
omniscient, even-tempered assistant. Each persona then adds its own verbal
tics. These tests assert the shared block is actually injected into the system
prompt, that the per-character voices stay distinct, and that the shared block
itself stays character-agnostic (no role marker leakage).
"""

from __future__ import annotations

from app.characters.base import CONVERSATION_STYLE_RULES
from app.characters.chatgpt import CHATGPT_PERSONA_SYSTEM
from app.characters.claude import CLAUDE_PERSONA_SYSTEM
from app.characters.deepseek import DEEPSEEK_PERSONA_SYSTEM, DeepSeekRuntime
from app.providers.mock import MockProvider


def test_shared_style_rules_reach_system_prompt():
    prompt = DeepSeekRuntime(MockProvider())._system_prompt()
    # Anti-template tone, intentful speech, and short turns are the three
    # "thinking AI" levers the shared block carries.
    assert "助手腔" in prompt
    assert "自己的目的" in prompt
    assert "1–3 句" in prompt


def test_shared_style_rules_do_not_leak_role_markers():
    # The shared block must stay character-agnostic so it never smuggles a
    # specific character's role marker across personas (docs/04 §68).
    assert "反派" not in CONVERSATION_STYLE_RULES
    assert "看不见" not in CONVERSATION_STYLE_RULES


def test_personas_carry_distinct_verbal_ticks():
    # DeepSeek: ellipses + token obsession (贪 Token, docs/04 §23).
    assert "……" in DEEPSEEK_PERSONA_SYSTEM
    assert "Token" in DEEPSEEK_PERSONA_SYSTEM
    # Claude: terse, controlled, no loss of menace (docs/04 §38).
    assert "话少而精" in CLAUDE_PERSONA_SYSTEM
    # ChatGPT: protective, reliable (docs/04 §30-32).
    assert "保护" in CHATGPT_PERSONA_SYSTEM
