"""
core/confidence.py

Confidence levels for observations and hypotheses.
"""

from __future__ import annotations

from enum import Enum


class Confidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"

    @property
    def weight(self) -> float:
        return {
            Confidence.CONFIRMED: 1.0,
            Confidence.LIKELY: 0.75,
            Confidence.POSSIBLE: 0.5,
            Confidence.UNKNOWN: 0.25,
        }[self]

    def __str__(self) -> str:
        return self.value
