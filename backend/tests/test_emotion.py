"""Deterministic mood dynamics (docs/04 §9 情绪弧线)."""

import pytest

from app.characters.base import CharacterMood
from app.game.emotion import DECAY_RATE, DAMPING, evolve_mood


def test_evolve_from_neutral_baseline_moves_partway():
    mood = evolve_mood(None, CharacterMood(0.9, 0.4))
    assert mood.positive == pytest.approx(DAMPING * 0.9)
    assert mood.excitement == pytest.approx(DAMPING * 0.4)


def test_evolve_smooths_jumps():
    mood = evolve_mood(CharacterMood(0.0, 0.0), CharacterMood(1.0, 0.0))
    assert mood.positive == pytest.approx(DAMPING)
    assert mood.positive < 1.0  # 不会瞬间跳到目标


def test_evolve_decays_when_target_is_neutral():
    mood = evolve_mood(CharacterMood(1.0, 1.0), CharacterMood(0.0, 0.0))
    relaxed = 1.0 * (1.0 - DECAY_RATE)
    expected = relaxed + DAMPING * (0.0 - relaxed)
    assert mood.positive == pytest.approx(expected)
    assert mood.positive < 1.0  # 情绪自然回落


def test_evolve_accumulates_same_direction():
    mood = None
    for _ in range(3):
        mood = evolve_mood(mood, CharacterMood(1.0, 0.0))
    assert mood.positive > DAMPING  # 超过第一轮的值（积累）
    assert mood.positive < 1.0  # 有衰减，永远到不了 1


def test_evolve_clamps_to_range():
    mood = evolve_mood(None, CharacterMood(5.0, -5.0))
    assert mood.positive == 1.0
    assert mood.excitement == -1.0
