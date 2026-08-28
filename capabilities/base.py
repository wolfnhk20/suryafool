"""
capabilities/base.py

Capability, CapabilityProvider, and the simulator-backed provider.

A Capability describes what an agent can ask for (e.g. "wifi.discovery.discover").
A CapabilityProvider knows how to actually run a request.

This is the Hardware Abstraction Layer's seam: the same `wifi.discovery.discover`
can be served by a SimulatorProvider (Phase 2 default) or a future ESP32Provider.

Phase 2.7.1 — capability contract extension:
A Capability now carries the metadata the rest of the platform needs to reason
about a future multi-domain (wifi / ble / subghz / nfc / infrared / camera /
ethernet / usb) hardware/security operation surface WITHOUT a second capability
system. Every new field is opt-in with a safe default so every existing
positional `Capability(...)` call keeps working unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.mission import ActionRisk
from core.observation import Observation


# Open set of wireless/network domains Suryafool intends to support. Used as a
# sanity-check vocabulary (see KNOWN_DOMAINS tests); we deliberately do NOT
# enforce membership — adding a new domain is a Phase-3+ concern and the
# catalogue's job, not the dataclass's.
KNOWN_DOMAINS: frozenset[str] = frozenset({
    "wifi", "ble", "subghz", "nfc", "infrared", "camera", "ethernet", "usb",
})


@dataclass
class Capability:
    """Describes a single capability action.

    Phase 2.7.1 metadata (opt-in, all with safe defaults):

      domain            — wireless/network domain (auto-derived from the
                          namespace before the first dot if unset). Free-form
                          string; see KNOWN_DOMAINS for the intended vocabulary.
      requires_args     — tuple of required input arg names (e.g.
                          ("address", "characteristic", "value") for
                          ble.discovery.write). Descriptive; providers already
                          validate args structurally.
      output_entity_type — expected Entity.type of the Observation produced
                          ("wifi_network", "ble_device", "nfc_tag",
                          "subghz_signal", ...). "" means unspecified.
      requires          — tuple of prerequisite capability keys (e.g.
                          ("ble.discovery.connect",) for ble.discovery.write).
                          Consumed by Capability.prerequisites_met() against
                          the env's observed capability set; enables future
                          observe -> test -> observe loops without a second
                          mission-state machine.
      hardware          — declared hardware/domain requirement ("esp32"
                          for a future firmware backend, "" = simulator-only).
      produces_evidence — whether the action captures evidence. Reserved for
                          the evidence/artifact pipeline (later subphase).
      mutates_state     — whether the action may mutate environment state.
                          False for passive observation, True for active
                          state-changing actions (connect, write, nfc.read,
                          subghz.analyze). This is the stateful-vs-
                          observational distinction.
    """
    name: str                           # human-readable, e.g. "Wi-Fi Discovery"
    capability: str                     # namespace, e.g. "wifi.discovery"
    action: str                         # verb, e.g. "discover"
    risk: ActionRisk = ActionRisk.PASSIVE
    description: str = ""
    # ── Phase 2.7.1 metadata (opt-in, default-safe) ────────────────────────
    domain: str = ""
    requires_args: tuple[str, ...] = ()
    output_entity_type: str = ""
    requires: tuple[str, ...] = ()
    hardware: str = ""
    produces_evidence: bool = False
    mutates_state: bool = False

    def __post_init__(self) -> None:
        if not self.capability:
            raise ValueError("Capability.capability must be a non-empty namespace.")
        if not self.action:
            raise ValueError("Capability.action must be a non-empty verb.")
        # Auto-derive domain from the namespace before the first dot (e.g.
        # "wifi.discovery" -> "wifi") when the caller did not set one. A
        # namespace without a dot (e.g. "nfc") is its own domain.
        if not self.domain:
            self.domain = self.capability.split(".", 1)[0]

    @property
    def key(self) -> str:
        return f"{self.capability}.{self.action}"

    def prerequisites_met(self, observed_keys: set[str]) -> bool:
        """True iff every capability key in `requires` is present in the
        observed-capability set. Empty `requires` always returns True
        (passive/observation-only actions have no prerequisites)."""
        return all(req in observed_keys for req in self.requires)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capability": self.capability,
            "action": self.action,
            "risk": self.risk.value,
            "description": self.description,
            "key": self.key,
            "domain": self.domain,
            "requires_args": list(self.requires_args),
            "output_entity_type": self.output_entity_type,
            "requires": list(self.requires),
            "hardware": self.hardware,
            "produces_evidence": self.produces_evidence,
            "mutates_state": self.mutates_state,
        }


class CapabilityProvider(ABC):
    """Backend that knows how to execute a set of capability actions."""

    name: str = "abstract"

    @abstractmethod
    def supports(self, capability: str, action: str) -> bool:
        """Return True if this provider can execute (capability, action)."""

    @abstractmethod
    def execute(self, capability: str, action: str,
                args: Optional[dict[str, Any]] = None) -> Observation:
        """Execute the action and return a structured Observation."""


# ── Simulator provider ────────────────────────────────────────────────────────

class SimulatorProvider(CapabilityProvider):
    """Backend that delegates everything to the wireless simulator."""

    name = "simulator"

    def __init__(self, environment):
        # Late import to avoid circular import at module load
        from simulator.simulator import execute as sim_execute
        self._execute = sim_execute
        self._env = environment

    def set_environment(self, environment) -> None:
        self._env = environment

    def supports(self, capability: str, action: str) -> bool:
        from simulator.simulator import HANDLERS
        return (capability, action) in HANDLERS

    def execute(self, capability: str, action: str,
                args: Optional[dict[str, Any]] = None) -> Observation:
        return self._execute(self._env, capability, action, args or {})


# ── Default capability catalogue ───────────────────────────────────────────────
#
# Phase 2.7.1 — metadata declared per entry. `mutates_state` reflects the
# existing simulator semantics (the active action handlers already toggle
# entity fields / env.notes); `requires_args` mirrors the args each handler
# validates; `requires` encodes the hard "must have run first" relations
# (ble.write needs ble.connect). `produces_evidence` stays False for every
# entry — the evidence/artifact pipeline is a later subphase.

DEFAULT_CAPABILITIES: list[Capability] = [
    Capability("Wi-Fi Discovery",   "wifi.discovery",   "discover", ActionRisk.PASSIVE,
               "Discover nearby Wi-Fi networks.",
               domain="wifi", output_entity_type="wifi_network"),
    Capability("Wi-Fi Inspect",     "wifi.discovery",   "inspect",  ActionRisk.PASSIVE,
               "Inspect a specific Wi-Fi network.",
               domain="wifi", requires_args=("bssid",), output_entity_type="wifi_network"),
    Capability("BLE Discovery",     "ble.discovery",    "discover", ActionRisk.PASSIVE,
               "Discover nearby BLE devices.",
               domain="ble", output_entity_type="ble_device"),
    Capability("BLE Inspect",        "ble.discovery",    "inspect",  ActionRisk.PASSIVE,
               "Inspect a specific BLE device.",
               domain="ble", requires_args=("address",), output_entity_type="ble_device"),
    Capability("NFC Scan",           "nfc.discovery",    "scan",     ActionRisk.PASSIVE,
               "Scan for NFC/RFID tags.",
               domain="nfc", output_entity_type="nfc_tag"),
    # ── Phase 2.8.2 — NFC/RFID scan/select/read slice ────────────────────
    Capability("NFC Select",         "nfc.discovery",     "select",   ActionRisk.PASSIVE,
               "Identify and activate a known NFC/RFID tag (PN532-style InListPassiveTarget + activate).",
               domain="nfc", requires_args=("uid",), output_entity_type="nfc_tag",
               mutates_state=True),
    Capability("NFC Read",          "nfc.discovery",     "read",     ActionRisk.SAFE_ACTIVE,
               "Read NDEF records from a previously-selected tag.",
               domain="nfc", requires_args=("uid",), output_entity_type="nfc_tag",
               mutates_state=True, produces_evidence=True),  # Phase 2.8.2: kind "nfc_read"
    Capability("Sub-GHz Spectrum",   "subghz.discovery", "spectrum", ActionRisk.PASSIVE,
               "Spectrum scan of Sub-GHz bands.",
               domain="subghz", output_entity_type="subghz_signal"),
    Capability("Sub-GHz Analyze",   "subghz.discovery", "analyze",  ActionRisk.SAFE_ACTIVE,
               "Analyze a specific Sub-GHz signal.",
               domain="subghz", requires_args=("frequency_mhz",),
               output_entity_type="subghz_signal", mutates_state=True,
               produces_evidence=True),
    Capability("BLE Connect",       "ble.discovery",    "connect",  ActionRisk.SAFE_ACTIVE,
               "Actively connect to a known BLE device and read its GATT service table.",
               domain="ble", requires_args=("address",), output_entity_type="ble_device",
               mutates_state=True),
    Capability("BLE Write",          "ble.discovery",    "write",    ActionRisk.SENSITIVE_ACTIVE,
               "Write a GATT characteristic value on a connected BLE device (mutates simulated device state).",
               domain="ble",
               requires_args=("address", "characteristic", "value"),
               output_entity_type="ble_device",
               requires=("ble.discovery.connect",),
               mutates_state=True),
    Capability("Wi-Fi Capture Handshake", "wifi.capture",  "handshake", ActionRisk.SAFE_ACTIVE,
               "Actively capture a WPA/WPA2/WPA3 EAPOL handshake on a target network.",
               domain="wifi",
               requires_args=("bssid",),
               output_entity_type="wifi_network",
               mutates_state=True,
               produces_evidence=True),
    Capability("Wi-Fi Capture PMKID",     "wifi.capture",  "pmkid",     ActionRisk.SENSITIVE_ACTIVE,
               "Request and capture a PMKID frame from a target WPA-encrypted network (requires preceding handshake capture).",
               domain="wifi",
               requires_args=("bssid",),
               output_entity_type="wifi_network",
               requires=("wifi.capture.handshake",),
               mutates_state=True,
               produces_evidence=True),
    Capability("BLE GATT Pair",          "ble.gatt",      "pair",  ActionRisk.SAFE_ACTIVE,
               "Establish BLE secure pairing/bonding on a connected BLE device (mutates simulated device state).",
               domain="ble",
               requires_args=("address",),
               output_entity_type="ble_device",
               requires=("ble.discovery.connect",),
               mutates_state=True,
               produces_evidence=True),
    Capability("BLE GATT Write",          "ble.gatt",      "write", ActionRisk.SENSITIVE_ACTIVE,
               "Write an encrypted GATT characteristic on a paired BLE device (mutates simulated device state).",
               domain="ble",
               requires_args=("address", "characteristic", "value"),
               output_entity_type="ble_device",
               requires=("ble.gatt.pair",),
               mutates_state=True,
               produces_evidence=True),
    # ── Phase 2.8.1 — Sub-GHz/RF stateful capture slice ──────────────────────
    # The `subghz.capture` namespace sits alongside `subghz.discovery`, exactly
    # parallel to `wifi.capture`/`wifi.discovery` (2.7.2) and `ble.gatt`/
    # `ble.discovery` (2.7.3): discovery reads, capture mutates. A captured
    # signal then unlocks evidence production on the existing analyze action
    # (per-target prereq: s.captured=True on the SAME frequency, enforced in
    # the handler — exactly like wifi.capture.pmkid needing handshake_captured
    # on the SAME bssid). Catalogue-level `requires=()` mirrors
    # wifi.capture.handshake (no catalogue prereq; the per-target gate is the
    # operator's question, the planner's question is answered by
    # Capability.prerequisites_met(env-observed keys)).
    Capability("Sub-GHz Capture Signal", "subghz.capture", "signal", ActionRisk.SAFE_ACTIVE,
               "Actively capture samples of a specific Sub-GHz signal at a known frequency (mutates SubGhzSignal).",
               domain="subghz",
               requires_args=("frequency_mhz",),
               output_entity_type="subghz_signal",
               mutates_state=True,
               produces_evidence=True),
    # ── Phase 2.8.0 — multi-domain foundation ────────────────────────────────
    # Infrared (flat `infrared` namespace — domain-auto-derived by
    # __post_init__). These entries are catalogue-staked but explicitly
    # UNSUPPORTED until Phase 2.8.3 adds handlers: registry.resolve() returns
    # supported=False and the policy gate rejects BEFORE the provider, so the
    # surface exists without pretending to work. `infrared.transmit` is a
    # replay-style SENSITIVE_ACTIVE interaction requiring a prior capture
    # (cross-namespace prereq, parallel to ble.gatt.pair requires connect).
    Capability("IR Capture",   "infrared", "capture",  ActionRisk.PASSIVE,
               "Passively capture ambient infrared signals.",
               domain="infrared", output_entity_type="ir_signal"),
    Capability("IR Analyze",   "infrared", "analyze",  ActionRisk.SAFE_ACTIVE,
               "Decode the protocol of a captured infrared signal.",
               domain="infrared", requires_args=("capture_id",),
               output_entity_type="ir_signal", mutates_state=True),
    Capability("IR Transmit",  "infrared", "transmit", ActionRisk.SENSITIVE_ACTIVE,
               "Re-transmit a previously captured infrared signal (authorized interaction only).",
               domain="infrared", requires_args=("capture_id",),
               output_entity_type="ir_signal",
               requires=("infrared.capture",), mutates_state=True),
    # Ethernet / wired networking.
    Capability("Ethernet Discovery", "ethernet.discovery", "discover", ActionRisk.PASSIVE,
               "Discover hosts on the local wired Ethernet segment.",
               domain="ethernet", output_entity_type="ethernet_host"),
    Capability("Ethernet Inspect",   "ethernet.discovery", "inspect",  ActionRisk.PASSIVE,
               "Inspect a specific Ethernet host.",
               domain="ethernet", requires_args=("host",),
               output_entity_type="ethernet_host"),
    # USB.
    Capability("USB Enumerate", "usb.discovery", "enumerate", ActionRisk.PASSIVE,
               "Enumerate USB devices present on the host.",
               domain="usb", output_entity_type="usb_device"),
    Capability("USB Inspect",   "usb.discovery", "inspect",   ActionRisk.PASSIVE,
               "Inspect a specific USB device.",
               domain="usb", requires_args=("path",),
               output_entity_type="usb_device"),
]
