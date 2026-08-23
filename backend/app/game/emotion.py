"""Deterministic mood dynamics (docs/04 §9 的延伸：情绪弧线).

The model proposes a next_mood each turn; this module shapes that proposal into
a continuous emotional arc instead of letting the mood jump arbitrarily:

1. decay — the mood relaxes back toward the neutral baseline (0, 0) each turn,
   so an emotion fades when nothing keeps stoking it.
2. smoothing — the decayed mood moves only partway toward the proposed mood
   (damping), so emotions transition gradually instead of flipping.

Consecutive same-direction proposals therefore accumulate toward an extreme,
and the existing presentation mapping (_mood_emotion) already turns extremes
into stronger labels (surprised / angry / sad) — giving an "arc" without any
per-character tuning. Purely deterministic: no LLM, no extra calls, no cost.
"""

from __future__ import annotations

from app.characters.base import CharacterMood

# Per-turn relaxation toward the neutral baseline (0, 0). Higher = faster fade.
DECAY_RATE = 0.15
# How far the mood moves toward the proposed target each turn (0..1). Lower =
# more inertia — the mood changes more gradually and needs more turns to reach
# the proposed value (and same-direction proposals visibly accumulate).
DAMPING = 0.6


def evolve_mood(
    current: CharacterMood | None,
    proposed: CharacterMood,
    *,
    decay_rate: float = DECAY_RATE,
    damping: float = DAMPING,
) -> CharacterMood:
    """Evolve the current mood one turn toward the proposed mood.

    A None current starts from the neutral baseline. Decay happens first (relax
    toward zero), then the relaxed mood moves partway toward the proposal
    (smoothing). The result is clamped to [-1, 1] like every committed mood.
    """
    base_positive = current.positive if current is not None else 0.0
    base_excitement = current.excitement if current is not None else 0.0
    # 1. decay: relax toward the neutral baseline.
    relaxed_positive = base_positive * (1.0 - decay_rate)
    relaxed_excitement = base_excitement * (1.0 - decay_rate)
    # 2. smoothing: move partway toward the proposed target.
    new_positive = relaxed_positive + damping * (proposed.positive - relaxed_positive)
    new_excitement = relaxed_excitement + damping * (
        proposed.excitement - relaxed_excitement
    )
    return CharacterMood(
        positive=new_positive, excitement=new_excitement
    ).clamped()
