# CONTEXT.md — Suryafool (Root)

> **For AI coding assistants:** This file describes the root of the Suryafool repository.
> Also read [`AGENTS.md`](AGENTS.md) before making changes.

---

## Project Identity

**Suryafool** is a universal agentic wireless platform.

It gives autonomous AI agents the ability to perceive, explore, investigate and interact with heterogeneous wireless environments (Wi-Fi, BLE, Sub-GHz, NFC, RFID, IR) through modular radio hardware — including safely conducting autonomous security research within explicitly authorized lab environments.

---

## Implementation Status

| Component | Status | Location |
|---|---|---|
| Product Requirements | ✅ Complete | [`docs/PRD.md`](docs/PRD.md) |
| Architecture (Bootstrap) | ✅ Complete | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| OS detection | ✅ Done | [`bootstrap/platform.py`](bootstrap/platform.py) |
| Dependency manifest | ✅ Done | [`bootstrap/manifest.yaml`](bootstrap/manifest.yaml) |
| Check runner | ✅ Done | [`bootstrap/checks.py`](bootstrap/checks.py) |
| Remediation runner | ✅ Done | [`bootstrap/remediate.py`](bootstrap/remediate.py) |
| Provisioning Guardian | ✅ Done | [`bootstrap/provisioning_guardian.py`](bootstrap/provisioning_guardian.py) |
| Bootstrap agent loop | ✅ Done | [`bootstrap/agent.py`](bootstrap/agent.py) |
| LLM factory + rate limiter | ✅ Done | [`core/llm.py`](core/llm.py) |
| Cyberpunk CLI (Ink/React TUI) | ✅ Complete (v0.1.0, Level 1000) | [`suryafool-cli/`](suryafool-cli/) |
| CLI State Management | ✅ Complete | [`suryafool-cli/src/state/`](suryafool-cli/src/state/) |
| CLI Backend Integration | ✅ Complete | [`suryafool-cli/src/backend/`](suryafool-cli/src/backend/) |
| CLI Full-screen TUI | ✅ Complete | [`suryafool-cli/src/app.js`](suryafool-cli/src/app.js) |
| CLI Components (12) | ✅ Complete | [`suryafool-cli/src/components/`](suryafool-cli/src/components/) |
| Phase 2 core types | ✅ Complete | [`core/mission.py`](core/mission.py), [`core/observation.py`](core/observation.py), [`core/confidence.py`](core/confidence.py) |
| Phase 2 capability registry | ✅ Complete | [`capabilities/`](capabilities/) |
| Phase 2 wireless simulator | ✅ Complete | [`simulator/`](simulator/) |
| Phase 2 policy layer | ✅ Complete | [`policy/policy.py`](policy/policy.py) |
| Phase 2 run engine + logging | ✅ Complete | [`engine/`](engine/) |
| Phase 2 HTML report | ✅ Complete | [`reports/html_report.py`](reports/html_report.py) |
| Phase 2 CLI | ✅ Complete | [`cli/phase2.py`](cli/phase2.py) |
| Phase 2.5 Marauder hardware backend (spike) | 🟡 Architectural reference only | ~~`backends/marauder/`~~, ~~`backends/transport.py`~~ — removed in Phase 2.7.4; [ESP32 Marauder](https://github.com/justcallmekoko/ESP32Marauder) remains a reference for future firmware design |
| Phase 2.6 Explicit AuthorizationScope + hardened policy | ✅ Complete | [`core/mission.py`](core/mission.py) (`AuthorizationScope`, `_RISK_SEVERITY`, `Run.authorization`, `ActionRecord.authoritative_risk`), [`policy/policy.py`](policy/policy.py) (`RiskTierAuthorizedRule`, strengthened `RiskDeclarationRule`), [`engine/runner.py`](engine/runner.py) (scenario decoupled), [`cli/phase2.py`](cli/phase2.py) (`--allow-risk`, `--authorization-label`), [`reports/html_report.py`](reports/html_report.py) (Authorization line) |
| Phase 2.7 Stateful Active Simulator | ✅ Complete | [`simulator/simulator.py`](simulator/simulator.py) (`action_ble_connect`, `action_ble_write`), [`capabilities/base.py`](capabilities/base.py) (`ble.discovery.connect`, `ble.discovery.write` in `DEFAULT_CAPABILITIES`), [`engine/runner.py`](engine/runner.py) (`active_inspection_plan`), [`cli/phase2.py`](cli/phase2.py) (`--plan active_inspection`) |
| Phase 2.7.1 Capability contract metadata | ✅ Complete | [`capabilities/base.py`](capabilities/base.py) (`Capability` extended with `domain`, `requires_args`, `output_entity_type`, `requires`, `hardware`, `produces_evidence`, `mutates_state`; `__post_init__`; `prerequisites_met()`; `KNOWN_DOMAINS`), [`simulator/simulator.py`](simulator/simulator.py) (`performed_capability_keys(env)`), [`cli/phase2.py`](cli/phase2.py) (`cmd_capabilities` surfaces `domain` + `mutates_state`) |
| Phase 2.7.2 Stateful Wi-Fi capture simulator | ✅ Complete | [`simulator/entities.py`](simulator/entities.py) (`WifiNetwork` += `handshake_captured`, `captured_frames`, `pmkid_captured`), [`capabilities/base.py`](capabilities/base.py) (`wifi.capture.handshake` SAFE_ACTIVE + `wifi.capture.pmkid` SENSITIVE_ACTIVE in `DEFAULT_CAPABILITIES` — 12 total), [`simulator/simulator.py`](simulator/simulator.py) (`action_wifi_capture_handshake`, `action_wifi_capture_pmkid` + `HANDLERS` + `_NOTE_PREFIX_TO_CAPABILITY_KEY` += `wifi_handshake:`/`wifi_pmkid:`; `action_wifi_inspect` surfaces capture state), [`engine/runner.py`](engine/runner.py) (`wifi_capture_plan`), [`cli/phase2.py`](cli/phase2.py) (`--plan wifi_capture`) |
| Phase 2.7.3 Stateful BLE GATT simulator | ✅ Complete | [`simulator/entities.py`](simulator/entities.py) (`BleDevice` += `paired`, `secure_characteristics`), [`capabilities/base.py`](capabilities/base.py) (`ble.gatt.pair` SAFE_ACTIVE + `ble.gatt.write` SENSITIVE_ACTIVE in `DEFAULT_CAPABILITIES` — 14 total), [`simulator/simulator.py`](simulator/simulator.py) (`action_ble_gatt_pair`, `action_ble_gatt_write` + `HANDLERS` + `_NOTE_PREFIX_TO_CAPABILITY_KEY` += `ble_paired:`/`ble_secure_write:`; `action_ble_inspect` surfaces paired + secure-write state), [`engine/runner.py`](engine/runner.py) (`ble_gatt_workflow_plan`), [`cli/phase2.py`](cli/phase2.py) (`--plan ble_gatt_workflow`) |
| Phase 2.7.4 Marauder decoupling | ✅ Complete | `backends/` directory removed; `tests/test_phase25_marauder.py` removed; `marauder_discovery_plan` removed; `--provider`/`--port`/`--baud` CLI flags removed; `MarauderProvider` import + `default_registry(provider_name=...)` branch removed; `available_providers()` returns `["simulator"]` only; marauder-specific regression tests stripped from Phase 2.6/2.7/2.7.2/2.7.3 suites; `capabilities/base.py` `hardware` field docstring updated; Node `test_phase2_cmds.cjs` marauder steps removed. 6 Python suites + 2 Node smoke tests green. The [ESP32 Marauder project](https://github.com/justcallmekoko/ESP32Marauder) remains an architectural reference only. |
| Phase 2.7.5 First evidence-producing capability | ✅ Complete | [`core/evidence.py`](core/evidence.py) (`EvidenceRecord` + `KNOWN_EVIDENCE_KINDS`), [`core/observation.py`](core/observation.py) (`Observation.evidence: list[EvidenceRecord]`), [`core/mission.py`](core/mission.py) (`ActionRecord.evidence` + `Run.evidence` + to_dict/from_dict round-trip with old-run back-compat), [`core/events.py`](core/events.py) (`EVIDENCE_CREATED`), [`suryafool-cli/src/backend/events.js`](suryafool-cli/src/backend/events.js) (Node mirror), [`simulator/simulator.py`](simulator/simulator.py) (`action_wifi_capture_handshake` success path builds an `EvidenceRecord` with realistic metadata; failure paths return `evidence=[]`), [`capabilities/base.py`](capabilities/base.py) (`wifi.capture.handshake` catalogue entry now `produces_evidence=True`), [`engine/runner.py`](engine/runner.py) (mirrors `observation.evidence` to `record.evidence` + `run.evidence`, stamps `source_action_id`, emits `evidence.created` JSONL event per item; rejected actions never reach this path), [`reports/html_report.py`](reports/html_report.py) (per-action evidence + top-level EVIDENCE section with provenance), [`cli/phase2.py`](cli/phase2.py) (`cmd_capabilities` surfaces `produces_evidence`; `cmd_show` prints evidence count) |
| Phase 2.7.6 Generalize evidence to PMKID capture | ✅ Complete | [`core/evidence.py`](core/evidence.py) (`KNOWN_EVIDENCE_KINDS` += `wifi_pmkid`), [`capabilities/base.py`](capabilities/base.py) (`wifi.capture.pmkid` catalogue entry now `produces_evidence=True` — the wifi.capture pair is now the only evidence-producing namespace, all other 12 entries stay `False`), [`simulator/simulator.py`](simulator/simulator.py) (`action_wifi_capture_pmkid` success path builds a `wifi_pmkid` `EvidenceRecord` with realistic metadata incl. `handshake_prereq`; failure + prereq-failure + invalid-target paths return `evidence=[]`). Same 2.7.5 pipeline unchanged: `Observation.evidence` → engine mirrors to `ActionRecord.evidence` + `Run.evidence` → `evidence.created` JSONL → HTML EVIDENCE section. Per-target handshake prereq REMAINS enforced (no evidence without a prior handshake on the SAME bssid). `tests/test_phase276_pmkid_evidence.py` — 32 stdlib-runnable tests + all 7 prior suites + 2 Node smokes green |
| Phase 2.7.7 Cross-domain BLE evidence | ✅ Complete | [`core/evidence.py`](core/evidence.py) (`KNOWN_EVIDENCE_KINDS` += `ble_pairing`, `ble_secure_write`), [`capabilities/base.py`](capabilities/base.py) (`ble.gatt.pair` + `ble.gatt.write` catalogue entries now `produces_evidence=True` — the 4 capability evidence producers are wifi.capture handshake/pmkid + ble.gatt pair/write; the other 10 entries stay `False`), [`simulator/simulator.py`](simulator/simulator.py) (`action_ble_gatt_pair` builds a `ble_pairing` `EvidenceRecord` on success only; `action_ble_gatt_write` builds a `ble_secure_write` `EvidenceRecord` on success only; all invalid-input / unknown-characteristic / not-connectable / unconnected / unpaired / policy-rejected paths return `evidence=[]`). Same 2.7.5 pipeline unchanged — no JSONL/HTML/policy changes. Per-address prerequisites REMAIN enforced (pair needs connect, secure write needs pair, both on the SAME address). Wi-Fi handshake + PMKID evidence unchanged. Existing BLE state transitions + inspection behavior preserved. `tests/test_phase277_ble_evidence.py` — 30 stdlib-runnable tests + all 8 prior suites + 2 Node smokes green |
| Phase 2.7.8 Live evidence surfacing in the TUI | ✅ Complete | [`suryafool-cli/src/state/reducer.js`](suryafool-cli/src/state/reducer.js) (`evidence` list + `ADD_EVIDENCE`, newest 200), [`suryafool-cli/src/app.js`](suryafool-cli/src/app.js) (`EventType.EVIDENCE_CREATED` → `ADD_EVIDENCE` + one-line console notice; no raw metadata dump), [`suryafool-cli/src/components/evidenceFormat.js`](suryafool-cli/src/components/evidenceFormat.js) (NEW pure `formatEvidenceLine` — compact kind/target/source/summary fields + wifi/ble/other domain, defensive fallbacks), [`suryafool-cli/src/components/EvidenceFeed.js`](suryafool-cli/src/components/EvidenceFeed.js) (NEW live feed panel, cyberpunk visual language; wifi→primary / ble→accent), [`suryafool-cli/src/components/TabPanel.js`](suryafool-cli/src/components/TabPanel.js) (Evidence tab). Reuses the existing OutputParser/event architecture — no new event model; `--json` semantics and Python evidence pipeline untouched. esbuild bundle clean. 50 Node tests (11 new across parser/reducer/evidenceFormat) + 2 Node smokes + all 9 Python suites green |
| Phase 2.7.9 Deterministic assessment integration + contract freeze | ✅ Complete (FINAL Phase 2.7) | [`tests/test_phase279_integration.py`](tests/test_phase279_integration.py) — 26 golden-path integration tests proving the complete stack end-to-end (registry→risk→scope→prereq→sim→state→observation→evidence→persistence→JSONL→HTML; TUI feed covered by the Node suite): WiFi golden path (discover→inspect→handshake→pmkid→inspect→2 evidence), BLE golden path (discover→inspect→connect→pair→gatt.write→inspect→2 evidence), combined 4-kind run, authorization boundary consistency (PASSIVE rejects active before provider; SAFE_ACTIVE blocks sensitive; zero `evidence.created` on reject), per-target prereqs, negative-path state/evidence consistency, determinism, and a CONTRACT AUDIT of every Phase 2.7 interface (catalogue 14, 4 evidence producers, `KNOWN_EVIDENCE_KINDS`, `EvidenceRecord` fields, evidence defaults + round-trips, Python↔Node event sync, frozen plan shapes, performed-capability mapping). Freeze only — no architecture/domain/kinds/policy changes. 10 Python suites (314 tests) + 50 JS tests + 2 Node smokes all green. **Phase 2.7 is COMPLETE; Phase 2.8 not begun.** |
| Phase 2.8.0 Multi-Domain Deterministic Expansion Foundation | ✅ Complete (FIRST Phase 2.8) | [`capabilities/base.py`](capabilities/base.py) (catalogue 14 → 21: `infrared.{capture,analyze,transmit}` flat namespace, `ethernet.discovery.{discover,inspect}`, `usb.discovery.{enumerate,inspect}`; the 14 Phase 2.7 entries byte-identical), [`simulator/entities.py`](simulator/entities.py) (`IrSignal`/`EthernetHost`/`UsbDevice`), [`simulator/environment.py`](simulator/environment.py) (empty `ir`/`ethernet`/`usb` + `snapshot()`), [`cli/phase2.py`](cli/phase2.py) (`capabilities` surfaces `supported` + `[UNSUPPORTED]`), [`tests/test_phase280_multidomain.py`](tests/test_phase280_multidomain.py) (29 tests — registration, metadata validity, risks, registered-but-unsupported resolution + policy REJECT before provider, prereq chain `infrared.transmit`→`infrared.capture`, Phase 2.7 freeze regression). No evidence kinds/policy/plans/LLM/hardware. 11 Python suites (343 tests) + 50 JS + esbuild + 2 Node smokes green. **Phase 2.8.0 COMPLETE; roadmap 2.8.1–2.8.8 pending.** |
| Phase 2.8.1 Sub-GHz/RF Capture Slice | ✅ Complete | [`capabilities/base.py`](capabilities/base.py) (catalogue 21 → 22: append `subghz.capture.signal` SAFE_ACTIVE `produces_evidence=True`; existing `subghz.discovery.analyze` `produces_evidence` False→True), [`simulator/entities.py`](simulator/entities.py) (`SubGhzSignal` += `captured`/`sample_count`/`capture_quality`/`decoded_protocol_hint`), [`core/evidence.py`](core/evidence.py) (`KNOWN_EVIDENCE_KINDS` 4 → 6: +`subghz_capture`, `subghz_analysis`; Phase 2.7 four preserved as subset), [`simulator/simulator.py`](simulator/simulator.py) (`_subghz_protocol_hint` heuristic map, `_subghz_capture_quality` rssi→{clean,partial,noisy}, `action_subghz_capture_signal` handler w/ EvidenceRecord, upgraded `action_subghz_analyze` w/ per-target `s.captured` prereq gate + `decoded_protocol_hint` + `subghz_analysis` EvidenceRecord), [`engine/runner.py`](engine/runner.py) (`subghz_capture_plan()` 5 actions → 4 evidence), [`cli/phase2.py`](cli/phase2.py) (`--plan subghz_capture`), [`tests/test_phase281_subghz_capture.py`](tests/test_phase281_subghz_capture.py) (34 tests — spectrum/capture/analyze success + target validation + per-target prereq + malformed args + no false-positive evidence + kind/provenance + determinism + JSONL `evidence.created` + HTML EVIDENCE section + TUI domain mapping + Phase 2.7/2.8.0 regression); count guards bumped 21→22 across 11 prior suites; [`suryafool-cli/src/components/EvidenceFeed.test.js`](suryafool-cli/src/components/EvidenceFeed.test.js) (+3 subghz-format assertions, forward-linked from Python). No LLM/hardware/RF replay/attack/policy/evidence-system changes. 12 Python suites (377 tests) + 53 JS tests + esbuild + 2 Node smokes all green. **Phase 2.8.1 COMPLETE; roadmap 2.8.2–2.8.8 pending.** |
| Phase 2.8.2 NFC/RFID Read Slice | ✅ Complete | [`capabilities/base.py`](capabilities/base.py) (catalogue 22 → 23: append `nfc.discovery.select` PASSIVE `mutates_state=True`; existing `nfc.discovery.read` upgraded `produces_evidence=True`), [`simulator/entities.py`](simulator/entities.py) (`NfcTag` += `selected`/`read`/`read_at`/`ndef_supported`), [`core/evidence.py`](core/evidence.py) (`KNOWN_EVIDENCE_KINDS` 6 → 7: +`nfc_read`), [`simulator/simulator.py`](simulator/simulator.py) (`action_nfc_select` handler + `action_nfc_read` handler with per-target `selected=True` prereq gate + `nfc_read` EvidenceRecord), [`engine/runner.py`](engine/runner.py) (`nfc_workflow_plan()` 5 actions → 2 evidence), [`cli/phase2.py`](cli/phase2.py) (`--plan nfc_workflow`), [`tests/test_phase282_nfc_read.py`](tests/test_phase282_nfc_read.py) (53 tests); count guards bumped 22→23 + evidence-kinds updated across 6 prior suites; [`suryafool-cli/src/components/EvidenceFeed.test.js`](suryafool-cli/src/components/EvidenceFeed.test.js) (+2 NFC-format assertions, forward-linked from Python). No LLM/hardware/NFC write/replay. 13 Python suites (431 tests) + 55 JS tests + esbuild + 2 Node smokes all green. **Phase 2.8.2 COMPLETE; roadmap 2.8.3–2.8.8 pending.** |
| Phase 2.8.3 Infrared (IR) Slice | ✅ Complete | [`simulator/entities.py`](simulator/entities.py) (`IrSignal` += `layout`/`frequency_khz`/`carrier_duty_cycle`/`protocol_hint`/`transmitted`), [`simulator/simulator.py`](simulator/simulator.py) (`action_ir_capture` observational handler, `action_ir_analyze` w/ per-target capture_id prereq + `ir_analysis` EvidenceRecord + `_ir_protocol_hint`/`_ir_classification` heuristics, `action_ir_transmit` w/ same-capture_id analyzed=True prereq + `ir_transmit` EvidenceRecord; HANDLERS + note-prefix mapping make the three `infrared.*` Phase 2.8.0 entries supported), [`capabilities/base.py`](capabilities/base.py) (`infrared.analyze` + `infrared.transmit` `produces_evidence` False→True), [`core/evidence.py`](core/evidence.py) (`KNOWN_EVIDENCE_KINDS` 7 → 9: +`ir_analysis`, `ir_transmit`), [`engine/runner.py`](engine/runner.py) (`ir_workflow_plan()` 4 actions → 3 evidence), [`cli/phase2.py`](cli/phase2.py) (`--plan ir_workflow`), [`tests/test_phase283_ir.py`](tests/test_phase283_ir.py) (40 tests — capture/analyze/transmit success + per-target prereq + malformed/unknown capture_id + no-false-positive + provenance + determinism + JSONL `evidence.created` (3; 0 under PASSIVE) + HTML evidence section + TUI forward-guard + Phase 2.7/2.8.0/2.8.1/2.8.2 regression); count guards bumped to 9 kinds/producers across 6 prior suites; [`suryafool-cli/src/components/EvidenceFeed.test.js`](suryafool-cli/src/components/EvidenceFeed.test.js) (+3 IR-format assertions, forward-linked from Python). No LLM/hardware/IR transmission-replay/policy/evidence-system changes. 14 Python suites (472 tests) + 58 JS tests + esbuild + 2 Node smokes all green. **Phase 2.8.3 COMPLETE; roadmap 2.8.4–2.8.8 pending.** |
| Capability Registry | 🔲 TODO | `capability_registry/` |
| Hardware Abstraction Layer | 🔲 TODO | `hal/` |
| Mission data model | 🔲 TODO | `core/mission.py` |
| Scope Guardian | 🔲 TODO | `scope_guardian/` |
| Mission Orchestrator | 🔲 TODO | `agents/orchestrator/` |
| Discovery Agent | 🔲 TODO | `agents/discovery/` |
| Signal Intelligence Agent | 🔲 TODO | `agents/signal_intel/` |
| Device Intelligence Agent | 🔲 TODO | `agents/device_intel/` |
| Correlation Agent | 🔲 TODO | `agents/correlation/` |
| Experiment Agent | 🔲 TODO | `agents/experiment/` |
| Security Research Agent | 🔲 TODO | `agents/security_research/` |
| Attack Planning Agent | 🔲 TODO | `agents/attack_planning/` |
| Verification Agent | 🔲 TODO | `agents/verification/` |
| Skeptic Agent | 🔲 TODO | `agents/skeptic/` |
| Memory Agent | 🔲 TODO | `agents/memory/` |
| Wireless Environment Graph | 🔲 TODO | `graph/` |
| Lab Mode | 🔲 TODO | `lab/` |

---

## Planned Directory Layout (Full)

```
suryafool/
├── AGENTS.md                    # AI assistant guide + agent roster
├── CONTEXT.md                   # this file
│
├── docs/                        # design docs
│   ├── CONTEXT.md
│   ├── PRD.md
│   └── ARCHITECTURE.md
│
├── bootstrap/                   # environment setup agent (runs first, standalone)
│   ├── CONTEXT.md
│   ├── manifest.yaml
│   ├── platform.py
│   ├── checks.py
│   ├── remediate.py
│   ├── provisioning_guardian.py
│   └── agent.py
│
├── core/                        # shared utilities for all agents
│   ├── CONTEXT.md
│   ├── llm.py                   # LLM factory + rate limiter (32 req/min)
│   ├── mission.py               # Mission dataclass
│   ├── observation.py           # Observation, Signal, Device types
│   └── confidence.py            # CONFIRMED/LIKELY/POSSIBLE/UNKNOWN enum
│
├── suryafool-cli/               # ✅ Ink/React terminal front-end (v0.1.0)
│   ├── bin/suryafool.js         # CLI entry (yargs) → forks bin/run.mjs
│   ├── bin/run.mjs              # Ink render entry (reads SURYAFOOL_ARGS)
│   ├── src/app.js               # Main App component (single command + REPL)
│   ├── src/components/          # Logo, ScanPanel, AgentStatus, REPL, ...
│   ├── src/animations/          # matrix rain, glitch, typewriter, scanner
│   ├── src/backend/             # BinaryManager, OutputParser
│   └── src/styles/theme.js      # cyberpunk + clean themes
│
├── capability_registry/         # hardware → capability mapping
│   ├── CONTEXT.md
│   └── registry.py
│
├── hal/                         # hardware abstraction layer
│   ├── CONTEXT.md
│   ├── base.py                  # discover/observe/capture/interact interfaces
│   ├── esp32/
│   └── cc1101/
│
├── scope_guardian/              # deterministic wireless action policy gate
│   ├── CONTEXT.md
│   └── guardian.py
│
├── agents/                      # all mission agents
│   ├── CONTEXT.md
│   ├── orchestrator/
│   ├── discovery/
│   ├── signal_intel/
│   ├── device_intel/
│   ├── correlation/
│   ├── experiment/
│   ├── security_research/
│   ├── attack_planning/
│   ├── verification/
│   ├── skeptic/
│   └── memory/
│
├── graph/                       # wireless environment graph
│   ├── CONTEXT.md
│   └── environment_graph.py
│
└── lab/                         # lab mode: authorized target management
    ├── CONTEXT.md
    └── lab_mode.py
```

---

## Build Order

Work in this sequence to respect dependency layers:

```
1. bootstrap/     — environment setup, no mission agents involved
2. core/          — shared types all agents depend on
3. capability_registry/ + hal/  — hardware abstraction
4. scope_guardian/  — must exist before any active wireless tool
5. agents/        — mission agents, bottom-up (memory → discovery → orchestrator)
6. graph/         — environment model, populated by agents
7. lab/           — lab mode, wraps scope_guardian for security missions
```

---

## Key Invariants

- The LLM never generates shell commands — only selects from manifest entries.
- Scope Guardian is a deterministic code gate, not a prompt.
- Passive observation is the default mode for all wireless operations.
- All agent actions are logged with provenance.
- Confidence levels (`CONFIRMED / LIKELY / POSSIBLE / UNKNOWN`) are never collapsed to bool.

## LLM Provider Stack

| Provider | Package | Env var | Priority |
|---|---|---|---|
| OpenRouter | `langchain-openai` | `OPENROUTER_API_KEY` | Primary |
| OpenCode Zen | `langchain-openai` | `OPENCODE_API_KEY` | Fallback |

Provider selection is automatic with fallback: OpenRouter (10s timeout) → OpenCode Zen (10s timeout) → graceful "LLM unavailable".

Model: NVIDIA Nemotron 3 Ultra (free tier) on both endpoints.