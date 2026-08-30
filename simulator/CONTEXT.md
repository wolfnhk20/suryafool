# CONTEXT.md — simulator/

> **For AI coding assistants:** Phase 2 wireless environment simulator.
> Read [`AGENTS.md`](../AGENTS.md) before making changes.

---

## Purpose

A deterministic, seedable simulation of a wireless environment (Wi-Fi, BLE,
NFC/RFID, Sub-GHz) so the full mission loop can run end-to-end without
real hardware.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Package marker |
| `rng.py` | ✅ Done | `SeededRNG` — deterministic `random.Random(seed)` wrapper |
| `entities.py` | ✅ Done | `WifiNetwork`, `BleDevice`, `NfcTag`, `SubGhzSignal` dataclasses |
| `environment.py` | ✅ Done | `Environment` — mutable container of all entities + notes |
| `scenarios.py` | ✅ Done | `scenario_home`, `scenario_lab`, `scenario_crowded` builders |
| `simulator.py` | ✅ Done | `execute(env, capability, action, args)` → `Observation` + `HANDLERS` |

---

## Scenarios

| Name | Description |
|---|---|
| `home` | Quiet residential environment |
| `lab` | Authorized Suryafool test lab with labeled targets |
| `crowded` | Dense urban/coworking RF environment |

Same seed → identical environment every time.

## Action surface

| Capability | Actions |
|---|---|
| `wifi.discovery` | `discover`, `inspect` (summary surfaces captured state when present) |
| `wifi.capture` | `handshake` (SAFE_ACTIVE, mutates `WifiNetwork.handshake_captured`+`captured_frames`), `pmkid` (SENSITIVE_ACTIVE, mutates `WifiNetwork.pmkid_captured`; per-target prereq — requires preceding `wifi.capture.handshake` on the SAME bssid) |
| `ble.discovery` | `discover`, `inspect` (summary surfaces paired + secure-write state when present), `connect` (Phase 2.7 SAFE_ACTIVE — link-layer connect + caches `gatt_services` + inits `characteristics`), `write` (Phase 2.7 SENSITIVE_ACTIVE — unauthenticated characteristic write) |
| `ble.gatt` | `pair` (Phase 2.7.3 SAFE_ACTIVE — establishes pairing/bonding on a connected device; per-target prereq `b.connected=True`; mutates `BleDevice.paired`+`secure_characteristics`), `write` (Phase 2.7.3 SENSITIVE_ACTIVE — encrypted characteristic write within the paired session; per-target prereq `b.paired=True`; mutates `BleDevice.secure_characteristics[char]`) |
| `nfc.discovery` | `scan`, `read` (one-shot, marks env state), `select` (Phase 2.8.2 PASSIVE — activates a tag for reading; mutates `NfcTag.selected`) |
| `subghz.discovery` | `spectrum`, `analyze` (Phase 2.8.1: `analyze` now requires a preceding `capture` on the SAME frequency — sets `decoded_protocol_hint` + emits `subghz_analysis` evidence on success; prereq-missing failure on uncaptured targets) |
| `subghz.capture` | `signal` (Phase 2.8.1 SAFE_ACTIVE — captures an RF sample at a known frequency; mutates `SubGhzSignal.captured/sample_count/capture_quality`; emits `subghz_capture` evidence) |
| `infrared` | `capture` (PASSIVE-observational — samples an `IrSignal`; no notes, no evidence), `analyze` (Phase 2.8.3 SAFE_ACTIVE — recognizes the captured signal; per-target capture_id prereq; sets `protocol_hint` + `ir_classification`; emits `ir_analysis` evidence), `transmit` (Phase 2.8.3 SENSITIVE_ACTIVE — replays a previously analyzed signal; per-target SAME-capture_id analyzed=True prereq; sets `transmitted=True`; emits `ir_transmit` evidence) |
| `zigbee.discovery` | `scan` (Phase 2.8.4 PASSIVE — lists Zigbee PANs; `node_count` recomputed LIVE from joined nodes so a re-scan reflects a join), `inspect` (Phase 2.8.4 PASSIVE — per-PAN node list + mesh topology via `parent_short_address`), `join` (Phase 2.8.4 SAFE_ACTIVE — authorizes an unjoined end-device onto a PAN; per-target gates network-exists + node-exists + not-already-joined; assigns next short `0x0003`, parent first-router-else-coordinator `0x0001`, `lqi=220`, `joined=True`; stamps `env.notes["zigbee_joined:<ieee>"]`; emits `zigbee_join` evidence) |

`wifi.capture.*` validate that the target network is WPA-encrypted
(`WPA2`/`WPA3`); `OPEN`/`WEP` returns a structured failure Observation
(no mutation). The `wifi.capture` namespace mirrors Risinek's
capture-vs-discovery separation: discovery reads, capture mutates.

`ble.gatt.*` layer on top of the legacy Phase 2.7 `ble.discovery.connect`
link-layer step — pairing presupposes a connected link; the secure write
presupposes a paired session. Both per-target gates are enforced strictly
by the handlers (the catalogue-level `requires` only proves "some connect /
some pair ran somewhere"); an unknown address / not-connectable device /
unconnected target / unpaired target / unknown characteristic / `None`
value all return structured failure Observations with no env mutation.

## Rules

- No LLM, no randomness without a seed.
- Actions return structured `Observation` objects — never raw strings.
- The simulator never decides *what to do* — the run engine does.

---

## Phase 2.7.1 — `performed_capability_keys(env)`

A pure helper added alongside the dispatcher:
`performed_capability_keys(env: Environment) -> set[str]` reads the
`env.notes` keys that the **state-changing** action handlers already stamp
and translates their prefixes back into capability keys:

| `env.notes` prefix | Capability key |
|---|---|
| `ble_connected:` | `ble.discovery.connect` |
| `ble_write:` | `ble.discovery.write` |
| `nfc_read:` | `nfc.discovery.read` |
| `subghz_analyzed:` | `subghz.discovery.analyze` |
| `wifi_handshake:` | `wifi.capture.handshake` |
| `wifi_pmkid:` | `wifi.capture.pmkid` |
| `ble_paired:` | `ble.gatt.pair` |
| `ble_secure_write:` | `ble.gatt.write` |
| `subghz_capture:` | `subghz.capture.signal` (Phase 2.8.1) |
| `ir_analyzed:` | `infrared.analyze` (Phase 2.8.3) |
| `ir_transmit:` | `infrared.transmit` (Phase 2.8.3) |
| `zigbee_joined:` | `zigbee.discovery.join` (Phase 2.8.4) |

This is the smallest simulator support needed to prove the Phase 2.7.1
`Capability.requires` / `prerequisites_met` metadata is actually usable:
feed `performed_capability_keys(env)` into
`Capability.prerequisites_met(observed_keys)` from
[`capabilities/base.py`](../capabilities/base.py) and you get the answer to
"is capability X now ready to run against this env?" without a new
mission-state machine. It is a pure descriptor — it reads `env.notes`, never
mutates them. Passive actions (`discover`, `inspect`, `scan`, `spectrum`)
intentionally leave no `env.notes` entry, so they never appear in the
returned set — the stateful-vs-observational distinction is preserved.
Unknown note prefixes are ignored (forward-compat with future domains).

---

## Phase 2.8.0 — multi-domain substrate (no handlers yet)

The three remaining domains get their ENTITY + ENVIRONMENT representation
only — pure data, NO simulator handlers, NO fake functionality:

| Entity | `Environment` field | `snapshot()` key |
|---|---|---|
| `IrSignal` (`capture_id`, `carrier_khz`, `length_ms`, `protocol`) | `ir` | `ir` |
| `EthernetHost` (`mac`, `ip`, `hostname`, `vendor_hint`) | `ethernet` | `ethernet` |
| `UsbDevice` (`path`, `vid`, `pid`, `manufacturer`, `product`) | `usb` | `usb` |

All three are `to_dict()` typed views exactly like `WifiNetwork` /
`BleDevice` / `NfcTag` / `SubGhzSignal`. `Environment` defaults the three
lists to empty and `snapshot()` serializes them (fresh scenarios have empty
`ir`/`ethernet`/`usb`). The catalogue entries for these domains are
registered but `HANDLERS` deliberately does NOT include them — they resolve
`supported=False` and the unchanged policy gate REJECTs them before the
provider ("don't pretend it works"). `performed_capability_keys` needs no
`_NOTE_PREFIX_TO_CAPABILITY_KEY` additions — no handler stamps notes yet.
Scenarios stay unpopulated (for ethernet/usb); 2.8.3 adds IR handlers +
scenario content (lab) on this substrate, and 2.8.4/2.8.5 add ethernet/usb
handlers.

---

## Phase 2.8.1 — Sub-GHz/RF stateful capture + analyze

`SubGhzSignal` gains four stateful fields used by the new capture handler +
upgraded analyze handler:

| Field | Type | Default | Set by |
|---|---|---|---|
| `captured` | `bool` | `False` | `subghz.capture.signal` success |
| `sample_count` | `int` | `0` | `subghz.capture.signal` success (fixed `1024` — deterministic, no RNG) |
| `capture_quality` | `str` | `""` | `subghz.capture.signal` success (rssi-derived: `≥-60`→`"clean"`, `≥-70`→`"partial"`, else `"noisy"`) |
| `decoded_protocol_hint` | `str` | `""` | `subghz.discovery.analyze` success on a captured target |

Two handlers change:

### `action_subghz_capture_signal` (new, SAFE_ACTIVE, produces `subghz_capture` evidence)

Validates `frequency_mhz` is a known lab frequency (433.92 / 868.30 / 915.00 /
315.00 — the seeded scenarios' values); unknown frequency or malformed args
return a structured failure Observation with `evidence=[]` and no env
mutation. On success, sets `SubGhzSignal.captured=True` +
`sample_count=1024` + `capture_quality` (rssi-derived), stamps
`env.notes["subghz_capture:<frequency>"]`, and builds one `subghz_capture`
`EvidenceRecord` with concise metadata (`frequency_mhz`, `modulation`,
`rssi_dbm`, `sample_count`, `capture_quality`). All failure paths produce
zero evidence.

### `action_subghz_analyze` (upgraded — `produces_evidence` False→True)

The handler now REQUIRES `SubGhzSignal.captured=True` on the SAME frequency
before it succeeds — a per-target gate exactly parallel to
`wifi.capture.pmkid`'s same-bssid handshake prereq. An uncaptured target
returns a prereq-missing failure Observation with `evidence=[]` and no
`env.notes` stamp (some historical calls that did `analyze` without a prior
`spectrum` will see this new structured failure — mission-mandated behavior).
On success, the handler sets a deterministic `decoded_protocol_hint` via the
`_subghz_protocol_hint` heuristic map:

| (frequency_mhz, modulation) | hint |
|---|---|
| `(433.92, "OOK")` | `remote_control` |
| `(433.92, "ASK")` | `ISM_remote` |
| `(315.00, "OOK")` | `car_remote` |
| `(868.30, "FSK")` | `LoRa_like` |
| `(915.00, "FSK")` | `ISM_IoT` |
| anything else | `unknown` |

`decoded_protocol_hint` is a HINT, NOT a decoder — the simulator has no
signal payloads and no real protocol parser; the field name ends in `_hint`
to make that explicit. The handler builds one `subghz_analysis`
`EvidenceRecord` with concise metadata (`frequency_mhz`, `modulation`,
`rssi_dbm`, `decoded_protocol_hint`, `sample_count_prereq`); failure paths
return zero evidence.

The `_NOTE_PREFIX_TO_CAPABILITY_KEY` mapping gains `subghz_capture:`
`→` `subghz.capture.signal` so `performed_capability_keys(env)` now
reflects that a capture has run. The Phase 2.6 policy gate is unchanged —
PASSIVE-only scope rejects both SAFE_ACTIVE actions before provider (zero
evidence, zero env mutation). `subghz_capture_plan()`: spectrum →
capture@433.92 → analyze@433.92 → capture@868.30 → analyze@868.30 (5
actions, 4 evidence).

---

## Phase 2.8.3 — Infrared stateful capture / analyze / transmit

`IrSignal` (Phase 2.8.0 substrate) gains five stateful fields:

| Field | Type | Default | Set by |
|---|---|---|---|
| `layout` | `str` | `""` | `infrared.capture` success (`short`/`long`/`unknown` via `_ir_classification` on `length_ms`) |
| `frequency_khz` | `float` | `0.0` | `infrared.capture` success (from the seed) |
| `carrier_duty_cycle` | `float` | `0.0` | `infrared.capture` success |
| `protocol_hint` | `str` | `""` | `infrared.analyze` success on a captured signal (`NEC`/`RC5`/`other` via `_ir_protocol_hint`) |
| `transmitted` | `bool` | `False` | `infrared.transmit` success |

Three handlers (registering them in `HANDLERS` makes the three Phase 2.8.0
`infrared.*` catalogue entries **supported**, so `registry.resolve()` now
returns `supported=True`):

### `action_ir_capture` (new, PASSIVE — observational, no evidence)

Validates `capture_id` is a known lab IR signal; unknown/malformed id returns
a structured failure Observation. On success it does NOT mutate env beyond
the entity — it sets the `IrSignal` substrate fields (`layout`,
`frequency_khz`, `carrier_duty_cycle`). No `env.notes` stamp, no evidence
(parallels `discover`/`scan`/`spectrum`).

### `action_ir_analyze` (new, SAFE_ACTIVE, produces `ir_analysis` evidence)

Requires `IrSignal` exists for the `capture_id` in env (per-target prereq).
Unknown/surreptitious capture_id returns a structured failure Observation
with `evidence=[]` + no env mutation. On success sets a deterministic
`protocol_hint` via `_ir_protocol_hint` heuristic:

| (frequency_khz, length_ms) | hint |
|---|---|
| `(38.0, 900)` | `NEC` |
| `(36.0, 560)` | `RC5` |
| anything else | `other` |

plus an `ir_classification` (`short`/`long`/`unknown`); stamps
`env.notes["ir_analyzed:<id>"]` (→ `performed_capability_keys` =
`infrared.analyze`) and builds an `ir_analysis` `EvidenceRecord` with concise
metadata (`capture_id`, `protocol_hint`, `frequency_khz`,
`carrier_duty_cycle`, `layout`) — no fake protocol blobs. `protocol_hint`
is a HINT, NOT a decoder (the simulator has no IR payload bytes).

### `action_ir_transmit` (new, SENSITIVE_ACTIVE, produces `ir_transmit` evidence)

Requires the SAME `capture_id` to be analyzed (`env.notes["ir_analyzed:<id>"]`
present) — a per-target gate exactly parallel to `wifi.capture.pmkid`'s
same-bssid prereq. Unknown capture_id / not-yet-analyzed target returns a
structured failure Observation with `evidence=[]` + no env mutation. On
success sets `IrSignal.transmitted=True`, stamps
`env.notes["ir_transmit:<id>"]`, and builds an `ir_transmit` `EvidenceRecord`
(metadata: `capture_id`, `protocol_hint`, `transmitted`). The Phase 2.6
policy gate is unchanged — PASSIVE-only scope rejects `analyze` + `transmit`
before provider (zero evidence, zero env mutation).

The `_NOTE_PREFIX_TO_CAPABILITY_KEY` mapping gains `ir_analyzed:` and
`ir_transmit:` (above). `ir_workflow_plan()`: capture → analyze@ir-lab-remote
→ transmit@ir-lab-remote → analyze@ir-lab-tv (4 actions, 3 evidence; NEC on
the remote, RC5 on the TV).

## Phase 2.8.4 — Zigbee wireless-mesh scan / inspect / join

Phase 2.8.4 stakes the **`zigbee`** domain with its own two entities — an
honest wireless mesh as real simulator state, not decorative data:

- `ZigbeeNetwork` — `pan_id`, `extended_pan_id`, `channel`, `rssi`, `prefix`,
  `node_count`.
- `ZigbeeNode` — `ieee_address`, `short_address`, `role`
  (`coordinator`/`router`/`end_device`), `network`, `parent_short_address`
  (the child→parent mesh link), `lqi`, `joined`.

`Environment` gains `zigbee_networks` + `zigbee_nodes` (populated in
`scenarios.py`; the lab carries a full mesh — PAN `0x1A2B` on ch15:
coordinator `...:01`/`0x0000`, router `...:02`/`0x0001`→`0x0000`, lamp
`...:03`/`0x0002`→`0x0001`, plus the **UNJOINED** join target
`...:04`/no-short, `node_count=3`; home a smaller PAN `0x2C3D`).

Three handlers, all registered in `HANDLERS` (so `zigbee` resolves
`supported=True` immediately — NOT the 2.8.0 unsupported-then-flip route):

- `action_zigbee_scan` (PASSIVE) — lists PANs via `_zigbee_network_entities`,
  which **recomputes `node_count` LIVE from the joined `ZigbeeNode`s** so a
  later `scan`/`inspect` reflects a join.
- `action_zigbee_inspect` (PASSIVE, `pan_id`) — per-PAN node list + topology
  ("4 node(s), 3 joined" before join → "4 node(s), 4 joined" after).
- `action_zigbee_join` (SAFE_ACTIVE, `pan_id`+`ieee_address`) — per-target
  gates: network exists + node exists + `not node.joined`. On success it
  assigns the next short address (`_zigbee_next_short` → `0x0003`), sets the
  parent to the first router else the coordinator (`_zigbee_parent` → `0x0001`),
  `lqi=220`, `joined=True`, stamps `env.notes["zigbee_joined:<ieee>"]`, and
  builds a `zigbee_join` `EvidenceRecord` (metadata: `ieee_address`, `network`,
  `assigned_short_address`, `parent_short_address`, `role`, `lqi` — a real
  transition, no fake blob).

Failure paths (unknown PAN, unknown node, already-joined node, missing/malformed
args, PASSIVE/SAFE_ACTIVE policy rejection) produce a structured failure
Observation with **zero evidence and zero env mutation**. The Phase 2.6 policy
gate is unchanged — PASSIVE-only scope rejects `join` before provider.

The `_NOTE_PREFIX_TO_CAPABILITY_KEY` mapping gains `zigbee_joined:` (above).
`zigbee_workflow_plan()`: scan → inspect@0x1A2B → join@0x1A2B/`00:15:8D:00:00:00:00:04`
→ inspect@0x1A2B (4 actions, 1 `zigbee_join` evidence).