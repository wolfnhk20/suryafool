"""
simulator/entities.py

Structured simulated wireless entities.

Each Entity subclass is a typed view over a plain dict so they serialize
cleanly into the run record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WifiNetwork:
    ssid: str
    bssid: str
    channel: int
    rssi: int
    encryption: str                       # "WPA2", "WPA3", "OPEN", "WEP"
    signal_strength: str = ""             # "weak"|"fair"|"good"|"strong" — derived
    vendor_hint: str = ""
    # Phase 2.7.2 stateful capture fields — set by wifi.capture.handshake/pmkid.
    # A later wifi.discovery.inspect reflects the change (state → observation loop).
    handshake_captured: bool = False
    captured_frames: int = 0              # EAPOL frame count from a captured handshake
    pmkid_captured: bool = False

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class BleDevice:
    address: str
    name: str
    rssi: int
    advertised_services: list[str] = field(default_factory=list)
    manufacturer: str = ""
    connectable: bool = True
    connected: bool = False
    gatt_services: list[str] = field(default_factory=list)
    characteristics: dict[str, str] = field(default_factory=dict)
    # Phase 2.7.3 stateful BLE GATT pairing fields — set by ble.gatt.pair/write.
    # A later ble.discovery.inspect reflects the change (state -> observation
    # loop), exactly parallel to wifi.capture on WifiNetwork (Phase 2.7.2).
    paired: bool = False
    secure_characteristics: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class NfcTag:
    uid: str
    tag_type: str                         # "MIFARE Classic", "NTAG215", etc.
    ndef_records: list[dict[str, Any]] = field(default_factory=list)
    writable: bool = True
    # ── Phase 2.8.2 — NFC scan/select/read state ──────────────────────────
    ndef_supported: bool = True            # False => tag identified but read-only/proprietary memory layout
    selected: bool = False                 # set by nfc.discovery.select success (PN532 InListPassiveTarget + activate)
    read: bool = False                     # set by nfc.discovery.read success (replaces ephemeral obs flag)
    read_at: float = 0.0                   # timestamp of last successful read (persisted in run.json snapshots)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class SubGhzSignal:
    frequency_mhz: float
    modulation: str                       # "OOK", "FSK", "ASK"
    bandwidth_khz: float
    rssi: int
    pattern_hint: str = ""                # short textual hint about what it might be
    # ── Phase 2.8.1 stateful capture fields — set by subghz.capture.signal
    # and consumed by subghz.discovery.analyze (a later analyze reflects the
    # change; state -> observation loop). The capture handler flips `captured`,
    # deterministically derives `sample_count` + `capture_quality`; the
    # analyze handler populates `decoded_protocol_hint` from a heuristic map.
    captured: bool = False
    sample_count: int = 0
    capture_quality: str = ""             # "clean"|"noisy"|"partial" — derived
    decoded_protocol_hint: str = ""       # heuristic label, NOT a real decoder

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


# ── Phase 2.8.0 multi-domain substrate ────────────────────────────────────────
# Pure entity representations for the remaining domains. These carry NO
# simulator handlers yet — the catalogue entries are explicit-unsupported
# (registry.resolve -> supported=False; policy REJECTs before the provider)
# until their dedicated 2.8.x subphase adds stateful handlers. The dataclasses
# are the deterministic field contract those subphases build on.

@dataclass
class IrSignal:
    """A captured infrared burst. `protocol` is the decode target of a future
    `infrared.analyze`; empty until then."""
    capture_id: str
    carrier_khz: float                    # typical IR carriers 36–56 kHz
    length_ms: float                      # burst duration in milliseconds
    protocol: str = ""                    # e.g. "NEC", "RC5"; "" = undecoded

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class EthernetHost:
    """A host observed on a wired Ethernet segment."""
    mac: str
    ip: str
    hostname: str = ""
    vendor_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class UsbDevice:
    """A USB device present on the host's bus."""
    path: str                             # device path, e.g. "1-2" or "/dev/ttyUSB0"
    vid: str
    pid: str
    manufacturer: str = ""
    product: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()
