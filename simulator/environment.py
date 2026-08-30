"""
simulator/environment.py

The simulated wireless environment state.

Mutable container — the Simulator reads it on each action and may mutate
(consume one-shot observations, mark a tag as read, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from simulator.entities import (
    BleDevice,
    EthernetHost,
    IrSignal,
    NfcTag,
    SubGhzSignal,
    UsbDevice,
    WifiNetwork,
    ZigbeeNetwork,
    ZigbeeNode,
)


@dataclass
class Environment:
    name: str = "default"
    wifi: list[WifiNetwork] = field(default_factory=list)
    ble: list[BleDevice] = field(default_factory=list)
    nfc: list[NfcTag] = field(default_factory=list)
    subghz: list[SubGhzSignal] = field(default_factory=list)
    # Phase 2.8.0 multi-domain substrate — empty until the dedicated 2.8.x
    # subphases add stateful handlers + scenario population.
    ir: list[IrSignal] = field(default_factory=list)
    ethernet: list[EthernetHost] = field(default_factory=list)
    usb: list[UsbDevice] = field(default_factory=list)
    # Phase 2.8.4 — Zigbee wireless mesh. a PAN list + its node population.
    zigbee_networks: list[ZigbeeNetwork] = field(default_factory=list)
    zigbee_nodes: list[ZigbeeNode] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)   # free-form notes (read flags, etc.)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe snapshot of the environment."""
        return {
            "name": self.name,
            "wifi": [w.to_dict() for w in self.wifi],
            "ble": [b.to_dict() for b in self.ble],
            "nfc": [t.to_dict() for t in self.nfc],
            "subghz": [s.to_dict() for s in self.subghz],
            "ir": [s.to_dict() for s in self.ir],
            "ethernet": [h.to_dict() for h in self.ethernet],
            "usb": [d.to_dict() for d in self.usb],
            "zigbee_networks": [n.to_dict() for n in self.zigbee_networks],
            "zigbee_nodes": [n.to_dict() for n in self.zigbee_nodes],
            "notes": dict(self.notes),
        }
