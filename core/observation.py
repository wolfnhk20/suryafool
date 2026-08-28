"""
core/observation.py

Structured observation types — the output of any capability action.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from core.confidence import Confidence
from core.evidence import EvidenceRecord


@dataclass
class Entity:
    """A logical wireless entity (network, device, tag, signal)."""
    id: str
    type: str                        # "wifi_network" | "ble_device" | "nfc_tag" | "subghz_signal"
    label: str                       # human-readable
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: Confidence = Confidence.LIKELY
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["confidence"] = self.confidence.value
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Entity":
        d = dict(d)
        d["confidence"] = Confidence(d.get("confidence", "UNKNOWN"))
        return Entity(**d)


@dataclass
class Observation:
    """A single structured observation produced by a capability.

    `evidence` is the optional list of durable `EvidenceRecord`s surfaced by
    a capture-style capability (Phase 2.7.5+). Default empty — passive and
    failed actions produce no evidence. The engine propagates this list to
    both `ActionRecord.evidence` and `Run.evidence`, and emits one
    `evidence.created` JSONL event per item.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability: str = ""             # e.g. "wifi.discovery"
    action: str = ""                 # e.g. "discover"
    entities: list[Entity] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    summary: str = ""
    evidence: list[EvidenceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "capability": self.capability,
            "action": self.action,
            "entities": [e.to_dict() for e in self.entities],
            "raw_data": self.raw_data,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Observation":
        d = dict(d)
        d["entities"] = [Entity.from_dict(e) for e in d.get("entities", [])]
        d["evidence"] = [EvidenceRecord.from_dict(e) for e in d.get("evidence", [])]
        return Observation(**d)
