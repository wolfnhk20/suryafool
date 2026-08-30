# AGENTS.md — Suryafool

> **This file is the canonical guide for AI coding assistants working on this repository.**
> Read this before touching any code. Check the relevant `CONTEXT.md` for the directory you are working in.

---

## What is Suryafool?

Suryafool is a **universal agentic wireless platform** — the operating layer between autonomous AI agents and heterogeneous wireless hardware (Wi-Fi, BLE, Sub-GHz, NFC, RFID, IR, SDR).

Users give it a **natural-language mission** (e.g. "Explore this environment", "Audit this device").  
The platform autonomously plans, executes, observes, re-plans, and reports.

Full product vision: [`docs/PRD.md`](docs/PRD.md)  
Bootstrap architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Repository Layout

```
suryafool/
├── AGENTS.md                  ← you are here
├── CONTEXT.md                 ← root project context
├── README.md                  ← setup + usage guide
├── requirements.txt
├── .env.example
├── check_env.py               ← standalone read-only check script
│
├── docs/
│   ├── CONTEXT.md             ← docs directory context
│   ├── PRD.md                 ← full product requirements
│   └── ARCHITECTURE.md        ← bootstrap agent design spec
│
├── bootstrap/               ← ✅ COMPLETE
│   ├── CONTEXT.md             ← bootstrap module context
│   ├── __init__.py            ← Python package marker
│   ├── manifest.yaml          ← dependency manifest (human-authored, never LLM-generated)
│   ├── platform.py            ← OS detection (windows / linux / macos)
│   ├── checks.py              ← read-only check() per dependency
│   ├── remediate.py           ← remediate() — runs manifest install_cmd only
│   ├── provisioning_guardian.py ← elevation gate (always shows command + waits for human)
│   └── agent.py               ← full remediation loop with Rich UI
│
├── core/                    ← ✅ COMPLETE (llm.py + Phase 2 types)
│   ├── CONTEXT.md             ← core module context
│   ├── llm.py                 ← LLM factory + sliding-window rate limiter (32 req/min)
│   ├── confidence.py          ← CONFIRMED/LIKELY/POSSIBLE/UNKNOWN enum
│   ├── observation.py         ← Entity + Observation dataclasses
│   ├── mission.py             ← Run/ActionRequest/PolicyDecision/ActionRecord
│   └── events.py              ← JSONL event helpers (CLI wire format)
│
├── capabilities/            ← ✅ COMPLETE (Phase 2)
│   ├── CONTEXT.md
│   ├── base.py                ← Capability, CapabilityProvider (ABC)
│   └── registry.py            ← CapabilityRegistry + SimulatorProvider binding
│
├── simulator/               ← ✅ COMPLETE (Phase 2)
│   ├── CONTEXT.md
│   ├── rng.py                 ← SeededRNG (deterministic)
│   ├── entities.py            ← WifiNetwork, BleDevice, NfcTag, SubGhzSignal
│   ├── environment.py         ← mutable Environment state
│   ├── scenarios.py           ← home / lab / crowded presets
│   └── simulator.py           ← execute() action handlers → Observations
│
├── policy/                  ← ✅ COMPLETE (Phase 2)
│   ├── CONTEXT.md
│   └── policy.py              ← PolicyEngine + 6 deterministic rules
│
├── engine/                  ← ✅ COMPLETE (Phase 2)
│   ├── CONTEXT.md
│   ├── runner.py              ← RunEngine + plans (exploration / active_inspection / wifi_capture / ble_gatt_workflow)
│   └── logger.py              ← RunLogger (run.json + events.jsonl)
│
├── reports/                 ← ✅ COMPLETE (Phase 2)
│   ├── CONTEXT.md
│   └── html_report.py         ← render_run() / write_report()
│
├── cli/                     ← ✅ COMPLETE (Phase 2)
│   ├── CONTEXT.md
│   └── phase2.py              ← capabilities / scenarios / providers / run / show / report
│
├── tests/                     ← ✅ COMPLETE (Phase 2 / 2.6 / 2.7 / 2.7.1 / 2.7.2 / 2.7.3 / 2.7.5 / 2.7.6 / 2.7.7 / 2.7.9)
│   ├── CONTEXT.md
│   ├── test_phase2_core.py         ← 21 stdlib-runnable tests
│   ├── test_phase26_authorization.py ← 15 stdlib-runnable tests
│   ├── test_phase27_active_sim.py  ← 37 stdlib-runnable tests
│   ├── test_phase271_capability_metadata.py ← 33 stdlib-runnable tests
│   ├── test_phase272_wifi_capture.py ← 36 stdlib-runnable tests
│   ├── test_phase273_ble_gatt.py   ← 47 stdlib-runnable tests
│   ├── test_phase275_evidence.py   ← 37 stdlib-runnable tests (Phase 2.7.5)
│   ├── test_phase276_pmkid_evidence.py ← 32 stdlib-runnable tests (Phase 2.7.6)
│   ├── test_phase277_ble_evidence.py ← 30 stdlib-runnable tests (Phase 2.7.7)
│   └── test_phase279_integration.py ← 26 stdlib-runnable tests (Phase 2.7.9 golden paths + contract audit)
│
└── suryafool-cli/             ← ✅ COMPLETE (v0.1.0) — Ink/React cyberpunk TUI
    ├── bin/suryafool.js       ← CLI entry (yargs) → forks bin/run.mjs
    ├── bin/run.mjs            ← Ink render entry (reads SURYAFOOL_ARGS env)
    ├── src/app.js             ← main App component (single command + REPL)
    ├── src/components/        ← Logo, ScanPanel, AgentStatus, REPL, CapabilitiesView, EvidenceFeed, ...
    ├── src/animations/        ← matrix rain, glitch, typewriter, scanner, neon
    ├── src/backend/           ← BinaryManager (fetch/run), OutputParser (event stream)
    ├── src/styles/theme.js    ← cyberpunk + clean themes
    └── src/utils/             ← platform, config (~/.suryafool/config.json)
```

Each directory has a `CONTEXT.md`. **Read it before editing files in that directory.**

---

## Agent Roster

### Implemented

| Agent | Module | Status |
|---|---|---|
| **Bootstrap / Environment Agent** | `/bootstrap` | 🟢 Complete |
| **Phase 2 Deterministic Core** | `/capabilities`, `/simulator`, `/policy`, `/engine`, `/reports`, `/cli` | 🟢 Complete — capability registry, deterministic policy gate, wireless simulator (home/lab/crowded), run engine, JSONL logging, HTML reports. No LLM in the loop. |
| **Phase 2.5 Marauder Hardware Spike** | ~~`/backends`~~ | 🟡 Architectural reference only (Phase 2.7.4 decoupled) — proved the `CapabilityProvider` ABC serves real hardware (ESP32 Marauder) with no core changes. The `backends/` directory and `MarauderProvider` were **removed** in Phase 2.7.4; Suryafool now owns its capability model. The [ESP32 Marauder project](https://github.com/justcallmekoko/ESP32Marauder) remains an architectural reference for future firmware design. |
| **Phase 2.7 Stateful Active Simulator** | `/simulator`, `/capabilities`, `/engine`, `/cli` | 🟢 Complete — two stateful *active* capabilities (`ble.discovery.connect` SAFE_ACTIVE, `ble.discovery.write` SENSITIVE_ACTIVE) that **mutate `BleDevice` entity objects** so a later passive observation reflects the change. Full deterministic chain `discover → inspect → connect → write → inspect` via `--plan active_inspection`. Target/arg validation + structured failure Observations (no crash); the existing policy gate is unchanged (provider-not-reached on REJECT proven). 37 stdlib-runnable tests; no LLM, no hardware, no attack code. |
| **Phase 2.7.1 Capability Contract Metadata** | `/capabilities`, `/simulator`, `/cli` | 🟢 Complete — extends the existing `Capability` dataclass with opt-in metadata (domain, requires_args, output_entity_type, requires, hardware, produces_evidence, mutates_state) + `KNOWN_DOMAINS` + `Capability.prerequisites_met()` + simulator `performed_capability_keys(env)`. Same registry/policy architecture — no second capability system. Lightweight domain concept (wifi/ble/subghz/nfc/infrared/camera/ethernet/usb). Stateful-vs-observational distinction + observe→test→observe readiness flips proven end-to-end. 33 stdlib-runnable tests + all 2/2.6/2.7 suites still green. No new wireless actions, no Phase 2.6 changes, no LLM, no hardware, no attack code. |
| **Phase 2.7.2 Stateful Wi-Fi Capture Simulator** | `/simulator`, `/capabilities`, `/engine`, `/cli` | 🟢 Complete — two stateful *active* Wi-Fi capture capabilities (`wifi.capture.handshake` SAFE_ACTIVE, `wifi.capture.pmkid` SENSITIVE_ACTIVE) that **mutate `WifiNetwork` entity objects** (`handshake_captured`, `captured_frames`, `pmkid_captured`) so a later passive `wifi.discovery.inspect` reflects the change. New `wifi.capture` namespace (NOT `wifi.discovery`) encodes Risinek's capture-vs-discovery separation. Full deterministic chain `discover → inspect → capture.handshake → capture.pmkid → inspect` via `--plan wifi_capture`. Per-target prereq (handshake on the SAME bssid first) + WPA-only encryption gate + structured failure Observations (no crash); the existing Phase 2.6 policy gate is unchanged (provider-not-reached on REJECT proven). `action_wifi_inspect` surfaces capture state in its summary. 36 stdlib-runnable tests + all 2/2.6/2.7/2.7.1 suites still green. No LLM, no hardware, no attack code. |
| **Phase 2.7.3 Stateful BLE GATT Simulator** | `/simulator`, `/capabilities`, `/engine`, `/cli` | 🟢 Complete — two stateful *active* BLE GATT capabilities (`ble.gatt.pair` SAFE_ACTIVE, `ble.gatt.write` SENSITIVE_ACTIVE) that **mutate `BleDevice` entity objects** (`paired`, `secure_characteristics`) so a later passive `ble.discovery.inspect` reflects the change. New `ble.gatt` namespace sits **alongside** `ble.discovery` — exactly parallel to how `wifi.capture` sits alongside `wifi.discovery` (Phase 2.7.2). Full deterministic chain `discover → inspect → connect (Phase 2.7) → pair → gatt.write → inspect` via `--plan ble_gatt_workflow`. Per-target prereqs (connect → pairing on the SAME address; pairing → secure write on the SAME address) + structured failure Observations (not-connectable / not-connected / not-paired / unknown-characteristic / missing args — no crash); the existing Phase 2.6 policy gate is unchanged (provider-not-reached on REJECT proven via `secure_characteristics` snapshot invariant test). `action_ble_inspect` summary surfaces paired + secure-write state. 47 stdlib-runnable tests + all 2/2.6/2.7/2.7.1/2.7.2 suites still green. No LLM, no hardware, no attack code. |
| **Phase 2.7.4 Marauder Decoupling** | ~~`/backends`~~ | 🟢 Complete — removed the ESP32 Marauder hardware spike from the runtime: `backends/` directory + `tests/test_phase25_marauder.py` deleted; `marauder_discovery_plan()`, `--provider`/`--port`/`--baud` CLI flags, `MarauderProvider` import + registry `provider_name`/`transport` branch, `SURYAFOOL_MARAUDER_FAKE` env var, and marauder-specific regression tests all removed. `available_providers()` returns `["simulator"]` only. Kept the generic seams (`CapabilityProvider` ABC, `CapabilityRegistry.add_provider()`, `Capability.hardware` field) for future Suryafool-owned firmware. 6 Python suites + 2 Node smoke tests green. The [ESP32 Marauder project](https://github.com/justcallmekoko/ESP32Marauder) remains an architectural reference only. |
| **Phase 2.7.5 First Evidence-Producing Capability** | `/core`, `/simulator`, `/capabilities`, `/engine`, `/reports`, `/cli` | 🟢 Complete — makes the Phase 2.7.1 `produces_evidence` flag functional for ONE slice (`wifi.capture.handshake`). New `core/evidence.py` `EvidenceRecord` (id, source_action_id, source_capability, source_action, target_entity_id, target_entity_type, kind, summary, metadata, captured_at) + `KNOWN_EVIDENCE_KINDS`. `Observation.evidence` carries it out of the simulator's success path only (all failure paths → `[]`); the engine mirrors it to `ActionRecord.evidence` + `Run.evidence`, stamps `source_action_id`, and emits one `evidence.created` JSONL event per item. Policy-rejected and failed captures provably produce zero evidence. Persisted via `Run.to_dict/from_dict` (old run.json back-compat: absent key → `[]`). HTML report gains a top-level EVIDENCE section + per-action evidence blocks; CLI `capabilities` surfaces `produces_evidence`. 37 stdlib-runnable tests + all 6 prior suites + 2 Node smokes green. BLE / Sub-GHz / NFC / IR evidence deliberately deferred (stay `produces_evidence=False`). No LLM, no hardware, no attack code. |
| **Phase 2.7.6 Generalize Evidence to PMKID Capture** | `/core`, `/simulator`, `/capabilities`, `/reports`, `/cli`, `/engine` | 🟢 Complete — extends the Phase 2.7.5 pipeline to the second wifi.capture capability (`wifi.capture.pmkid`) through the EXACT same machinery (no second evidence system). `KNOWN_EVIDENCE_KINDS` += `wifi_pmkid`; catalogue `wifi.capture.pmkid` now `produces_evidence=True`; `action_wifi_capture_pmkid` success path builds a `wifi_pmkid` `EvidenceRecord` with realistic concise metadata (`pmkid`, `encryption`, `ssid`, `bssid`, `channel`, `handshake_prereq`) — no fake packet/blob data. All non-success paths (missing/invalid/unknown bssid, OPEN, WEP, per-target handshake prereq unmet on the SAME bssid, policy rejection) provably produce zero evidence. The Phase 2.7.2 per-target handshake prereq remains enforced — no PMKID evidence can exist without a prior handshake capture on the same target. Handshake evidence behavior unchanged; both kinds coexist in one run (run.json round-trip + 2 `evidence.created` JSONL events + HTML EVIDENCE section). 32 stdlib-runnable tests (`test_phase276_pmkid_evidence.py`) + all 7 prior suites + 2 Node smokes green. No LLM, no hardware, no attack code. |
| **Phase 2.7.7 Cross-Domain BLE Evidence** | `/core`, `/simulator`, `/capabilities`, `/reports`, `/engine` | 🟢 Complete — generalizes the exact same 2.7.5/2.7.6 pipeline ACROSS domains to the BLE GATT session operations: `ble.gatt.pair` → kind `ble_pairing`, `ble.gatt.write` → kind `ble_secure_write` (`KNOWN_EVIDENCE_KINDS` += both; both catalogue entries `produces_evidence=True` — the 4 evidence producers are wifi.capture handshake/pmkid + ble.gatt pair/write; the other 10 entries stay `False`). Handler success paths build the `EvidenceRecord`s with realistic concise metadata (pairing: `address`, `device_name`, `connectable`, `secure_service_count`; secure write: `address`, `device_name`, `characteristic`, `value`) — no fake protocol blobs. Per-address prerequisites remain the simulator's gate: no `ble_pairing` evidence without connect on the SAME address; no `ble_secure_write` evidence without pairing on the SAME address; unknown characteristic / invalid input / not-connectable / unconnected / unpaired / policy-rejected paths all produce zero evidence. Wi-Fi handshake + PMKID evidence unchanged. Existing BLE state transitions + `inspect` behavior preserved. No policy / AuthorizationScope / JSONL / HTML changes (pipeline reused as-is). 30 stdlib-runnable tests (`test_phase277_ble_evidence.py`) + all 8 prior suites + 2 Node smokes green. No LLM, no hardware, no attack code. |
| **Phase 2.7.8 Live Evidence Surfacing in the TUI** | `/suryafool-cli` | 🟢 Complete — connects the existing `EVIDENCE_CREATED` JSONL event to the live TUI using the existing OutputParser/event architecture (no new event model). `reducer.js` gains a bounded `evidence` list + `ADD_EVIDENCE` handler (newest 200); `app.js` dispatches `ADD_EVIDENCE` + a one-line console notice on `evidence.created` (no raw metadata dump); new `EvidenceFeed` component (via new `evidenceFormat.js` pure `formatEvidenceLine` helper) renders compact rows — kind (wifi→primary / ble→accent color), target, source capability.action, one-line summary — with defensive fallbacks so malformed/missing metadata never crashes the UI; `TabPanel` gains an `Evidence` tab. Multiple records render independently; Wi-Fi and BLE evidence are visually distinguishable; existing action/output/error event handling and `--json` semantics untouched; no Python/policy/simulator/report changes. esbuild bundle builds clean; 50 Node tests (11 new across parser/reducer/evidenceFormat) + 2 Node smokes + all 9 Python suites green. |
| **Phase 2.7.9 Deterministic Assessment Integration + Contract Freeze** | `/tests`, `/core`, `/simulator`, `/capabilities`, `/engine`, `/reports`, `/cli`, `/suryafool-cli` | 🟢 Complete — FINAL Phase 2.7 subphase. `test_phase279_integration.py` (26 tests) proves the full stack end-to-end as one coherent platform: WiFi golden path (discover→inspect→handshake→pmkid→inspect→2 evidence), BLE golden path (discover→inspect→connect→pair→GATT write→inspect→2 evidence), combined run (both plans → 4 evidence kinds coexisting; run.json + JSONL + HTML verified), authorization boundaries (PASSIVE rejects all 5 active actions before provider; SAFE_ACTIVE allows safe + blocks sensitive; rejected actions emit zero `evidence.created`), per-target prerequisites (pmkid needs same-bssid handshake; pair needs same-address connect; write needs same-address pair), negative-path consistency (wrong target / invalid args / success-then-failure → state + evidence stay consistent), determinism, and an explicit CONTRACT AUDIT of every Phase 2.7 interface (catalogue 14, 4 evidence producers, `KNOWN_EVIDENCE_KINDS` frozen, `EvidenceRecord` field contract, `Observation/ActionRecord/Run.evidence` defaults + round-trips, Python↔Node `EVIDENCE_CREATED` sync, plan shapes frozen, `performed_capability_keys` mapping). No architecture/domain/kinds changes — freeze only. 10 Python suites (314 tests) + 50 JS tests + 2 Node smokes all green. Phase 2.7 declared COMPLETE. Node TUI feed verified against live `--json` streams (WiFi 2 kinds, BLE 2 kinds). |
| **Phase 2.8.0 Multi-Domain Deterministic Expansion Foundation** | `/capabilities`, `/simulator`, `/cli`, `/tests`, `/docs` | 🟢 Complete — FIRST Phase 2.8 subphase. Establishes the clean multi-domain foundation for the remaining five Suryafool domains ON the frozen Phase 2.7 stack — no second capability system, no parallel frameworks. Catalogue grows **14 → 21** by APPENDING 7 entries for the three domains with no actions yet: `infrared.{capture,analyze,transmit}` (flat namespace; `transmit` requires `capture` — SENSITIVE_ACTIVE replay chain), `ethernet.discovery.{discover,inspect}`, `usb.discovery.{enumerate,inspect}`. Sub-GHz and NFC keep their existing 2-entry surfaces (2.8.1/2.8.2 extend them, not a catalogue reshape). New adapter-less **registered-but-unsupported** semantics: entries have NO simulator handlers, so `registry.resolve()` → `supported=False` and the unchanged policy gate REJECTs them BEFORE the provider (zero observation/evidence/env mutation; run continues) — the platform never pretends an unimplemented domain works. CLI `capabilities` adds a `supported` field (JSON additive) + `[UNSUPPORTED]` human tag. Entity/environment substrate: `IrSignal` / `EthernetHost` / `UsbDevice` dataclasses + empty `Environment.ir/ethernet/usb` + `snapshot()`. No evidence kinds, no policy changes, no plans, no LLM/hardware. 29 new stdlib-runnable tests (`test_phase280_multidomain.py`) + suite count guards updated 14→21; the 14 frozen Phase 2.7 entries, 4 evidence producers, `KNOWN_EVIDENCE_KINDS`, plan shapes, and all report/JSONL/TUI contracts verified unchanged. 11 Python suites (343 tests) + 50 JS tests + esbuild build + 2 Node smokes all green. Phase 2.8.0 declared COMPLETE. |

### Planned (from PRD §9)

| Agent | Role | Module |
|---|---|---|
| **Mission Orchestrator** | Central coordinator — interprets objectives, delegates tasks, handles replanning | `/agents/orchestrator` |
| **Discovery Agent** | Broad passive reconnaissance across all available wireless protocols | `/agents/discovery` |
| **Signal Intelligence Agent** | Characterizes signals, detects patterns, classifies signal families | `/agents/signal_intel` |
| **Device Intelligence Agent** | Builds logical device hypotheses from multi-protocol observations | `/agents/device_intel` |
| **Correlation Agent** | Links observations across protocols into a unified environment model | `/agents/correlation` |
| **Experiment Agent** | Designs controlled investigations to resolve between hypotheses | `/agents/experiment` |
| **Security Research Agent** | Maps attack surfaces, matches weakness classes, selects permitted tests | `/agents/security_research` |
| **Attack Planning Agent** | Active only during authorized security missions — reasons about test paths | `/agents/attack_planning` |
| **Verification Agent** | Independently verifies security findings, checks reproducibility | `/agents/verification` |
| **Skeptic Agent** | Challenges conclusions from other agents, reduces overconfidence | `/agents/skeptic` |
| **Memory Agent** | Persistent environmental and mission knowledge store | `/agents/memory` |
| **Scope Guardian** | **Deterministic** policy enforcement layer — not an LLM advisory agent | `/scope_guardian` |

> **Scope Guardian is not optional.** It is an enforced gate. No active wireless action bypasses it.

---

## Phase 2 (Deterministic Core) — Quick Reference

Run end-to-end without hardware or LLM:

```bash
# From repo root
python -m cli.phase2 capabilities            # list capability catalogue
python -m cli.phase2 scenarios               # list simulator scenarios
python -m cli.phase2 run --scenario home     # deterministic run → logs + report
python -m cli.phase2 run --scenario lab --seed 7 --json   # JSONL event stream
python -m cli.phase2 show <run-id>           # summarize a stored run
python -m cli.phase2 report <run-id>         # regenerate HTML report
```

Run artifacts live under `~/.suryafool/runs/<run-id>/` (override with
`SURYAFOOL_RUNS_DIR`): `run.json`, `events.jsonl`, `report.html`.

Core loop: `ActionRequest → CapabilityRegistry.resolve() → PolicyEngine.validate() → provider.execute() → Observation → Run record`.

Phase 2 has **no LLM dependency**: the plan comes from
`engine/runner.py::default_exploration_plan()`.

---

## Phase 2.5 (Marauder Hardware Spike) — Architectural Reference

> **Phase 2.7.4 removed `backends/` from the runtime.** Suryafool now owns
> its capability model, simulator, policy, and future hardware/runtime
> architecture. The [ESP32 Marauder project](https://github.com/justcallmekoko/ESP32Marauder)
> remains an **architectural reference** for future firmware design — it is
> NOT a runtime dependency, provider, or CLI option.
>
> The spike proved the `CapabilityProvider` ABC serves real hardware with no
> core changes. That proof informed the decision to keep the ABC generic
> (in `capabilities/base.py`) and remove the Marauder-specific plumbing
> (transport, parser, provider, CLI flags, tests).
>
> No `--provider`, `--port`, or `--baud` CLI flag exists today. The simulator
> is the only runtime provider. A future real-hardware backend plugs in by
> subclassing `CapabilityProvider` and registering via
> `registry.add_provider(...)`.

---

## Phase 2.7 (Stateful Active Simulator) — Quick Reference

Prove Suryafool can safely execute the **complete active chain** deterministically
— `discover → inspect → authorized active interaction → observe changed state` —
through the existing Phase 2.6 authorization gate. Adds two stateful *active*
capabilities that **mutate `BleDevice` entity objects** (not just `env.notes`),
so a subsequent passive observation reflects the change. No LLM, no hardware.

| Capability | Action | Authoritative risk | Authorization | State effect (on `BleDevice`) |
|---|---|---|---|---|
| `ble.discovery.connect` | active inspection | `SAFE_ACTIVE` | `--allow-risk safe_active` | `connected=True`, caches `gatt_services`, inits `characteristics` |
| `ble.discovery.write` | authorized interaction | `SENSITIVE_ACTIVE` | `--allow-risk sensitive_active` | `characteristics[char]=value` (observable in a later `inspect`) |

Both flow through the **unchanged** gate:
`Registry → cap.risk (authoritative) → AuthorizationScope → Policy → Provider`.
Active+inspection actions validate targets/args structurally — unknown id,
missing/malformed arg, non-connectable device, unconnected target, or unknown
characteristic all return a structured *failure* `Observation` (no exception, no
crashed run). The provider never decides safety.

```bash
# Full active lifecycle (lab target AA:BB:CC:00:00:01) + SENSITIVE_ACTIVE scope
python -m cli.phase2 run --scenario lab --plan active_inspection \
    --allow-risk sensitive_active --authorization-label "lab audit"

# Same plan, PASSIVE-only scope: connect+write are REJECTED at the gate
# (run still COMPLETED; environment unchanged — provider never reached)
python -m cli.phase2 run --scenario lab --plan active_inspection

# The default exploration plan is unchanged
python -m cli.phase2 run --scenario lab           # --plan exploration (default)
```

`--plan {exploration,active_inspection}` selects the deterministic plan.
The `active_inspection_plan()` is `discover → inspect → connect → write → inspect`
over the lab target — the final `inspect` shows
`connected; 1 characteristic(s) written`, proving the environment state actually
changed, whereas the initial `inspect` showed `not connected`.

```bash
python -m tests.test_phase27_active_sim   # 37 tests, stdlib-only runner
```

Cumulative `AuthorizationScope` boundary demonstrated by the new caps:
`--allow-risk safe_active` permits `connect` but **rejects** `write`;
`--allow-risk sensitive_active` permits both. No RESTRICTED action in Phase 2.7
(that would imply transmit/replay = attack; out of scope).

---

## Phase 2.7.1 (Capability Contract Metadata) — Quick Reference

Strengthen the **existing** `Capability` dataclass so it can describe Suryafool's
future multi-domain (wifi / ble / subghz / nfc / infrared / camera / ethernet /
usb) hardware/security operation surface **without** a second capability system.
Metadata is opt-in with safe defaults — every existing positional constructor
call keeps working.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `domain` | `str` | auto-derived from `capability.split('.', 1)[0]` | Wireless/network domain. Open-set; see `KNOWN_DOMAINS`. |
| `requires_args` | `tuple[str, ...]` | `()` | Required input arg names (descriptive; providers still validate structurally). |
| `output_entity_type` | `str` | `""` | Expected `Entity.type` of the Observation. `""` = unspecified. |
| `requires` | `tuple[str, ...]` | `()` | Prerequisite capability keys (e.g. `("ble.discovery.connect",)` for `ble.discovery.write`). |
| `hardware` | `str` | `""` | Declared hardware (`"esp32"`, `""` = sim-only). |
| `produces_evidence` | `bool` | `False` | Reserved for the future evidence/artifact pipeline. |
| `mutates_state` | `bool` | `False` | State-changing (`True` for `connect`, `write`, `nfc.read`, `subghz.analyze`). The **stateful vs observational** distinction. |

New methods/constants:
- `Capability.__post_init__()` — raises `ValueError` on empty `capability` or `action`; auto-derives `domain` if left blank.
- `Capability.prerequisites_met(observed_keys: set[str]) -> bool` — True iff every `requires` key is present in the observed set.
- `KNOWN_DOMAINS: frozenset[str]` — open-set vocabulary of the nine intended domains: wifi, ble, subghz, nfc, infrared, camera, ethernet, usb, **zigbee** (Phase 2.8.4; camera stays vocabulary-only). **Not enforced** — the catalogue may add new ones later.
- `simulator.simulator.performed_capability_keys(env) -> set[str]` — pure helper that derives the set of capability keys already exercised on an env, by translating the existing `env.notes` prefixes (`ble_connected:` → `ble.discovery.connect`, `ble_write:` → `ble.discovery.write`, `nfc_read:` → `nfc.discovery.read`, `subghz_analyzed:` → `subghz.discovery.analyze`). Passive actions don't stamp env.notes, so they never appear — proving the catalogue's `mutates_state=False` semantically.

Catalogue metadata mapping (declared per entry in `DEFAULT_CAPABILITIES`):

| Capability.action | domain | requires_args | output_entity_type | requires | mutates_state |
|---|---|---|---|---|---|
| wifi.discovery.discover | wifi | () | wifi_network | () | False |
| wifi.discovery.inspect | wifi | ("bssid",) | wifi_network | () | False |
| ble.discovery.discover | ble | () | ble_device | () | False |
| ble.discovery.inspect | ble | ("address",) | ble_device | () | False |
| ble.discovery.connect | ble | ("address",) | ble_device | () | True |
| ble.discovery.write | ble | ("address","characteristic","value") | ble_device | ("ble.discovery.connect",) | True |
| nfc.discovery.scan | nfc | () | nfc_tag | () | False |
| nfc.discovery.read | nfc | ("uid",) | nfc_tag | () | True |
| subghz.discovery.spectrum | subghz | () | subghz_signal | () | False |
| subghz.discovery.analyze | subghz | ("frequency_mhz",) | subghz_signal | () | True |

```bash
python -m cli.phase2 capabilities          # CLI surfaces (domain) + [STATEFUL|OBSERVE] per entry
python -m cli.phase2 capabilities --json  # JSON includes `domain` + `mutates_state` per entry
python -m tests.test_phase271_capability_metadata   # 33 tests, stdlib-only runner
```

Policy and authorization are unchanged. Phase 2.6 is the authority for risk
(`cap.risk`); `RiskDeclarationRule` and `RiskTierAuthorizedRule` are untouched.
A REJECTED action with `cap.mutates_state=True` is proven NOT to mutate env
state in `TestPolicyRejectDoesNotMutateState` — combining the new contract
flag with the standing Phase 2.6 gate.

---

## Phase 2.7.2 (Stateful Wi-Fi Capture Simulator) — Quick Reference

Prove Suryafool can safely execute the **complete Wi-Fi capture chain**
deterministically — `discover → inspect → capture.handshake → capture.pmkid
→ inspect` — through the existing Phase 2.6 authorization gate. Adds two
stateful *active* capabilities that **mutate `WifiNetwork` entity objects**
(not just `env.notes`), so a subsequent passive `wifi.discovery.inspect`
reflects the change. The `wifi.capture` namespace (NOT `wifi.discovery`)
encodes Risinek's capture-vs-discovery separation. No LLM, no hardware.

| Capability | Action | Authoritative risk | Authorization | State effect (on `WifiNetwork`) |
|---|---|---|---|---|
| `wifi.capture.handshake` | capture EAPOL 4-way frames | `SAFE_ACTIVE` | `--allow-risk safe_active` | `handshake_captured=True`, `captured_frames=4`; stamps `env.notes["wifi_handshake:<bssid>"]` |
| `wifi.capture.pmkid`     | capture PMKID frame | `SENSITIVE_ACTIVE` | `--allow-risk sensitive_active` | `pmkid_captured=True`; stamps `env.notes["wifi_pmkid:<bssid>"]`; per-target prereq: same bssid must have `handshake_captured=True` |

Both flow through the **unchanged** gate: `Registry → cap.risk
(authoritative) → AuthorizationScope → Policy → Provider`. The capture
handlers validate `encryption in {WPA2, WPA3}` — `OPEN`/`WEP` are
rejected with a structured failure Observation (no mutation, no crash).
`wifi.capture.pmkid` additionally enforces the per-target handshake
prereq: `wifi.capture.handshake` must have run on the SAME bssid (this is
stricter than the catalogue-level `requires` tuple, which only proves
"some handshake ran somewhere").

```bash
# Full Wi-Fi capture lifecycle (lab target 02:00:00:00:00:01, LAB-INTERNAL WPA3) + SENSITIVE_ACTIVE scope
python -m cli.phase2 run --scenario lab --plan wifi_capture \
    --allow-risk sensitive_active --authorization-label "lab capture audit"

# Same plan, PASSIVE-only scope: capture.handshake + capture.pmkid are REJECTED at the gate
# (run still COMPLETED; environment unchanged — provider never reached)
python -m cli.phase2 run --scenario lab --plan wifi_capture

# SAFE_ACTIVE scope: capture.handshake ALLOWs, capture.pmkid REJECTs at tier gate
python -m cli.phase2 run --scenario lab --plan wifi_capture --allow-risk safe_active
```

```bash
python -m tests.test_phase272_wifi_capture    # 36 tests, stdlib-only runner
```

Catalogue grows from 10 → 12 entries.

---

## Phase 2.7.3 (Stateful BLE GATT Simulator) — Quick Reference

Prove Suryafool can safely execute the **complete BLE GATT stateful chain**
deterministically — `discover → inspect → connect (Phase 2.7) → ble.gatt.pair
→ ble.gatt.write → inspect` — through the existing Phase 2.6 authorization
gate. Adds two stateful *active* capabilities that **mutate `BleDevice`
entity objects** (`paired`, `secure_characteristics`) so a subsequent passive
`ble.discovery.inspect` reflects the change. The new `ble.gatt` namespace
sits **alongside** `ble.discovery` — exactly parallel to how Phase 2.7.2's
`wifi.capture` namespace sits alongside `wifi.discovery`: encoding the
Risinek-style capture-vs-discovery separation inside Suryafool's own typed
capability model. No LLM, no hardware.

| Capability | Action | Authoritative risk | Authorization | State effect (on `BleDevice`) |
|---|---|---|---|---|
| `ble.gatt.pair`  | establish BLE secure pairing/bonding | `SAFE_ACTIVE` | `--allow-risk safe_active` | `paired=True`, inits `secure_characteristics` `{svc: ""}`; stamps `env.notes["ble_paired:<addr>"]`; per-target prereq `b.connected=True` (legacy `ble.discovery.connect` Phase 2.7) |
| `ble.gatt.write` | encrypted GATT characteristic write within the paired session | `SENSITIVE_ACTIVE` | `--allow-risk sensitive_active` | `secure_characteristics[char]=str(value)`; stamps `env.notes["ble_secure_write:<addr>:<char>"]`; per-target prereq `b.paired=True` (the new `ble.gatt.pair` on the SAME address) |

Both flow through the **unchanged** Phase 2.6 gate:
`Registry → cap.risk (authoritative) → AuthorizationScope → Policy → Provider`.
`ble.gatt.pair` validates `b.connectable=True` (link-layer restriction) and
`b.connected=True` (per-target prereq — the catalogue-level
`requires=("ble.discovery.connect",)` only proves *some* connect ran
somewhere; the simulator enforces the same-address gate). `ble.gatt.write`
validates that `characteristic` is a known `b.gatt_services` entry — refusing
unknown characteristics with a structured failure Observation. Any invalid
input (missing/non-string address, `None` value, unknown address,
not-connectable / unconnected / unpaired target) returns a structured failure
Observation with no env mutation, no crash.

```bash
# Full BLE GATT lifecycle (lab target AA:BB:CC:00:00:01) + SENSITIVE_ACTIVE scope
python -m cli.phase2 run --scenario lab --plan ble_gatt_workflow \
    --allow-risk sensitive_active --authorization-label "lab GATT audit"

# Same plan, PASSIVE-only scope: connect, pair, and write are all REJECTED
# at the policy gate (run still COMPLETED; environment unchanged — provider
# never reached). 3 errors recorded for the 3 rejected active actions.
python -m cli.phase2 run --scenario lab --plan ble_gatt_workflow

# SAFE_ACTIVE scope: connect + pair ALLOW, gatt.write REJECTs at the tier
# gate (cumulative stops at the first SENSITIVE_ACTIVE action). The
# connect + pair env mutations land; the secure write does NOT.
python -m cli.phase2 run --scenario lab --plan ble_gatt_workflow --allow-risk safe_active
```

```bash
python -m tests.test_phase273_ble_gatt    # 47 tests, stdlib-only runner
```

Catalogue grows from 12 → 14 entries. The Phase 2.7
`ble.discovery.connect`/`ble.discovery.write` and the Phase 2.7.2
`wifi.capture.handshake`/`wifi.capture.pmkid` behaviours are preserved
identically — the new `ble.gatt.*` layer adds session-pairing and encrypted
writes *on top of* the existing link-level BLE/GATT discovery operations.

---

## Phase 2.7 — FREEZE / HANDOFF (subphase 2.7.9 complete)

> **This is the handoff summary for the next major OpenCode session.**
> `AGENTS.md` roster + the per-directory `CONTEXT.md` files are the
> canonical phase-2.7 documentation; this section is the compressed
> contract table a Phase 2.8 session must not violate.

### Final contract (frozen)

| Item | Final value |
|---|---|
| Capability catalogue | **14 entries** (wifi.discovery 2, wifi.capture 2, ble.discovery 4, ble.gatt 2, nfc.discovery 2, subghz.discovery 2) |
| Evidence producers | **4**: `wifi.capture.handshake` (`wifi_eapol_handshake`), `wifi.capture.pmkid` (`wifi_pmkid`), `ble.gatt.pair` (`ble_pairing`), `ble.gatt.write` (`ble_secure_write`) |
| Evidence kinds | `KNOWN_EVIDENCE_KINDS` = `{wifi_eapol_handshake, wifi_pmkid, ble_pairing, ble_secure_write}` |
| Risk model (authoritative) | `cap.risk` is authoritative; `RiskDeclarationRule` rejects caller downgrade/upgrade; tiers PASSIVE < SAFE_ACTIVE < SENSITIVE_ACTIVE < RESTRICTED |
| Authorization | `AuthorizationScope` — PASSIVE always allowed; `with_cumulative_tier` for CLI `--allow-risk`; disjoint `with_tiers` for exact grants |
| Prerequisites | catalogue-level `requires` (planning) + **simulator per-target gate** (same bssid/address) — both enforced |
| Deterministic plans | `default_exploration_plan` (4), `active_inspection_plan` (5), `wifi_capture_plan` (5), `ble_gatt_workflow_plan` (6) |
| Evidence wiring | `Observation.evidence` → engine mirrors to `ActionRecord.evidence` + `Run.evidence`, stamps `source_action_id`, emits one `evidence.created` per item; `run.json` round-trips; old run.json back-compat (`evidence` absent → `[]`) |
| JSONL events | `agent.status`, `finding.created`, `evidence.created`, `error`, `log` (+ command/scan events) — Python `core/events.py` ↔ `suryafool-cli/src/backend/events.js` synced |
| TUI | `--json` streams consumed by OutputParser; `Evidence` tab (EvidenceFeed) renders `evidence.created` live; `evidenceFormat.js` `formatEvidenceLine` |
| HTML | top-level EVIDENCE section + per-action evidence blocks; empty run renders "No evidence captured by this run." |

### Final test counts

- Python: **14 suites / 472 tests**, all green (`test_phase2_core` 21, `test_phase26_authorization` 14, `test_phase27_active_sim` 34, `test_phase271` 34, `test_phase272` 35, `test_phase273` 48, `test_phase275` 37, `test_phase276` 31, `test_phase277` 30, `test_phase279` 26, `test_phase280_multidomain` 29, `test_phase281` 40, `test_phase282_nfc_read` 53, `test_phase283_ir` 40).
- Node: **55 tests** (`node --test` in `suryafool-cli`) + **2 smoke scripts** (`test_phase2_cmds.cjs`, `test_phase2_wiring.cjs`), `npm run build` (esbuild) clean.

### Known limitations (Phase 2.7)

- **Simulator only** — no real hardware; `CapabilityProvider` ABC + `registry.add_provider()` are the (untested-against-hardware) seams.
- Evidence is **run-local** (run.json + JSONL + HTML + TUI session); no cross-run evidence store/artifact generalization yet.
- Evidence kinds limited to the 4 above; Sub-GHz / NFC / IR / camera / ethernet / usb **do not** produce evidence.
- No LLM in the loop — plans are deterministic; the orchestrator/agents are Phase 3+.
- Single-threaded deterministic engine; no concurrency/queues.
- `ble.discovery.connect`/`ble.discovery.write` (Phase 2.7) do **not** produce evidence (only `ble.gatt.*`).
- TUI EvidenceFeed is a live session panel — no historical evidence browsing beyond regeneration from `run.json`.

### What Phase 2.8 may safely build on

- An **LLM-driven plan/orchestrator** on top of the unchanged gate
  (`Registry.resolve → cap.risk → AuthorizationScope → Policy → Provider`),
  planning via `Capability.prerequisites_met(performed_capability_keys(env))`.
- **Real hardware backends** by subclassing `CapabilityProvider` + `registry.add_provider(...)`; transport is Suryafool-owned (Marauder spike removed in 2.7.4).
- Cross-run **artifact/evidence store** generalizing the `EvidenceRecord` provenance model.
- New evidence kinds / domains by extending `KNOWN_EVIDENCE_KINDS` + catalogue flags + a handler success path — no pipeline change required (proven by 2.7.5→2.7.7).

### What Phase 2.8 must not break

- **Determinism**: same seed → same observations/evidence semantics.
- **Gate order**: policy rejection happens **before** the provider; rejected actions produce **zero evidence** and no env mutation.
- **Authoritative risk**: never trust `request.risk`; resolve `cap.risk` once per action and persist it.
- **Per-target prerequisites** in the simulator handlers (same bssid / same address).
- **Evidence only on success**: failure paths must keep `evidence=[]`.
- **run.json schema** (incl. `evidence` fields + old-file back-compat), **JSONL event contract**, **HTML EVIDENCE section**, **TUI event handling**.
- **Catalogue of 14** + the 4 `produces_evidence=True` flags already declared. Phase 2.8.0 APPENDED 7 multi-domain entries (21 total) without altering the 14 or their evidence flags; future subphases must likewise extend by appending only.

| **Phase 2.8.1 Sub-GHz/RF Capture Slice** | `/capabilities`, `/simulator`, `/core`, `/engine`, `/cli`, `/tests`, `/suryafool-cli` | 🟢 Complete — first real Sub-GHz/RF vertical slice on the frozen Phase 2.7 stack + Phase 2.8.0 multi-domain foundation. ONE new stateful capability (`subghz.capture.signal` SAFE_ACTIVE, `produces_evidence=True`) in a NEW `subghz.capture` namespace parallel to `wifi.capture`/`ble.gatt`; the existing `subghz.discovery.analyze` capability is upgraded with per-target prereq + evidence (`produces_evidence` False→True). Catalogue grows **21 → 22** (one append; no existing entries reshaped). `SubGhzSignal` gains `captured`/`sample_count`/`capture_quality`/`decoded_protocol_hint` state; capture sets them + builds `subghz_capture` `EvidenceRecord`; analyze now REJECTs targets not captured on the SAME frequency (per-target gate in the simulator, catalogue `requires=()` unchanged — exactly mirrors `wifi.capture.pmkid`'s same-bssid gate) and on success sets a deterministic `decoded_protocol_hint` (heuristic map: 433.92 OOK→remote_control, 868.30 FSK→LoRa_like, etc.) + builds `subghz_analysis` evidence. `KNOWN_EVIDENCE_KINDS` grows 4 → 6 (the four Phase 2.7 producers preserved as a subset). New `subghz_capture_plan()` — 5 actions (spectrum → capture@433.92 → analyze@433.92 → capture@868.30 → analyze@868.30) → 4 evidence (2 capture + 2 analysis). All failure paths (unknown frequency, not-captured target, malformed args, OPEN/uncaptured prereq, policy-rejected) produce zero evidence + zero env mutation; the Phase 2.6 policy gate is unchanged (PASSIVE-only → 4 REJECTs, 0 evidence). `decoded_protocol_hint` is a hint, NOT a decoder (no payloads in the simulator). 34 new stdlib-runnable tests (`test_phase281_subghz_capture.py`) + 11 prior Python suites' count guards bumped 21→22 + Phase 2.7/2.8.0 contract-audit assertions updated; TUI JS suite gains 3 subghz-format assertions (forward-linked from Python). 12 Python suites (377 tests) + 53 JS tests + esbuild build + 2 Node smokes all green. **No LLM, no hardware, no RF transmission/replay, no attack code, no evidence-system or policy changes.** |

| **Phase 2.8.2 NFC/RFID Read Slice** | `/capabilities`, `/simulator`, `/engine`, `/cli`, `/tests`, `/suryafool-cli` | 🟢 Complete — first real NFC/RFID vertical slice on the frozen Phase 2.7 stack + Phase 2.8.0/2.8.1 foundation. ONE new capability (`nfc.discovery.select` PASSIVE, `mutates_state=True`) in the existing `nfc.discovery` namespace; existing `nfc.discovery.read` upgraded with `produces_evidence=True` (kind `nfc_read`) + per-target `t.selected=True` prereq (mirroring Sub-GHz analysis). Catalogue grows **22 → 23** by appending one entry. `NfcTag` gains `selected`/`read`/`read_at`/`ndef_supported` fields. New evidence kind `nfc_read` (read → NDEF records; concise metadata: uid, tag_type, ndef_supported, records_count, technology). New `nfc_workflow_plan()` — 5 actions (scan→select→read on each of 2 lab tags). Total `KNOWN_EVIDENCE_KINDS` now 7. Phase 2.8.2 adds 1 more evidence producer (nfc.discovery.read) + one new HANDLER (select). 53 new stdlib-runnable tests (`test_phase282_nfc_read.py`) + all prior suites green. No LLM, no hardware, no NFC write/replay. |
| **Phase 2.8.3 Infrared (IR) Slice** | `/capabilities`, `/simulator`, `/engine`, `/cli`, `/tests`, `/suryafool-cli` | 🟢 Complete — first real Infrared vertical slice on the frozen Phase 2.7 stack + Phase 2.8.0/2.8.1/2.8.2 foundation, implemented entirely on the Phase 2.8.0 catalogue surface (NO new catalogue entries; the three `infrared.*` entries flip from registered-but-unsupported to supported). `infrared.capture` stays PASSIVE/observational/no-evidence (parallels discover/scan); existing `infrared.analyze` (SAFE_ACTIVE, requires_args `capture_id`) and `infrared.transmit` (SENSITIVE_ACTIVE, `requires=("infrared.capture",)`) upgraded `produces_evidence` False→True + per-target prereq gates in the simulator. `IrSignal` gains `layout`/`frequency_khz`/`carrier_duty_cycle`/`protocol_hint`/`transmitted` state; `action_ir_capture` sets them (no mutation of env beyond the entity). `action_ir_analyze` REJECTs surreptitious/unknown capture_id (structured failure Observation, zero evidence/zero mutation) and on success builds an `ir_analysis` `EvidenceRecord` (metadata: capture_id, protocol_hint, frequency_khz, carrier_duty_cycle, layout — concise, no fake blobs); `action_ir_transmit` enforces SAMЕ-capture_id analyzed=True per-target prereq + `s.transmitted=True` + builds `ir_transmit` evidence. Heuristic `_ir_protocol_hint` (38.0kHz/900ms→NEC, 36.0kHz/560ms→RC5, else other) + `_ir_classification` (short/long/unknown) — hints, NOT a decoder (no payload bytes in the simulator). `KNOWN_EVIDENCE_KINDS` grows **7 → 9** (+`ir_analysis`, `ir_transmit`; the Phase 2.7 four + Phase 2.8.1 two + Phase 2.8.2 one preserved as subset). New `ir_workflow_plan()` — 4 actions (capture → analyze@ir-lab-remote → transmit@ir-lab-remote → analyze@ir-lab-tv) → 3 evidence. All failure paths (unknown/malformed capture_id, not-analyzed target, policy rejection) produce zero evidence + zero env mutation; the Phase 2.6 policy gate unchanged (PASSIVE-only → 3 REJECTs, 0 evidence.created). 40 new stdlib-runnable tests (`test_phase283_ir.py`) + all 13 prior suites green; TUI JS suite gains 3 IR-format assertions (forward-linked from Python). Catalogue stays 23; evidence producers grow to **9**. No LLM, no hardware, no IR transmission/replay, no policy/evidence-system changes. 14 Python suites (472 tests) + 58 Node tests + esbuild build + 2 Node smokes all green. |
| **Phase 2.8.4 Zigbee Mesh Slice** | `/capabilities`, `/simulator`, `/core`, `/engine`, `/cli`, `/tests`, `/suryafool-cli` | 🟢 Complete — a new Zigbee wireless-mesh domain staked in ONE phase with handlers (NOT the 2.8.0 registered-but-unsupported-then-flip route — the brand-new `zigbee` domain resolves `supported=True` immediately). Catalogue grows **23 → 26** by APPENDING three `zigbee.discovery.*` entries after USB: `scan` (PASSIVE, out `zigbee_network`), `inspect` (PASSIVE, requires_args `pan_id`, out `zigbee_node`), `join` (SAFE_ACTIVE, requires_args `pan_id`+`ieee_address`, out `zigbee_node`, `mutates_state=True`, `produces_evidence=True`). `KNOWN_DOMAINS` grows 8 → 9 (+`zigbee`; camera stays vocabulary-only). Two honest mesh entities — `ZigbeeNetwork` (pan_id, extended_pan_id, channel, rssi, prefix, node_count) + `ZigbeeNode` (ieee_address, short_address, role, network, **parent_short_address** child→parent link, lqi, joined) — so the "mesh" is real simulator state, not decorative data. Lab scenario gains a full mesh (PAN `0x1A2B` ch15: coordinator `...:01` 0x0000, router `...:02` 0x0001→0x0000, end_device `...:03` 0x0002→0x0001, UNJOINED join target `...:04`, node_count=3); home a smaller mesh (PAN `0x2C3D`). New `action_zigbee_scan` (PASSIVE) + `action_zigbee_inspect` (PASSIVE, per-PAN node list + topology) + `action_zigbee_join` (SAFE_ACTIVE — per-target gates: network exists + node exists + NOT already joined; success assigns next short `0x0003`, sets parent to the first router else coordinator `0x0001`, `lqi=220`, `joined=True`, stamps `env.notes["zigbee_joined:<ieee>"]` — and **`_zigbee_network_entities` recomputes node_count LIVE from joined nodes** so a later `scan`/`inspect` reflects the join). New `zigbee_workflow_plan()` — 4 actions (scan → inspect@0x1A2B → join@0x1A2B/`...:04` → inspect@0x1A2B) → 1 `zigbee_join` `EvidenceRecord` (metadata: ieee_address, network, assigned_short_address, parent_short_address, role, lqi — a real transition, no fake blob). All failure paths (unknown PAN, unknown node, already-joined node, malformed args, policy rejection) produce zero evidence + zero env mutation; the Phase 2.6 policy gate unchanged (PASSIVE-only → join REJECTed before provider, 0 evidence.created). `KNOWN_EVIDENCE_KINDS` grows 9 → 10 (+`zigbee_join`); producers 9 → 10. 51 new stdlib-runnable tests (`test_phase284_zigbee.py`) + count/kinds/producers guards bumped 23→26 across 8 prior suites (27/271/272/273/275/276/277/279/280/281/282/283); TUI JS suite gains 2 Zigbee-format assertions (forward-linked from Python: `zigbee_join` → domain `other`). Reports/JSONL/TUI reuse the generic evidence pipeline — no report/event/TUI code changes. No LLM, no hardware, no RF transmission/replay, no attack code, no policy/evidence-system changes. 15 Python suites (**523 tests**) + 60 JS tests + esbuild build + 2 Node smokes all green. |

---

## Phase 2.8 — Roadmap (2.8.4 declared COMPLETE)

Established: multi-domain catalogue surface (26 entries) on the FROZEN Phase 2.7 stack; registered-but-unsupported semantics (harmless policy REJECT before provider); `IrSignal` / `EthernetHost` / `UsbDevice` + `ZigbeeNetwork`/`ZigbeeNode` entity substrate + empty `Environment.ir/ethernet/usb` + populated `Environment.zigbee_networks/zigbee_nodes`; CLI `capabilities` `supported` field.

| Subphase | Scope | Catalogue lean |
|---|---|---|
| **2.8.0** ✅ | Multi-domain foundation (this) | 21 entries (7 new, unsupported) |
| 2.8.1 ✅ | Sub-GHz / RF — stateful capture/analyze on `SubGhzSignal` | existing surface + handlers |
| 2.8.2 ✅ | NFC / RFID — card read/write states, evidence-worthy capture | existing surface + handlers |
| 2.8.3 ✅ | Infrared — `capture`/`analyze`/`transmit` handlers on `IrSignal` | infra entries become supported |
| 2.8.4 ✅ | Zigbee mesh — `scan`/`inspect`/`join` on `ZigbeeNetwork`/`ZigbeeNode` | +3 zigbee entries (23 → 26), supported |
| 2.8.5 | Ethernet / Network — `discover`/`inspect` handlers on `EthernetHost` | ethernet entries become supported |
| 2.8.6 | USB — `enumerate`/`inspect` handlers on `UsbDevice` | usb entries become supported |
| 2.8.7 | Cross-domain deterministic workflows (multi-protocol plans) | — |
| 2.8.8 | Evidence/analysis generalization across new domains | new evidence kinds when real producers exist |
| 2.8.9 | Phase 2.8 integration / freeze | contract audit |

Per-subphase rule: **`produces_evidence=True` only when a real implemented producer exists**; no evidence kinds/machinery added speculatively.

---

## LLM Provider Stack

| Provider | Package | Env var | Priority |
|---|---|---|---|
| OpenRouter | `langchain-openai` | `OPENROUTER_API_KEY` | Primary |
| OpenCode Zen | `langchain-openai` | `OPENCODE_API_KEY` | Fallback |

Provider selection is automatic with fallback: OpenRouter (10s timeout) → OpenCode Zen (10s timeout) → graceful "LLM unavailable".

Model: NVIDIA Nemotron 3 Ultra (free tier) on both endpoints.

---

## Hardware Targets (MVP)

| Hardware | Protocols | Role |
|---|---|---|
| ESP32 | Wi-Fi, BLE | Discovery + passive observation |
| CC1101 | Sub-GHz | Signal capture + transmission |
| NFC/RFID module | NFC, RFID | Detection + inspection |
| IR Tx/Rx | Infrared | Capture + replay |

Budget: ₹3,000 maximum (MVP hardware).

---

## OS Support Matrix

The Bootstrap Agent must handle all three platforms:

| Platform | WSL needed | USB access | Package manager |
|---|---|---|---|
| Windows | Yes (WSL2 + usbipd) | Via usbipd passthrough | winget / apt (inside WSL) |
| Linux | No | Native | apt / pip |
| macOS | No | Native | Homebrew / pip3 |

OS detection lives in [`bootstrap/platform.py`](bootstrap/platform.py). **Never use `sys.platform` directly elsewhere — import from there.**

---

## Core Design Rules

These are non-negotiable. Do not violate them.

### 1. LLM = diagnosis and interpretation only
The LLM never generates shell commands from scratch. Every command that mutates the system comes from a **human-authored, version-controlled manifest**. The model selects which manifest entry to apply — it does not write new commands.

### 2. Scope Guardian is deterministic
The Scope Guardian for wireless missions is **not** a prompt or advisory layer. It is a deterministic code gate. An LLM cannot reason its way past it.

### 3. Provisioning Guardian mirrors this for bootstrap
The Provisioning Guardian in `/bootstrap` applies the same principle to system setup: any `requires_elevation: windows_admin|wsl_sudo` entry always pauses and shows the exact command to the human before execution.

### 4. Passive is the default
Agents default to passive observation. Active interactions require explicit mission scope. Security testing requires Lab Mode with explicit authorized targets.

### 5. All agent actions are logged
No silent mutations. Every action the agent takes must produce a log entry.

### 6. Platform detection is centralized
Use `bootstrap/platform.py → current_os()`. Never scatter `sys.platform` checks.

### 7. Manifest is never LLM-generated
`bootstrap/manifest.yaml` is the ground truth for "ready". The LLM cannot modify it at runtime.

---

## Key Capability Abstractions (HAL)

Agents reason using these operations, not hardware specifics:

```
DISCOVER  OBSERVE  CAPTURE  IDENTIFY  ANALYZE
COMPARE   CORRELATE  EXPERIMENT  INTERACT  TEST  VERIFY
```

Hardware modules register which operations they support in the **Capability Registry** (planned: `/capability_registry`).

---

## Mission Data Model (planned)

A mission contains:
- `objective` — natural-language goal
- `authorization_scope` — what targets are permitted
- `available_capabilities` — from the Capability Registry
- `observations` — raw wireless data
- `hypotheses` — agent-generated, with confidence levels
- `planned_actions` — queued next steps
- `executed_actions` — full history
- `evidence` — findings with provenance
- `agent_reasoning_state` — per-agent scratchpad
- `results` — final report

---

## Confidence Levels

Signal Intelligence Agent and Device Intelligence Agent must tag all conclusions:

```
CONFIRMED  |  LIKELY  |  POSSIBLE  |  UNKNOWN
```

Never collapse these into a boolean. Preserve uncertainty.

---

## When Adding a New Agent

1. Create `/agents/<name>/` directory with its own `CONTEXT.md`.
2. Define the agent's tools as plain Python functions — no LLM-generated side effects.
3. Register any active tools with the Scope Guardian before wiring them.
4. Add the agent to the roster table in this file.
5. Update the root `CONTEXT.md` implementation status.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
