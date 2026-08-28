"""
simulator/rng.py

Deterministic, seedable random generator for reproducible scenarios.

A plain `random.Random(seed)` instance — no LLM, no surprises.
"""

from __future__ import annotations

import random


class SeededRNG:
    """Thin wrapper so callers don't import `random` directly."""

    def __init__(self, seed: int = 42):
        self.seed = int(seed)
        self._rng = random.Random(self.seed)

    def reset(self) -> None:
        self._rng = random.Random(self.seed)

    # ── Delegations ────────────────────────────────────────────────────────────
    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq):
        return self._rng.choice(seq)

    def choices(self, seq, k: int = 1, weights=None):
        return self._rng.choices(seq, k=k, weights=weights)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def random(self) -> float:
        return self._rng.random()

    def shuffle(self, seq):
        self._rng.shuffle(seq)
        return seq
