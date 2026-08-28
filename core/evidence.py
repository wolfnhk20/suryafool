"""
core/evidence.py

Structured evidence record — the durable output of a capability that captures
artifacts (e.g. `wifi.capture.handshake` produces an EAPOL-frame evidence
record). Distinct from `Observation`, `Finding`, vulnerability hypothesis,
and confirmed finding; an `EvidenceRecord` carries the provenance that lets
a later consumer ask "what evidence did this action produce, and where did
it come from?".

Phase 2.7.5 establishes ONE clean vertical slice: `wifi.capture.handshake`
is the sole producer. Phase 2.7.6 generalizes the slice to
`wifi.capture.pmkid` within the SAME wifi.capture domain. Phase 2.7.7
generalizes it across domains to the BLE GATT session operations:
`ble.gatt.pair` (kind `ble_pairing`) and `ble.gatt.write` (kind
`ble_secure_write`) — the pipeline is unchanged, only the producing
handlers and their kinds differ. Phase 2.8.1 extends the pipeline to Sub-GHz:
`subghz.capture.signal` (kind `subghz_capture`) and the existing
`subghz.discovery.analyze` upgraded to produce `subghz_analysis` when run
against a captured target (per-target prereq, same pipeline). Phase 2.8.2
extends the pipeline to NFC: the NEW `nfc.discovery.select` activates a
known tag, and the existing `nfc.discovery.read` is upgraded to produce
`nfc_read` evidence when run against a selected tag (per-target prereq, same
pipeline). Phase 2.8.3 extends the pipeline to Infrared: the existing
`infrared.analyze` is upgraded to produce `ir_analysis` evidence when run
against a known capture_id, and `infrared.transmit` produces `ir_transmit`
evidence when replayed against an ANALYZED capture_id (per-target prereq,
same pipeline). Camera / ethernet / usb evidence stays out of scope until
2.8.4+.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


# Open vocabulary of evidence kinds. The frozenset is a vocabulary hint (not
# enforced) so future phases can add kinds without changing the dataclass.
# Mirrors the KNOWN_DOMAINS pattern from capabilities/base.py.
KNOWN_EVIDENCE_KINDS: frozenset[str] = frozenset({
    "wifi_eapol_handshake",   # produced by wifi.capture.handshake  (Phase 2.7.5)
    "wifi_pmkid",             # produced by wifi.capture.pmkid     (Phase 2.7.6)
    "ble_pairing",            # produced by ble.gatt.pair          (Phase 2.7.7)
    "ble_secure_write",       # produced by ble.gatt.write         (Phase 2.7.7)
    "subghz_capture",         # produced by subghz.capture.signal  (Phase 2.8.1)
    "subghz_analysis",        # produced by subghz.discovery.analyze (Phase 2.8.1, when capture prereq met)
    "nfc_read",               # produced by nfc.discovery.read       (Phase 2.8.2, when select prereq met)
    "ir_analysis",            # produced by infrared.analyze         (Phase 2.8.3, when capture_id known)
    "ir_transmit",            # produced by infrared.transmit        (Phase 2.8.3, when analyze prereq met)
})


@dataclass
class EvidenceRecord:
    """A single piece of evidence captured by a capability action.

    Provenance fields:
      id                 — this record's own UUID (run-local unique)
      source_action_id   — ActionRequest.id that produced it
      source_capability  — e.g. "wifi.capture"
      source_action      — e.g. "handshake"
      target_entity_id   — the entity the evidence is about (e.g. bssid)
      target_entity_type — Entity.type of the target (e.g. "wifi_network")
      kind               — evidence kind (see KNOWN_EVIDENCE_KINDS);
                           distinguishes this from observation / indicator /
                           vulnerability hypothesis / confirmed finding
      summary            — concise human-readable summary
      metadata           — deterministic structured fields (frame_count,
                           encryption, ssid, bssid, ...). No giant fake
                           packet blobs — realistic metadata only.
      captured_at        — timestamp (the run model carries timestamps
                           natively; no separate sequence counter)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_action_id: str = ""
    source_capability: str = ""
    source_action: str = ""
    target_entity_id: str = ""
    target_entity_type: str = ""
    kind: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "EvidenceRecord":
        return EvidenceRecord(**dict(d))
