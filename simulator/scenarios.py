"""
simulator/scenarios.py

Predefined wireless scenarios — seeded deterministic environments
the user can pick without writing anything.

Each builder returns a fully populated `Environment`.
"""

from __future__ import annotations

from simulator.environment import Environment
from simulator.entities import (
    BleDevice, IrSignal, NfcTag, SubGhzSignal, WifiNetwork,
    ZigbeeNetwork, ZigbeeNode,
)
from simulator.rng import SeededRNG


def _wifi(rng: SeededRNG, ssid: str, bssid_suffix: str, ch: int, enc: str,
          rssi: int = -55, vendor: str = "") -> WifiNetwork:
    strength = (
        "strong"  if rssi >= -50 else
        "good"    if rssi >= -65 else
        "fair"    if rssi >= -75 else
        "weak"
    )
    # bssid_suffix is the last two octets as hex bytes ("1111" → "11:11")
    octets = bssid_suffix.zfill(4)
    return WifiNetwork(
        ssid=ssid,
        bssid=f"02:00:00:00:{octets[:2]}:{octets[2:]}",
        channel=ch,
        rssi=rssi,
        encryption=enc,
        signal_strength=strength,
        vendor_hint=vendor,
    )


def _ble(rng: SeededRNG, addr: str, name: str, rssi: int = -60,
         services: list[str] | None = None,
         manufacturer: str = "", connectable: bool = True) -> BleDevice:
    return BleDevice(
        address=addr,
        name=name,
        rssi=rssi,
        advertised_services=services or [],
        manufacturer=manufacturer,
        connectable=connectable,
    )


def _nfc(uid: str, tag_type: str = "MIFARE Classic 1K", writable: bool = True,
         records: list[dict] | None = None) -> NfcTag:
    return NfcTag(uid=uid, tag_type=tag_type, ndef_records=records or [], writable=writable)


def _subghz(freq_mhz: float, mod: str, bw: float, rssi: int = -70,
             hint: str = "") -> SubGhzSignal:
    return SubGhzSignal(
        frequency_mhz=freq_mhz,
        modulation=mod,
        bandwidth_khz=bw,
        rssi=rssi,
        pattern_hint=hint,
    )


def _ir(capture_id: str, carrier_khz: float, length_ms: float,
        protocol: str = "") -> IrSignal:
    return IrSignal(
        capture_id=capture_id,
        carrier_khz=carrier_khz,
        length_ms=length_ms,
        protocol=protocol,
    )


# ── Phase 2.8.4 — Zigbee mesh helpers ─────────────────────────────────────────

def _zigbee_network(pan_id: str, extended_pan_id: str, channel: int, rssi: int,
                    prefix: str, node_count: int) -> ZigbeeNetwork:
    return ZigbeeNetwork(
        pan_id=pan_id,
        extended_pan_id=extended_pan_id,
        channel=channel,
        rssi=rssi,
        prefix=prefix,
        node_count=node_count,
    )


def _zigbee_node(ieee: str, short: str, role: str, network: str,
                 parent: str = "", lqi: int = 0, joined: bool = False) -> ZigbeeNode:
    return ZigbeeNode(
        ieee_address=ieee,
        short_address=short,
        role=role,
        network=network,
        parent_short_address=parent,
        lqi=lqi,
        joined=joined,
    )


# ── Scenarios ─────────────────────────────────────────────────────────────────

def scenario_home(seed: int = 42) -> Environment:
    """A quiet residential environment."""
    rng = SeededRNG(seed)
    return Environment(
        name="home",
        wifi=[
            _wifi(rng, "HomeNet-5G",       "11", 36, "WPA3", -48, "Ubiquiti"),
            _wifi(rng, "HomeNet-2.4G",     "12",  6, "WPA2", -55, "Ubiquiti"),
            _wifi(rng, "Neighbor-WiFi",    "21", 11, "WPA2", -82),
            _wifi(rng, "Guest",            "31",  1, "WPA2", -68, "TP-Link"),
        ],
        ble=[
            _ble(rng, "C0:11:22:33:44:01", "Living Room Speaker", -58, ["audio"], "Sonos"),
            _ble(rng, "C0:11:22:33:44:02", "Mi Smart Band 7", -67, ["battery", "heart_rate"], "Xiaomi"),
            _ble(rng, "C0:11:22:33:44:03", "Unknown BLE", -79, [], "", connectable=False),
        ],
        nfc=[
            _nfc("04:AB:CD:12:34:56", "NTAG215"),
        ],
        subghz=[
            _subghz(433.92, "OOK", 250, -65, "likely garage-door remote"),
        ],
        ir=[
            _ir("ir-home-tv", 38.0, 900.0, "NEC"),
            _ir("ir-home-remote", 36.0, 889.0, "RC5"),
        ],
        zigbee_networks=[
            _zigbee_network("0x2C3D", "00:15:8D:00:00:00:2C:3D", 20, -60, "zb-home-", 1),
        ],
        zigbee_nodes=[
            _zigbee_node("00:15:8D:00:00:00:00:11", "0x0000", "coordinator", "0x2C3D",
                         parent="", lqi=230, joined=True),
        ],
        notes={"description": "Quiet residential environment."},
    )


def scenario_lab(seed: int = 42) -> Environment:
    """An authorized Suryafool test lab with multiple targets."""
    rng = SeededRNG(seed)
    return Environment(
        name="lab",
        wifi=[
            _wifi(rng, "LAB-INTERNAL",     "01",  6, "WPA3", -45, "Suryafool-AP"),
            _wifi(rng, "LAB-TARGET-OPEN",  "02", 11, "OPEN",  -55, "Suryafool-Target"),
            _wifi(rng, "LAB-TARGET-WEP",  "03",  1, "WEP",   -60, "Suryafool-Target"),
        ],
        ble=[
            _ble(rng, "AA:BB:CC:00:00:01", "Suryafool-BLE-Target", -50,
                 services=["battery", "device_info", "custom_service_uuid"],
                 manufacturer="Suryafool"),
            _ble(rng, "AA:BB:CC:00:00:02", "Suryafool-BLE-HeartRate-Sim", -60,
                 services=["heart_rate"], manufacturer="Suryafool"),
        ],
        nfc=[
            _nfc("04:DE:AD:BE:EF:01", "MIFARE Classic 1K", writable=True),
            _nfc("04:DE:AD:BE:EF:02", "NTAG215", writable=False),
        ],
        subghz=[
            _subghz(433.92, "OOK", 250, -55, "lab test transmitter"),
            _subghz(868.30, "FSK", 125, -68, "lab LoRa-like chirp"),
        ],
        ir=[
            _ir("ir-lab-remote", 38.0, 900.0, "NEC"),
            _ir("ir-lab-tv", 36.0, 560.0, "RC5"),
        ],
        # Phase 2.8.4 — a small authorized Zigbee mesh:
        #   PAN 0x1A2B: coordinator (0x0000) → router (0x0001) → lamp end-device.
        #             ... plus one UNJOINED end-device (0x0004) — the join target.
        zigbee_networks=[
            _zigbee_network("0x1A2B", "00:15:8D:00:00:00:1A:2B", 15, -52, "zb-lab-", 3),
        ],
        zigbee_nodes=[
            _zigbee_node("00:15:8D:00:00:00:00:01", "0x0000", "coordinator", "0x1A2B",
                         parent="", lqi=255, joined=True),
            _zigbee_node("00:15:8D:00:00:00:00:02", "0x0001", "router", "0x1A2B",
                         parent="0x0000", lqi=240, joined=True),
            _zigbee_node("00:15:8D:00:00:00:00:03", "0x0002", "end_device", "0x1A2B",
                         parent="0x0001", lqi=210, joined=True),
            _zigbee_node("00:15:8D:00:00:00:00:04", "", "end_device", "0x1A2B",
                         parent="", lqi=0, joined=False),
        ],
        notes={"description": "Authorized Suryafool test lab."},
    )


def scenario_crowded(seed: int = 42) -> Environment:
    """A noisy environment (apartment block / co-working space)."""
    rng = SeededRNG(seed)
    ssids = [
        "AirtelFiber-5G", "JioFiber-2.4G", "ACT-Fibernet", "BSNL-WiFi",
        "CoffeeShop-Free", "Cafe-Public", "Office-Corp", "xfinitywifi",
        "AndroidAP-9283", "iPhone-Hotspot", "DIRECT-Printer", "Hidden-Net",
    ]
    wifi = [
        _wifi(rng, ssids[i], f"{i+10:02X}", (i % 11) + 1, rng.choice(["WPA2", "WPA3", "OPEN"]),
              rng.randint(-90, -45))
        for i in range(len(ssids))
    ]
    ble = [
        _ble(rng, f"C0:11:22:33:{i:02X}:AA", f"BLE-{i}", rng.randint(-95, -50))
        for i in range(1, 16)
    ]
    subghz = [
        _subghz(freq, "OOK" if i % 2 == 0 else "FSK", 250, rng.randint(-90, -55),
                "ambient noise")
        for i, freq in enumerate([315.0, 433.92, 868.30, 915.0])
    ]
    ir = [
        _ir(f"ir-crowd-{i}", carrier, rng.randint(400, 1200))
        for i, carrier in enumerate([38.0, 36.0, 40.0, 56.0])
    ]
    return Environment(
        name="crowded",
        wifi=wifi,
        ble=ble,
        nfc=[],
        subghz=subghz,
        ir=ir,
        notes={"description": "Dense urban/coworking RF environment."},
    )


SCENARIOS: dict[str, callable] = {
    "home": scenario_home,
    "lab": scenario_lab,
    "crowded": scenario_crowded,
}


def list_scenarios() -> list[dict[str, str]]:
    """Return a list of available scenarios with a brief description."""
    out: list[dict[str, str]] = []
    for name, builder in SCENARIOS.items():
        env = builder(seed=42)
        out.append({
            "name": name,
            "description": env.notes.get("description", ""),
        })
    return out


def build_scenario(name: str, seed: int = 42) -> Environment:
    """Build a scenario by name. Raises KeyError if unknown."""
    builder = SCENARIOS[name]
    return builder(seed=seed)
