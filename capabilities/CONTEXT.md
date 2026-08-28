# CONTEXT.md — capabilities/

> **For AI coding assistants:** Phase 2 capability layer.
> Read [`AGENTS.md`](../AGENTS.md) before making changes.

---

## Purpose

The capability layer answers three questions for the rest of the platform:

- What capabilities are available?
- What backend (provider) provides them?
- What actions does each capability support?

Everything capability-related lives here — nothing is hardcoded in the
engine, policy, CLI, or reports.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Package marker |
| `base.py` | ✅ Done | `Capability`, `CapabilityProvider` (ABC), `SimulatorProvider`, `DEFAULT_CAPABILITIES` |
| `registry.py` | ✅ Done | `CapabilityRegistry`, `CapabilityDecision`, `default_registry(environment)` |

---

## Public API

```python
from capabilities.registry import default_registry
from capabilities.base import Capability, CapabilityProvider

registry = default_registry(environment=env)
registry.capabilities()                  # list[Capability]
registry.provider_names()                # list[str] — e.g. ["simulator"]
registry.resolve("wifi.discovery", "discover")  # CapabilityDecision
```

## Adding a real hardware backend later

1. Subclass `CapabilityProvider` (implement `supports` + `execute`).
2. Register it: `registry.add_provider(MyESP32Provider(...))`.
3. Nothing else in the codebase needs to change — the engine already
   resolves providers through the registry.

`available_providers()` returns the list of provider names the registry
factory knows how to construct (`["simulator"]` today). A future real-hardware
backend plugs in by subclassing `CapabilityProvider` and registering itself.

## Rules

- Capability *definition* is static data — no runtime capability creation.
- A provider must be deterministic: same args → same Observation.
- No real hardware integration in Phase 2 — simulator only.

---

## Phase 2.7.1 — capability contract metadata

A `Capability` now carries the fields the rest of the platform needs to reason
about Suryafool's future multi-domain hardware/security operation surface —
**without** creating a second capability system. All new fields are opt-in
with safe defaults, so every existing positional `Capability(...)` call keeps
working unchanged.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `domain` | `str` | auto-derived from `capability.split('.', 1)[0]` | Wireless/network domain (wifi / ble / subghz / nfc / infrared / camera / ethernet / usb). Free-form; see `KNOWN_DOMAINS`. |
| `requires_args` | `tuple[str, ...]` | `()` | Required input arg names. Descriptive — providers already validate args structurally; the catalogue stays the single source of truth for the contract. |
| `output_entity_type` | `str` | `""` | Expected `Entity.type` of the produced Observation (`"wifi_network"`, `"ble_device"`, `"nfc_tag"`, `"subghz_signal"`, ...). `""` = unspecified. |
| `requires` | `tuple[str, ...]` | `()` | Prerequisite capability keys (e.g. `("ble.discovery.connect",)` for `ble.discovery.write`). Consumed by `Capability.prerequisites_met(observed_keys)`. |
| `hardware` | `str` | `""` | Declared hardware requirement (`"esp32"`, etc.). `""` = none/simulator-only. |
| `produces_evidence` | `bool` | `False` | Reserved for the future evidence/artifact pipeline. `False` for every entry in Phase 2.7.1. |
| `mutates_state` | `bool` | `False` | Whether the action may mutate `Environment`/entity state. `False` for observation-only; `True` for `connect`, `write`, `nfc.read`, `subghz.analyze`. This is the **stateful vs observational** distinction. |

Two methods are added:

- `__post_init__()` — raises `ValueError` on empty `capability` or `action`,
  auto-derives `domain` from `capability` if it was left empty. A namespace
  without a dot becomes its own domain (e.g. `"infrared"` → `"infrared"`).
- `prerequisites_met(observed_keys: set[str]) -> bool` — returns `True` iff
  every key in `requires` is present in `observed_keys`. Empty `requires`
  always returns `True` (passive actions have no prerequisites). The live
  set of observed keys comes from
  `simulator.simulator.performed_capability_keys(env)` (see
  [`simulator/CONTEXT.md`](../simulator/CONTEXT.md)): env.notes prefixes
  (`ble_connected:`, `ble_write:`, `nfc_read:`, `subghz_analyzed:`) map back to
  capability keys, so a future observe → test → observe loop can ask "is X
  now ready to run?" without a separate mission-state machine.

`KNOWN_DOMAINS` is an open-set `frozenset` carrying the eight intended
domains (`wifi`, `ble`, `subghz`, `nfc`, `infrared`, `camera`, `ethernet`,
`usb`). It is a vocabulary hint for tests, **not** an enforced membership —
adding a future domain is a catalogue concern, not a dataclass change. Four
of the eight domains have no actions implemented in Phase 2.7.1; they exist
to make the contract's extensibility visible.

`Capability.to_dict()` carries every new field. Phase 2.7.1's `requires_args`
and `requires` are encoded as JSON lists for run-record/report serialization
(they are tuples in-memory; tuples round-trip cleanly through `json`).

### Phase 2.7.1 regression

`tests/test_phase271_capability_metadata.py` — 33 stdlib-runnable tests
covering: per-entry contract vs. expected metadata table, `KNOWN_DOMAINS`
open-set membership, `to_dict()` field roundtrip, auto-derivation for
declared + future (infrared/camera/ethernet/usb) namespaces,
`ValueError` on invalid definitions, `prerequisites_met` flips,
`performed_capability_keys(env)` mapping with unknown-prefix tolerance,
registry surfacing metadata, simulator end-to-end consumption
(observe→test→observe flips the write prereq), policy-reject → no env
mutation AND authoritative `mutates_state=True` agree, and full regression
of the catalogue (12 entries, per-key risks, positional-constructor
back-compat).

---

## Phase 2.7.2 — stateful Wi-Fi capture entries

The catalogue now carries two new `wifi.capture.*` entries that mutate
`WifiNetwork` entity state. The `wifi.capture` namespace is intentionally
separate from `wifi.discovery` to encode Risinek's capture-vs-discovery
separation: discovery reads, capture mutates.

| Capability key | Risk | `requires_args` | `requires` | `mutates_state` |
|---|---|---|---|---|
| `wifi.capture.handshake` | `SAFE_ACTIVE` | `("bssid",)` | `()` | `True` |
| `wifi.capture.pmkid` | `SENSITIVE_ACTIVE` | `("bssid",)` | `("wifi.capture.handshake",)` | `True` |

`wifi.capture.pmkid` is the second `requires`-chain in the catalogue
(alongside `ble.discovery.write` `requires` `ble.discovery.connect`); the
prereq is enforced *per-target* in the simulator handler — `wifi.capture.handshake`
must have captured the SAME `bssid` first, not just any WPA network
(`WifiNetwork.handshake_captured` is the gate, not the catalogue-level
`performed_capability_keys(env)` set). Catalogue-level `requires` answers
"has any handshake run somewhere?" — useful for agents planning; the
simulator's per-target check answers "is precisely this target ready?"
— useful for the active operator.

`wifi.capture.*` validate the target network's `encryption` is in
{`WPA2`, `WPA3`}; `OPEN`/`WEP` return a structured failure Observation
with no env mutation. Authorization flows through the unchanged Phase 2.6
gate (`RiskDeclarationRule` + `RiskTierAuthorizedRule`). Authorization is
unchanged — no new hardware path.

### Phase 2.7.2 regression

`tests/test_phase272_wifi_capture.py` — 36 stdlib-runnable tests._SEE
[`tests/CONTEXT.md`](../tests/CONTEXT.md) for the per-suite summary.

---

## Phase 2.7.3 — stateful BLE GATT pairing + secure-write entries

The catalogue now carries two new `ble.gatt.*` entries that mutate
`BleDevice` entity state. The new `ble.gatt` namespace sits **alongside**
the existing `ble.discovery` namespace, exactly parallel to how Phase 2.7.2's
`wifi.capture` namespace sits alongside `wifi.discovery`: encoding the
architectural distinction (Risinek-style capture-vs-discovery separation,
rolled into Suryafool's own typed capability model) between *link-level
GATT discovery operations* and *GATT-level session/state-changing operations*.

| Capability key | Risk | `requires_args` | `requires` | `mutates_state` |
|---|---|---|---|---|
| `ble.gatt.pair`  | `SAFE_ACTIVE` | `("address",)` | `("ble.discovery.connect",)` | `True` |
| `ble.gatt.write` | `SENSITIVE_ACTIVE` | `("address", "characteristic", "value")` | `("ble.gatt.pair",)` | `True` |

Two `requires`-chains now reference across namespaces:

- `ble.gatt.write` `requires` `ble.gatt.pair` (intra-namespace, parallel to `wifi.capture.pmkid` `requires` `wifi.capture.handshake`).
- `ble.gatt.pair`  `requires` `ble.discovery.connect` (cross-namespace — pairing presupposes the legacy Phase 2.7 link-level connect).

The per-target prereq is enforced strictly by the simulator handler:

- `ble.gatt.pair`  requires `b.connected=True` (the Phase 2.7 `ble.discovery.connect` handler sets that flag) *on the same address* — not "some connect ran somewhere".
- `ble.gatt.write` requires `b.paired=True` (the new `ble.gatt.pair` handler sets that flag) *on the same address*.
- `ble.gatt.write` additionally validates that `characteristic` is a known GATT service (`b.gatt_services`) — refusing unknown characteristics with a structured failure Observation.

Catalogue-level `requires` answers "has the prerequisite chain run anywhere?"
— useful for an agent planning its next action; the simulator's per-target
check answers "is precisely this target ready?" — useful for the active
operator. Both gates are needed for true stateful behavior.

`ble.gatt.*` do not gate on encryption (BLE has no WPA/OPEN analog) but DO
gate on `b.connectable=False` (link-layer restriction) and on the per-target
prereq flag. Invalid inputs (missing/non-string address/characteristic, `None`
value, unknown address) return structured failure Observations with no env
mutation. Authorization flows through the unchanged Phase 2.6 gate
(`RiskDeclarationRule` + `RiskTierAuthorizedRule`). Authorization is
unchanged — no new hardware path.

### Phase 2.7.3 regression

`tests/test_phase273_ble_gatt.py` — 47 stdlib-runnable tests. SEE
[`tests/CONTEXT.md`](../tests/CONTEXT.md) for the per-suite summary.

---

## Phase 2.7.5 — `produces_evidence` is now functional for `wifi.capture.handshake`

The `produces_evidence` flag on the `Capability` dataclass (declared in
Phase 2.7.1) is now backed by a real evidence pipeline for one slice:
`wifi.capture.handshake`. Phase 2.7.5 establishes ONE clean vertical slice
that Phase 2.7.6/2.7.7 generalize.

| Capability key | Risk | `produces_evidence` (since Phase 2.7.7) |
|---|---|---|
| `wifi.capture.handshake` | `SAFE_ACTIVE` | **`True`** ✅ (Phase 2.7.5) |
| `wifi.capture.pmkid`     | `SENSITIVE_ACTIVE` | **`True`** ✅ (Phase 2.7.6) |
| `ble.gatt.pair`          | `SAFE_ACTIVE` | **`True`** ✅ (Phase 2.7.7) |
| `ble.gatt.write`         | `SENSITIVE_ACTIVE` | **`True`** ✅ (Phase 2.7.7) |
| `subghz.capture.signal`  | `SAFE_ACTIVE` | **`True`** ✅ (Phase 2.8.1, kind `subghz_capture`) |
| `subghz.discovery.analyze` | `SAFE_ACTIVE` | **`True`** ✅ (Phase 2.8.1, kind `subghz_analysis`) |
| all other 16 entries | — | `False` (unchanged) |

`produces_evidence` is a **flag** the catalogue exposes — it does not gate
execution. The actual evidence production happens in the simulator's success
path (`action_wifi_capture_handshake`, `action_wifi_capture_pmkid`,
`action_ble_gatt_pair`, `action_ble_gatt_write` build an `EvidenceRecord`,
attach it to the returned `Observation.evidence`); the engine mirrors
`observation.evidence` to both `ActionRecord.evidence` and `Run.evidence`,
stamps `source_action_id` (the simulator deliberately cannot see the
`ActionRequest.id`), and emits one `evidence.created` JSONL event per item.
Policy-rejected actions never reach the provider, so they produce zero
evidence. Failed capture/write paths (missing/unknown target, invalid args,
non-WPA encryption / unknown characteristic, unmet prerequisite) return
`Observation(evidence=[])`, so they also produce zero evidence. The
per-target prerequisites are all still enforced by the handlers: pmkid needs
a handshake on the SAME bssid, ble.gatt.pair needs connect on the SAME
address, ble.gatt.write needs pairing on the SAME address. Evidence is
distinct from findings (raw entity observations) and lives in its own
`Run.evidence` list with its own `kind` field — it is NOT a finding, NOT an
observation, NOT an indicator, NOT a hypothesis. SEE
[`core/evidence.py`](../core/evidence.py) for the dataclass and
[`tests/CONTEXT.md`](../tests/CONTEXT.md) for the Phase 2.7.5/2.7.6/2.7.7
test summaries.

---

## Phase 2.8.0 — multi-domain foundation (no second capability system)

The catalogue grows 14 → 21 by APPENDING seven entries for the three domains
that had no actions yet. The 14 Phase 2.7 entries are byte-identical; only
the count guards in prior suites changed (mirroring the 12→14 growth).
Sub-GHz and NFC keep their existing 2-entry surfaces (stateful/evidence
extension is 2.8.1 / 2.8.2, not a catalogue reshape).

| Capability key | Risk | `requires_args` | `requires` | `mutates_state` |
|---|---|---|---|---|
| `infrared.capture` | `PASSIVE` | `()` | `()` | `False` |
| `infrared.analyze` | `SAFE_ACTIVE` | `("capture_id",)` | `()` | `True` |
| `infrared.transmit` | `SENSITIVE_ACTIVE` | `("capture_id",)` | `("infrared.capture",)` | `True` |
| `ethernet.discovery.discover` | `PASSIVE` | `()` | `()` | `False` |
| `ethernet.discovery.inspect` | `PASSIVE` | `("host",)` | `()` | `False` |
| `usb.discovery.enumerate` | `PASSIVE` | `()` | `()` | `False` |
| `usb.discovery.inspect` | `PASSIVE` | `("path",)` | `()` | `False` |

---

## Phase 2.8.1 — Sub-GHz/RF stateful capture slice

ONE new `subghz.capture.signal` entry (SAFE_ACTIVE, `produces_evidence=True`)
in a NEW `subghz.capture` namespace (parallel to `wifi.capture` / `ble.gatt`);
the existing `subghz.discovery.analyze` entry is upgraded — its
`produces_evidence` flag flips `False`→`True`. No Phase 2.7 entries reshaped;
the catalogue grew 21 → 22 by appending alone.

| Capability key | Risk | `requires_args` | `requires` | `mutates_state` | `produces_evidence` |
|---|---|---|---|---|---|
| `subghz.capture.signal` | `SAFE_ACTIVE` | `("frequency_mhz",)` | `()` | `True` | **`True`** ✅ (Phase 2.8.1, kind `subghz_capture`) |
| `subghz.discovery.analyze` | `SAFE_ACTIVE` | `("frequency_mhz",)` | `()` | `True` | **`True`** ✅ (Phase 2.8.1, kind `subghz_analysis`) |

`subghz.discovery.analyze` catalogue metadata is unchanged from Phase 2.7.1
except for the single `produces_evidence` flag flip — `requires=()` stays
empty (the per-target gate lives in the simulator handler, exactly like
`wifi.capture.pmkid`'s same-bssid gate; catalogue-level `requires` answers
"has any analyze run anywhere?"). The new `subghz.capture.signal` carries
`requires=()` too — its only prerequisite is the host environment's spectrum
discovery (the plan enforces order; the simulator handler does not need a
catalogue-level prereq to know whether a frequency is valid).

`subghz_capture_plan()`: spectrum → capture@433.92 → analyze@433.92 →
capture@868.30 → analyze@868.30 (5 actions, 4 evidence — 2 capture + 2
analysis). Failure paths (unknown frequency, not-captured target, malformed
args, OPEN/uncaptured prereq, policy-rejected) all produce zero evidence +
zero env mutation. `decoded_protocol_hint` is a HINT in the simulator, not a
real decoder (no payloads in the simulator); the `_subghz_protocol_hint`
deterministic map labels (frequency, modulation) → `remote_control` /
`LoRa_like` / `ISM_IoT` / `unknown`. SEE
[`simulator/CONTEXT.md`](../simulator/CONTEXT.md) for the handler details and
[`tests/CONTEXT.md`](../tests/CONTEXT.md) for the test summary.


**Infrared uses a flat `infrared` namespace** (`__post_init__` derives the
domain from a dot-less namespace) — the mission-shape
`infrared.capture/analyze/transmit` that also encodes capture→analyze→transmit
as a prereq chain (`infrared.transmit` requires `infrared.capture`, parallel
to `ble.gatt.pair` requiring `ble.discovery.connect`).

**Registered-but-unsupported is the explicit contract.** The 7 new entries
have NO simulator handlers until their dedicated 2.8.x subphases. Therefore
`registry.resolve()` returns `supported=False`
("No registered provider supports this capability.") and the unchanged
`ProviderSupportsRule` REJECTs these actions at the policy gate BEFORE the
provider — zero observation/evidence/env mutation, run continues. No shallow
fake handlers were added to inflate counts. The CLI `capabilities` command
surfaces a `supported` field (JSON, additive) + a `[UNSUPPORTED]` tag (human
mode) per entry.

No `produces_evidence=True` additions (no real evidence behavior yet — the
4 Phase 2.7 producers are unchanged) and no policy/risk/AuthorizationScope
changes. `tests/test_phase280_multidomain.py` — 29 stdlib-runnable tests
covering registration, metadata validity, risks, resolution, unsupported
behavior, prereq metadata, and Phase 2.7 freeze regression.