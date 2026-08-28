"""
simulator/simulator.py

The wireless environment simulator — action handlers that produce structured
observations. This is what capability providers call under the hood for
the "simulator" backend.

Action surface (deterministic, no LLM):

  wifi.discover          -> Observation with WifiNetwork entities
  wifi.inspect           -> Observation for a single wifi network (by bssid)
  wifi.capture.handshake -> Active: capture EAPOL handshake frames (mutates WifiNetwork)
  wifi.capture.pmkid     -> Active: capture PMKID frame on a prior-handshake target (mutates WifiNetwork)
  ble.discover           -> Observation with BleDevice entities
  ble.inspect            -> Observation for a single BLE device (by address; surfaces paired/secure-write state when present)
  ble.connect            -> Active: link-layer connect + read GATT service table (mutates BleDevice)
  ble.write              -> Active: SENSITIVE write to an unauthenticated characteristic (mutates BleDevice.characteristics)
  ble.gatt.pair          -> Active: SAFE pairing/bonding on a connected device (mutates BleDevice.paired + secure_characteristics)
  ble.gatt.write         -> Active: SENSITIVE encrypted write within a paired session (mutates BleDevice.secure_characteristics)
  nfc.scan               -> Observation with NfcTag entities
  nfc.read               -> Observation reading NDEF records from a tag (one-shot)
  subghz.spectrum        -> Observation with SubGhzSignal entities
  subghz.analyze         -> Observation characterizing a captured signal (requires prior capture on same freq)
  subghz.capture.signal  -> Phase 2.8.1 Active: capture samples of a known signal (mutates SubGhzSignal; produces evidence)

Each action returns an Observation and may mutate the environment
(e.g. mark a tag as read).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from core.confidence import Confidence
from core.evidence import EvidenceRecord
from core.observation import Entity, Observation
from simulator.environment import Environment
from simulator.entities import WifiNetwork, BleDevice, NfcTag, SubGhzSignal


def _wifi_entities(env: Environment) -> list[Entity]:
    out: list[Entity] = []
    for w in env.wifi:
        out.append(Entity(
            id=w.bssid,
            type="wifi_network",
            label=w.ssid or "(hidden)",
            confidence=Confidence.CONFIRMED,
            attributes=w.to_dict(),
        ))
    return out


def _ble_entities(env: Environment) -> list[Entity]:
    out: list[Entity] = []
    for b in env.ble:
        out.append(Entity(
            id=b.address,
            type="ble_device",
            label=b.name or "(unnamed)",
            confidence=Confidence.CONFIRMED if b.connectable else Confidence.LIKELY,
            attributes=b.to_dict(),
        ))
    return out


def _nfc_entities(env: Environment) -> list[Entity]:
    out: list[Entity] = []
    for t in env.nfc:
        out.append(Entity(
            id=t.uid,
            type="nfc_tag",
            label=f"NFC {t.tag_type} {t.uid[-5:]}",
            confidence=Confidence.CONFIRMED,
            attributes=t.to_dict(),
        ))
    return out


def _subghz_entities(env: Environment) -> list[Entity]:
    out: list[Entity] = []
    for s in env.subghz:
        sig_id = f"{s.frequency_mhz:.3f}MHz-{s.modulation}"
        out.append(Entity(
            id=sig_id,
            type="subghz_signal",
            label=f"{s.frequency_mhz:.2f} MHz {s.modulation}",
            confidence=Confidence.LIKELY,
            attributes=s.to_dict(),
        ))
    return out


# ── Action implementations ────────────────────────────────────────────────────

def action_wifi_discover(env: Environment, args: dict[str, Any]) -> Observation:
    entities = _wifi_entities(env)
    return Observation(
        capability="wifi.discovery",
        action="discover",
        entities=entities,
        raw_data={"count": len(entities)},
        summary=f"Discovered {len(entities)} Wi-Fi network(s).",
    )


def action_wifi_inspect(env: Environment, args: dict[str, Any]) -> Observation:
    bssid = args.get("bssid", "")
    for w in env.wifi:
        if w.bssid == bssid:
            ent = Entity(
                id=w.bssid, type="wifi_network", label=w.ssid or "(hidden)",
                confidence=Confidence.CONFIRMED, attributes=w.to_dict(),
            )
            # Surface capture state in the summary when present (mirrors
            # ble.discovery.inspect). Fresh networks get the same summary
            # as before, preserving Phase 2 read compat.
            parts: list[str] = []
            if w.handshake_captured:
                parts.append(f"handshake captured ({w.captured_frames} frames)")
            if w.pmkid_captured:
                parts.append("PMKID captured")
            suffix = ("; " + "; ".join(parts)) if parts else ""
            return Observation(
                capability="wifi.discovery", action="inspect",
                entities=[ent], raw_data=w.to_dict(),
                summary=f"Inspected Wi-Fi network {w.ssid} ({w.bssid}){suffix}.",
            )
    return Observation(
        capability="wifi.discovery", action="inspect",
        entities=[], raw_data={"bssid": bssid},
        summary=f"No Wi-Fi network found for bssid={bssid}.",
    )


# WPA encryption types eligible for handshake/PMKID capture. OPEN/WEP carry
# no 4-way handshake or PMKID, so capture attempts return a structured failure.
_WPA_ENC = ("WPA2", "WPA3")


def action_wifi_capture_handshake(env: Environment, args: dict[str, Any]) -> Observation:
    bssid_arg = args.get("bssid")
    if not isinstance(bssid_arg, str) or not bssid_arg.strip():
        return Observation(
            capability="wifi.capture", action="handshake",
            entities=[], raw_data={"bssid": bssid_arg},
            summary="Invalid or missing 'bssid' argument — handshake capture aborted.",
        )
    bssid = bssid_arg.strip()
    for w in env.wifi:
        if w.bssid == bssid:
            if w.encryption not in _WPA_ENC:
                return Observation(
                    capability="wifi.capture", action="handshake",
                    entities=[], raw_data={"bssid": bssid, "encryption": w.encryption},
                    summary=f"{w.ssid} ({bssid}) uses {w.encryption}; no WPA handshake to capture.",
                )
            w.handshake_captured = True
            w.captured_frames = 4                # the four EAPOL frames of a 4-way handshake
            env.notes[f"wifi_handshake:{bssid}"] = time.time()
            ent = Entity(
                id=w.bssid, type="wifi_network", label=w.ssid or "(hidden)",
                confidence=Confidence.CONFIRMED, attributes=w.to_dict(),
            )
            # Phase 2.7.5 — successful capture produces a durable EvidenceRecord.
            # No giant fake packet blobs: realistic metadata only (frame count,
            # encryption, ssid, bssid). Failed capture paths above return early
            # with `evidence=[]` (default) — no false-positive evidence.
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="wifi.capture",
                source_action="handshake",
                # source_action_id is patched by the engine after it observes
                # the request — the simulator does not see the ActionRequest.
                # Ponytail: keep the simulator decoupled from the run model.
                target_entity_id=w.bssid,
                target_entity_type="wifi_network",
                kind="wifi_eapol_handshake",
                summary=(
                    f"Captured {w.captured_frames} EAPOL frames "
                    f"({w.encryption}) from {w.ssid} ({w.bssid})."
                ),
                metadata={
                    "frame_count": w.captured_frames,
                    "encryption": w.encryption,
                    "ssid": w.ssid,
                    "bssid": w.bssid,
                    "channel": w.channel,
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="wifi.capture", action="handshake",
                entities=[ent], raw_data=w.to_dict(),
                summary=f"Captured {w.captured_frames} EAPOL frame(s) from {w.ssid} ({bssid}).",
                evidence=evidence,
            )
    return Observation(
        capability="wifi.capture", action="handshake",
        entities=[], raw_data={"bssid": bssid},
        summary=f"No Wi-Fi network found for bssid={bssid}.",
    )


def action_wifi_capture_pmkid(env: Environment, args: dict[str, Any]) -> Observation:
    bssid_arg = args.get("bssid")
    if not isinstance(bssid_arg, str) or not bssid_arg.strip():
        return Observation(
            capability="wifi.capture", action="pmkid",
            entities=[], raw_data={"bssid": bssid_arg},
            summary="Invalid or missing 'bssid' argument — PMKID capture aborted.",
        )
    bssid = bssid_arg.strip()
    for w in env.wifi:
        if w.bssid == bssid:
            if w.encryption not in _WPA_ENC:
                return Observation(
                    capability="wifi.capture", action="pmkid",
                    entities=[], raw_data={"bssid": bssid, "encryption": w.encryption},
                    summary=f"{w.ssid} ({bssid}) uses {w.encryption}; no PMKID to capture.",
                )
            # Prerequisite: a handshake must have been captured on THIS target.
            # Encoded by env.notes["wifi_handshake:<bssid>"], which simulators
            # hash via performed_capability_keys() -> "wifi.capture.handshake".
            if not w.handshake_captured:
                return Observation(
                    capability="wifi.capture", action="pmkid",
                    entities=[], raw_data={"bssid": bssid, "handshake_captured": False},
                    summary=f"No handshake captured on {w.ssid} ({bssid}); call wifi.capture.handshake first.",
                )
            w.pmkid_captured = True
            env.notes[f"wifi_pmkid:{bssid}"] = time.time()
            ent = Entity(
                id=w.bssid, type="wifi_network", label=w.ssid or "(hidden)",
                confidence=Confidence.CONFIRMED, attributes=w.to_dict(),
            )
            # Phase 2.7.6 — successful PMKID capture produces a durable
            # EvidenceRecord through the exact 2.7.5 pipeline (same
            # source_capability namespace, distinct kind). No fake raw
            # packet/blob data — the ID itself is the artifact handle, and
            # metadata stays deterministic + concise. Failure paths above
            # return early with `evidence=[]` (default); success REQUIRES the
            # per-target handshake prereq (checked above), so no evidence can
            # exist without a prior handshake capture on the SAME bssid.
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="wifi.capture",
                source_action="pmkid",
                # source_action_id is patched by the engine (simulator never
                # sees the ActionRequest) — same decoupling as Phase 2.7.5.
                target_entity_id=w.bssid,
                target_entity_type="wifi_network",
                kind="wifi_pmkid",
                summary=f"Captured PMKID ({w.encryption}) from {w.ssid} ({w.bssid}).",
                metadata={
                    "pmkid": True,
                    "encryption": w.encryption,
                    "ssid": w.ssid,
                    "bssid": w.bssid,
                    "channel": w.channel,
                    "handshake_prereq": True,
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="wifi.capture", action="pmkid",
                entities=[ent], raw_data=w.to_dict(),
                summary=f"Captured PMKID from {w.ssid} ({bssid}).",
                evidence=evidence,
            )
    return Observation(
        capability="wifi.capture", action="pmkid",
        entities=[], raw_data={"bssid": bssid},
        summary=f"No Wi-Fi network found for bssid={bssid}.",
    )


def action_ble_discover(env: Environment, args: dict[str, Any]) -> Observation:
    entities = _ble_entities(env)
    return Observation(
        capability="ble.discovery", action="discover",
        entities=entities, raw_data={"count": len(entities)},
        summary=f"Discovered {len(entities)} BLE device(s).",
    )


def action_ble_inspect(env: Environment, args: dict[str, Any]) -> Observation:
    addr = args.get("address", "")
    for b in env.ble:
        if b.address == addr:
            ent = Entity(
                id=b.address, type="ble_device", label=b.name or "(unnamed)",
                confidence=Confidence.CONFIRMED if b.connectable else Confidence.LIKELY,
                attributes=b.to_dict(),
            )
            state = "connected" if b.connected else "not connected"
            # Surface GATT state mutations in the summary (mirrors
            # wifi.discovery.inspect's capture-state suffix and
            # action_wifi_inspect's handshake/PMKID suffix). Back-compat:
            # freshly discovered / connected-without-writes devices still
            # produce the same summary as in Phase 2 / 2.7.
            parts: list[str] = []
            written = sum(1 for v in b.characteristics.values() if v)
            if written:
                parts.append(f"{written} characteristic(s) written")
            if b.paired:
                parts.append("paired")
            secure_written = sum(1 for v in b.secure_characteristics.values() if v)
            if secure_written:
                parts.append(f"{secure_written} secure characteristic(s) written")
            suffix = ("; " + "; ".join(parts)) if parts else ""
            return Observation(
                capability="ble.discovery", action="inspect",
                entities=[ent], raw_data=b.to_dict(),
                summary=f"Inspected BLE device {b.name} ({b.address}); {state}{suffix}.",
            )
    return Observation(
        capability="ble.discovery", action="inspect",
        entities=[], raw_data={"address": addr},
        summary=f"No BLE device found for address={addr}.",
    )


def action_ble_connect(env: Environment, args: dict[str, Any]) -> Observation:
    address = args.get("address")
    if not isinstance(address, str) or not address.strip():
        return Observation(
            capability="ble.discovery", action="connect",
            entities=[], raw_data={"address": address},
            summary="Invalid or missing 'address' argument — connect aborted.",
        )
    addr = address.strip()
    for b in env.ble:
        if b.address == addr:
            if not b.connectable:
                return Observation(
                    capability="ble.discovery", action="connect",
                    entities=[], raw_data={"address": addr, "connectable": False},
                    summary=f"BLE device {b.name} ({addr}) is not connectable.",
                )
            b.connected = True
            b.gatt_services = list(b.advertised_services) + ["generic_access"]
            b.characteristics = {svc: "" for svc in b.gatt_services}
            env.notes[f"ble_connected:{addr}"] = time.time()
            ent = Entity(
                id=b.address, type="ble_device", label=b.name or "(unnamed)",
                confidence=Confidence.CONFIRMED,
                attributes=b.to_dict(),
            )
            return Observation(
                capability="ble.discovery", action="connect",
                entities=[ent], raw_data=b.to_dict(),
                summary=f"Connected to {b.name} ({addr}); read {len(b.gatt_services)} GATT service(s).",
            )
    return Observation(
        capability="ble.discovery", action="connect",
        entities=[], raw_data={"address": addr},
        summary=f"No BLE device found for address={addr}.",
    )


def action_ble_write(env: Environment, args: dict[str, Any]) -> Observation:
    address = args.get("address")
    characteristic = args.get("characteristic")
    value = args.get("value")
    if not isinstance(address, str) or not address.strip():
        return Observation(
            capability="ble.discovery", action="write",
            entities=[], raw_data={"address": address},
            summary="Invalid or missing 'address' argument — write aborted.",
        )
    if not isinstance(characteristic, str) or not characteristic.strip():
        return Observation(
            capability="ble.discovery", action="write",
            entities=[], raw_data={"characteristic": characteristic},
            summary="Invalid or missing 'characteristic' argument — write aborted.",
        )
    if value is None:
        return Observation(
            capability="ble.discovery", action="write",
            entities=[], raw_data={"value": value},
            summary="Missing 'value' argument — write aborted.",
        )
    addr = address.strip()
    for b in env.ble:
        if b.address == addr:
            if not b.connected:
                return Observation(
                    capability="ble.discovery", action="write",
                    entities=[], raw_data={"address": addr, "connected": False},
                    summary=f"BLE device {b.name} ({addr}) is not connected; call ble.discovery.connect first.",
                )
            if characteristic not in b.gatt_services:
                return Observation(
                    capability="ble.discovery", action="write",
                    entities=[], raw_data={"characteristic": characteristic,
                                          "known": b.gatt_services},
                    summary=f"Unknown characteristic {characteristic!r} on {b.name} ({addr}).",
                )
            b.characteristics[characteristic] = str(value)
            env.notes[f"ble_write:{addr}:{characteristic}"] = time.time()
            ent = Entity(
                id=b.address, type="ble_device", label=b.name or "(unnamed)",
                confidence=Confidence.CONFIRMED,
                attributes=b.to_dict(),
            )
            return Observation(
                capability="ble.discovery", action="write",
                entities=[ent], raw_data=b.to_dict(),
                summary=f"Wrote value to characteristic {characteristic} on {b.name} ({addr}).",
            )
    return Observation(
        capability="ble.discovery", action="write",
        entities=[], raw_data={"address": addr},
        summary=f"No BLE device found for address={addr}.",
    )


# Phase 2.7.3 — stateful BLE GATT pairing/bonding lifecycle. The new
# `ble.gatt` namespace sits alongside `ble.discovery` exactly as `wifi.capture`
# sits alongside `wifi.discovery` (Phase 2.7.2): `ble.discovery.connect`/
# `ble.discovery.write` establish *link-level* GATT reads/writes; the new
# `ble.gatt.pair`/`ble.gatt.write` operate *on top of* the link — pairing is a
# session-establishing action (SAFE_ACTIVE) requiring `ble.discovery.connect`
# first; `ble.gatt.write` is the encrypted state-changing operation
# (SENSITIVE_ACTIVE) that requires `ble.gatt.pair` on the SAME address first
# (per-target prereq, exactly parallel to wifi.capture.pmkid needing a
# handshake on the SAME bssid).

def action_ble_gatt_pair(env: Environment, args: dict[str, Any]) -> Observation:
    address = args.get("address")
    if not isinstance(address, str) or not address.strip():
        return Observation(
            capability="ble.gatt", action="pair",
            entities=[], raw_data={"address": address},
            summary="Invalid or missing 'address' argument — pair aborted.",
        )
    addr = address.strip()
    for b in env.ble:
        if b.address == addr:
            if not b.connectable:
                return Observation(
                    capability="ble.gatt", action="pair",
                    entities=[], raw_data={"address": addr, "connectable": False},
                    summary=f"BLE device {b.name} ({addr}) is not connectable.",
                )
            # Per-target prereq: ble.discovery.connect (link establishment)
            # must have run against THIS address first. Catalogue-level
            # `requires=("ble.discovery.connect",)` only proves "some connect
            # ran somewhere"; the simulator enforces the same-device gate
            # (parallel to wifi.capture.pmkid needing a handshake on the
            # same bssid).
            if not b.connected:
                return Observation(
                    capability="ble.gatt", action="pair",
                    entities=[], raw_data={"address": addr, "connected": False},
                    summary=f"BLE device {b.name} ({addr}) is not connected; call ble.discovery.connect first.",
                )
            b.paired = True
            b.secure_characteristics = {svc: "" for svc in b.gatt_services}
            env.notes[f"ble_paired:{addr}"] = time.time()
            ent = Entity(
                id=b.address, type="ble_device", label=b.name or "(unnamed)",
                confidence=Confidence.CONFIRMED,
                attributes=b.to_dict(),
            )
            # Phase 2.7.7 — successful pairing produces a durable EvidenceRecord
            # (kind "ble_pairing") through the exact 2.7.5/2.7.6 pipeline. Prereq
            # (connect on the SAME address) was enforced above, so pairing
            # evidence only exists after successful pairing. No fake protocol
            # blobs — metadata is concise/deterministic/realistic.
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="ble.gatt",
                source_action="pair",
                # source_action_id is patched by the engine (simulator never
                # sees the ActionRequest) — same decoupling as Phase 2.7.5.
                target_entity_id=b.address,
                target_entity_type="ble_device",
                kind="ble_pairing",
                summary=f"Paired with {b.name} ({b.address}).",
                metadata={
                    "address": b.address,
                    "device_name": b.name,
                    "connectable": b.connectable,
                    "secure_service_count": len(b.secure_characteristics),
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="ble.gatt", action="pair",
                entities=[ent], raw_data=b.to_dict(),
                summary=(
                    f"Paired with {b.name} ({addr}); "
                    f"{len(b.secure_characteristics)} secure GATT characteristic slot(s) ready."
                ),
                evidence=evidence,
            )
    return Observation(
        capability="ble.gatt", action="pair",
        entities=[], raw_data={"address": addr},
        summary=f"No BLE device found for address={addr}.",
    )


def action_ble_gatt_write(env: Environment, args: dict[str, Any]) -> Observation:
    address = args.get("address")
    characteristic = args.get("characteristic")
    value = args.get("value")
    if not isinstance(address, str) or not address.strip():
        return Observation(
            capability="ble.gatt", action="write",
            entities=[], raw_data={"address": address},
            summary="Invalid or missing 'address' argument — secure write aborted.",
        )
    if not isinstance(characteristic, str) or not characteristic.strip():
        return Observation(
            capability="ble.gatt", action="write",
            entities=[], raw_data={"characteristic": characteristic},
            summary="Invalid or missing 'characteristic' argument — secure write aborted.",
        )
    if value is None:
        return Observation(
            capability="ble.gatt", action="write",
            entities=[], raw_data={"value": value},
            summary="Missing 'value' argument — secure write aborted.",
        )
    addr = address.strip()
    for b in env.ble:
        if b.address == addr:
            if not b.paired:
                return Observation(
                    capability="ble.gatt", action="write",
                    entities=[], raw_data={"address": addr, "paired": False},
                    summary=f"BLE device {b.name} ({addr}) is not paired; call ble.gatt.pair first.",
                )
            if characteristic not in b.gatt_services:
                return Observation(
                    capability="ble.gatt", action="write",
                    entities=[], raw_data={"characteristic": characteristic,
                                          "known": b.gatt_services},
                    summary=f"Unknown characteristic {characteristic!r} on {b.name} ({addr}).",
                )
            b.secure_characteristics[characteristic] = str(value)
            env.notes[f"ble_secure_write:{addr}:{characteristic}"] = time.time()
            ent = Entity(
                id=b.address, type="ble_device", label=b.name or "(unnamed)",
                confidence=Confidence.CONFIRMED,
                attributes=b.to_dict(),
            )
            # Phase 2.7.7 — successful secure write produces a durable
            # EvidenceRecord (kind "ble_secure_write"). The pairing prereq
            # (b.paired=True on the SAME address) was enforced above, so
            # secure-write evidence only exists after that prerequisite is
            # satisfied. No fake protocol blobs — concise deterministic
            # metadata. All failure paths return early with `evidence=[]`.
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="ble.gatt",
                source_action="write",
                # source_action_id is patched by the engine (simulator never
                # sees the ActionRequest) — same decoupling as Phase 2.7.5.
                target_entity_id=b.address,
                target_entity_type="ble_device",
                kind="ble_secure_write",
                summary=f"Wrote secure value to characteristic {characteristic} on {b.name} ({b.address}).",
                metadata={
                    "address": b.address,
                    "device_name": b.name,
                    "characteristic": characteristic,
                    "value": str(value),
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="ble.gatt", action="write",
                entities=[ent], raw_data=b.to_dict(),
                summary=f"Wrote secure value to characteristic {characteristic} on {b.name} ({addr}).",
                evidence=evidence,
            )
    return Observation(
        capability="ble.gatt", action="write",
        entities=[], raw_data={"address": addr},
        summary=f"No BLE device found for address={addr}.",
    )


def action_nfc_scan(env: Environment, args: dict[str, Any]) -> Observation:
    entities = _nfc_entities(env)
    return Observation(
        capability="nfc.discovery", action="scan",
        entities=entities, raw_data={"count": len(entities)},
        summary=f"Scanned {len(entities)} NFC tag(s).",
    )


def action_nfc_select(env: Environment, args: dict[str, Any]) -> Observation:
    """Phase 2.8.2 — identify + activate a known NFC/RFID tag.

    PN532-equivalent InListPassiveTarget + Activate. NOT a read; it
    validates the tag UID exists and flips `NfcTag.selected=True`. The
    per-target prereq for `nfc.discovery.read` is `t.selected=True` on the
    SAME uid — exactly mirrors `subghz.discovery.analyze` requiring
    `SubGhzSignal.captured=True` on the same frequency. Failures (unknown
    uid, malformed args) return structured Observations with no env mutation.
    Produces no evidence (it is a discovery step, not a capture).
    """
    uid = args.get("uid", "")
    if not isinstance(uid, str) or not uid:
        return Observation(
            capability="nfc.discovery", action="select",
            entities=[], raw_data={"uid": uid},
            summary="Invalid or missing uid argument — select aborted.",
        )
    for t in env.nfc:
        if t.uid == uid:
            t.selected = True
            # Phase 2.8.2: stateful action stamps notes so
            # performed_capability_keys(env) reflects the select and
            # Capability.prerequisites_met can answer "is this tag selected?".
            env.notes[f"nfc_select:{uid}"] = time.time()
            ent = Entity(
                id=t.uid, type="nfc_tag",
                label=f"NFC {t.tag_type} {t.uid[-5:]}",
                confidence=Confidence.CONFIRMED,
                attributes={
                    **t.to_dict(),
                    "selected": True,
                },
            )
            return Observation(
                capability="nfc.discovery", action="select",
                entities=[ent],
                raw_data={"uid": uid, "tag_type": t.tag_type,
                          "ndef_supported": t.ndef_supported},
                summary=f"Selected NFC {t.tag_type} tag {uid}.",
            )
    return Observation(
        capability="nfc.discovery", action="select",
        entities=[], raw_data={"uid": uid},
        summary=f"No NFC tag found for uid={uid}.",
    )


def action_nfc_read(env: Environment, args: dict[str, Any]) -> Observation:
    """Phase 2.8.2 — read NDEF records from a previously-selected tag.

    Per-target prereq: `t.selected=True` on the SAME uid (set by
    `nfc.discovery.select`). Tags with `ndef_supported=False` are rejected
    with a structured failure Observation (clean representation of a
    read-only / proprietary-memory-layout tag). Success produces exactly one
    `nfc_read` `EvidenceRecord` with concise deterministic metadata (uid,
    tag_type, technology, records_count, ndef_supported) — NO fake raw
    dumps / byte blobs. All failure paths return `evidence=[]` with no env
    mutation.
    """
    uid = args.get("uid", "")
    if not isinstance(uid, str) or not uid:
        return Observation(
            capability="nfc.discovery", action="read",
            entities=[], raw_data={"uid": uid},
            summary="Invalid or missing uid argument — read aborted.",
            evidence=[],
        )
    for t in env.nfc:
        if t.uid == uid:
            if not t.selected:
                return Observation(
                    capability="nfc.discovery", action="read",
                    entities=[], raw_data={"uid": uid},
                    summary=(
                        f"Tag {uid} has not been selected — "
                        "run nfc.discovery.select on the same uid first."
                    ),
                    evidence=[],
                )
            if not t.ndef_supported:
                ent = Entity(
                    id=t.uid, type="nfc_tag",
                    label=f"NFC {t.tag_type} {t.uid[-5:]}",
                    confidence=Confidence.CONFIRMED,
                    attributes={**t.to_dict(), "read_status": "ndef_unsupported"},
                )
                return Observation(
                    capability="nfc.discovery", action="read",
                    entities=[ent], raw_data={"uid": uid},
                    summary=(
                        f"Tag {uid} ({t.tag_type}) does not expose NDEF — "
                        "read aborted (proprietary memory layout)."
                    ),
                    evidence=[],
                )
            t.read = True
            t.read_at = time.time()
            env.notes[f"nfc_read:{uid}"] = t.read_at
            ent = Entity(
                id=t.uid, type="nfc_tag",
                label=f"NFC {t.tag_type} {t.uid[-5:]}",
                confidence=Confidence.CONFIRMED,
                attributes={
                    **t.to_dict(),
                    "read": True,
                    "records_count": len(t.ndef_records),
                    "read_status": "ok",
                },
            )
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="nfc.discovery",
                source_action="read",
                target_entity_id=t.uid,
                target_entity_type="nfc_tag",
                kind="nfc_read",
                summary=(
                    f"Read {len(t.ndef_records)} NDEF record(s) from "
                    f"{t.tag_type} tag {uid}."
                ),
                metadata={
                    "uid": t.uid,
                    "tag_type": t.tag_type,
                    "technology": "NFC",
                    "ndef_supported": t.ndef_supported,
                    "records_count": len(t.ndef_records),
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="nfc.discovery", action="read",
                entities=[ent],
                raw_data={"uid": uid, "records": t.ndef_records},
                summary=f"Read {len(t.ndef_records)} NDEF record(s) from tag {uid}.",
                evidence=evidence,
            )
    return Observation(
        capability="nfc.discovery", action="read",
        entities=[], raw_data={"uid": uid},
        summary=f"No NFC tag found for uid={uid}.",
        evidence=[],
    )


def action_subghz_spectrum(env: Environment, args: dict[str, Any]) -> Observation:
    entities = _subghz_entities(env)
    return Observation(
        capability="subghz.discovery", action="spectrum",
        entities=entities, raw_data={"count": len(entities)},
        summary=f"Spectrum scan returned {len(entities)} signal(s).",
    )


# Phase 2.8.1 — heuristic label for a captured Sub-GHz signal, derived from
# (frequency, modulation). This is NOT a real signal decoder: the simulator
# has no payloads to decode. It returns a deterministic best-guess label
# based on common Sub-GHz device-class knowledge so the evidence metadata
# carries something more useful than "unclassified". Tests assert this is a
# `_hint`, not a decoded value.
def _subghz_protocol_hint(s: SubGhzSignal) -> str:
    key = (round(s.frequency_mhz, 2), s.modulation)
    return {
        (433.92, "OOK"): "remote_control",      # garage-door / PR12-style remotes
        (433.92, "ASK"): "ISM_remote",
        (315.00, "OOK"): "car_remote",
        (868.30, "FSK"): "LoRa_like",
        (915.00, "FSK"): "ISM_IoT",
    }.get(key, "unknown")


def _subghz_capture_quality(rssi: int) -> str:
    """Derive a deterministic capture-quality label from signal strength.
    No RNG — the lab scenario's rssi values map to fixed labels so the same
    seed yields the same evidence metadata."""
    if rssi >= -60:
        return "clean"
    if rssi >= -70:
        return "partial"
    return "noisy"


def action_subghz_capture_signal(env: Environment, args: dict[str, Any]) -> Observation:
    try:
        freq = float(args.get("frequency_mhz", 0.0))
    except (TypeError, ValueError):
        return Observation(
            capability="subghz.capture", action="signal",
            entities=[], raw_data={"frequency_mhz": args.get("frequency_mhz")},
            summary="Invalid frequency_mhz argument — capture aborted.",
        )
    for s in env.subghz:
        if abs(s.frequency_mhz - freq) < 0.01:
            if not s.captured:
                s.captured = True
                s.sample_count = 1024
                s.capture_quality = _subghz_capture_quality(s.rssi)
            env.notes[f"subghz_capture:{s.frequency_mhz:.3f}"] = time.time()
            ent = Entity(
                id=f"{s.frequency_mhz:.3f}MHz-{s.modulation}",
                type="subghz_signal",
                label=f"{s.frequency_mhz:.2f} MHz {s.modulation}",
                confidence=Confidence.CONFIRMED,
                attributes=s.to_dict(),
            )
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="subghz.capture",
                source_action="signal",
                target_entity_id=ent.id,
                target_entity_type="subghz_signal",
                kind="subghz_capture",
                summary=(
                    f"Captured {s.sample_count} samples of {s.modulation} signal "
                    f"at {s.frequency_mhz:.2f} MHz ({s.capture_quality})."
                ),
                metadata={
                    "frequency_mhz": s.frequency_mhz,
                    "modulation": s.modulation,
                    "bandwidth_khz": s.bandwidth_khz,
                    "rssi": s.rssi,
                    "sample_count": s.sample_count,
                    "capture_quality": s.capture_quality,
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="subghz.capture", action="signal",
                entities=[ent], raw_data=s.to_dict(),
                summary=(
                    f"Captured {s.sample_count} samples of {s.modulation} signal "
                    f"at {s.frequency_mhz:.2f} MHz ({s.capture_quality})."
                ),
                evidence=evidence,
            )
    return Observation(
        capability="subghz.capture", action="signal",
        entities=[], raw_data={"frequency_mhz": freq},
        summary=f"No signal found at frequency {freq} MHz.",
    )


def action_subghz_analyze(env: Environment, args: dict[str, Any]) -> Observation:
    try:
        freq = float(args.get("frequency_mhz", 0.0))
    except (TypeError, ValueError):
        return Observation(
            capability="subghz.discovery", action="analyze",
            entities=[], raw_data={"frequency_mhz": args.get("frequency_mhz")},
            summary="Invalid frequency_mhz argument — nothing analyzed.",
        )
    for s in env.subghz:
        if abs(s.frequency_mhz - freq) < 0.01:
            # Phase 2.8.1 — per-target prereq: the signal must have been
            # captured by `subghz.capture.signal` on the SAME frequency
            # before analyze can produce evidence or stamp env.notes. This
            # mirrors wifi.capture.pmkid requiring handshake_captured=True
            # on the SAME bssid (catalogue-level `requires` answers the
            # planner's "did some capture run somewhere?"; the handler gate
            # answers the operator's "is precisely THIS target ready?"). The
            # empty-evidence path keeps the action runnable (the run does not
            # fail) but produces nothing and leaves env state untouched.
            if not s.captured:
                return Observation(
                    capability="subghz.discovery", action="analyze",
                    entities=[], raw_data={"frequency_mhz": freq, "captured": False},
                    summary=(
                        f"Signal at {s.frequency_mhz:.2f} MHz not captured; "
                        f"call subghz.capture.signal first."
                    ),
                )
            # Decode hint (NOT a true decode — the simulator has no payload).
            if not s.decoded_protocol_hint:
                s.decoded_protocol_hint = _subghz_protocol_hint(s)
            env.notes[f"subghz_analyzed:{s.frequency_mhz:.3f}"] = time.time()
            classification = _classify_subghz(s)
            ent = Entity(
                id=f"{s.frequency_mhz:.3f}MHz-{s.modulation}",
                type="subghz_signal",
                label=f"{s.frequency_mhz:.2f} MHz {s.modulation}",
                confidence=Confidence.LIKELY,
                attributes={
                    **s.to_dict(),
                    "analyzed": True,
                    "classification": classification,
                },
            )
            captured_at = time.time()
            evidence = [EvidenceRecord(
                source_capability="subghz.discovery",
                source_action="analyze",
                target_entity_id=ent.id,
                target_entity_type="subghz_signal",
                kind="subghz_analysis",
                summary=f"Analyzed captured signal at {s.frequency_mhz:.2f} MHz: {classification}.",
                metadata={
                    "frequency_mhz": s.frequency_mhz,
                    "modulation": s.modulation,
                    "classification": classification,
                    "decoded_protocol_hint": s.decoded_protocol_hint,
                    "capture_prereq": True,
                },
                captured_at=captured_at,
            )]
            return Observation(
                capability="subghz.discovery", action="analyze",
                entities=[ent], raw_data=s.to_dict(),
                summary=f"Analyzed signal at {s.frequency_mhz:.2f} MHz.",
                evidence=evidence,
            )
    return Observation(
        capability="subghz.discovery", action="analyze",
        entities=[], raw_data={"frequency_mhz": freq},
        summary=f"No signal found at frequency {freq} MHz.",
    )


def _classify_subghz(s: SubGhzSignal) -> str:
    """Trivial classifier used for the analyze action."""
    if s.frequency_mhz == 433.92 and s.modulation == "OOK":
        return "likely ISM-band remote control / sensor"
    if s.frequency_mhz in (868.30, 915.00) and s.modulation == "FSK":
        return "likely LoRa / sub-GHz IoT"
    return "unclassified"


# ── Dispatcher ────────────────────────────────────────────────────────────────

HANDLERS = {
    ("wifi.discovery", "discover"):   action_wifi_discover,
    ("wifi.discovery", "inspect"):    action_wifi_inspect,
    ("wifi.capture",   "handshake"):  action_wifi_capture_handshake,
    ("wifi.capture",   "pmkid"):      action_wifi_capture_pmkid,
    ("ble.discovery",  "discover"):   action_ble_discover,
    ("ble.discovery",  "inspect"):    action_ble_inspect,
    ("ble.discovery",  "connect"):    action_ble_connect,
    ("ble.discovery",  "write"):      action_ble_write,
    ("ble.gatt",       "pair"):       action_ble_gatt_pair,
    ("ble.gatt",       "write"):      action_ble_gatt_write,
    ("nfc.discovery",  "scan"):       action_nfc_scan,
    ("nfc.discovery",  "select"):     action_nfc_select,  # Phase 2.8.2
    ("nfc.discovery",  "read"):       action_nfc_read,
    ("subghz.discovery", "spectrum"): action_subghz_spectrum,
    ("subghz.discovery", "analyze"):  action_subghz_analyze,
    ("subghz.capture",   "signal"):   action_subghz_capture_signal,
}


# Phase 2.7.1 — performed-capability mapping. Each state-changing simulator
# action already leaves a stamped `env.notes` entry (see action_ble_connect,
# action_ble_write, action_nfc_read, action_subghz_analyze). Translating those
# note prefixes back into capability keys lets a dependency-aware consumer
# ask "is capability X ready to run?" against the live env, which is what
# `Capability.prerequisites_met(observed_keys)` consumes. Pure descriptor —
# reads env.notes, never mutates them; passive actions (discover/inspect/scan/
# spectrum) intentionally leave no notes entry because they do not mutate env.
_NOTE_PREFIX_TO_CAPABILITY_KEY: dict[str, str] = {
    "ble_connected:":     "ble.discovery.connect",
    "ble_write:":         "ble.discovery.write",
    "nfc_select:":        "nfc.discovery.select",  # Phase 2.8.2
    "nfc_read:":          "nfc.discovery.read",
    "subghz_analyzed:":   "subghz.discovery.analyze",
    "subghz_capture:":    "subghz.capture.signal",
    "wifi_handshake:":    "wifi.capture.handshake",
    "wifi_pmkid:":        "wifi.capture.pmkid",
    "ble_paired:":        "ble.gatt.pair",
    "ble_secure_write:":  "ble.gatt.write",
}


def performed_capability_keys(env: Environment) -> set[str]:
    """Return the set of capability keys that have been performed on `env`,
    derived from the prefixes the state-changing action handlers stamp into
    `env.notes`. Unknown prefixes are ignored (forward-compat with future
    domains that may also stamp notes). Empty set when nothing has run yet —
    the standard state of a fresh scenario env.
    """
    out: set[str] = set()
    for note_key in env.notes.keys():
        if not isinstance(note_key, str):
            continue
        for prefix, cap_key in _NOTE_PREFIX_TO_CAPABILITY_KEY.items():
            if note_key.startswith(prefix):
                out.add(cap_key)
                break
    return out


def execute(env: Environment, capability: str, action: str,
            args: Optional[dict[str, Any]] = None) -> Observation:
    """Execute a capability action against the simulator environment."""
    handler = HANDLERS.get((capability, action))
    if handler is None:
        return Observation(
            capability=capability, action=action,
            entities=[], raw_data={"args": args or {}},
            summary=f"Simulator has no handler for {capability}.{action}.",
        )
    return handler(env, args or {})
