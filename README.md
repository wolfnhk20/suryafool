# Suryafool

> **A universal agentic wireless platform** — give AI agents eyes, ears and hands for the wireless world.

Suryafool sits between autonomous AI agents and heterogeneous wireless hardware (Wi-Fi, BLE, Sub-GHz, NFC, RFID, IR). You hand it a natural-language mission; it plans, executes, observes, re-plans and reports — autonomously.

```
"Explore this environment."
"What wireless devices are present?"
"Audit this device for security weaknesses."
```

> See [`docs/PRD.md`](docs/PRD.md) for the full product vision and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the bootstrap design spec.

---

## Status

| Component | Status |
|---|---|
| OS detection / manifest / checks / remediation / Provisioning Guardian / bootstrap (`bootstrap/`) | ✅ Done |
| LLM factory + rate limiter (`core/llm.py`) | ✅ Done |
| **Cyberpunk CLI** (`suryafool-cli/`) | ✅ Done (v0.1.0) |
| **Phase 2 deterministic core** (`capabilities/`, `simulator/`, `policy/`, `engine/`, `reports/`, `cli/`) | ✅ Done |
| **Phase 2.7 stateful active simulator + evidence** (Wi-Fi capture, BLE GATT, evidence pipeline, TUI feed) | ✅ Done |
| **Phase 2.8.0 multi-domain foundation** (catalogue 23: wifi, ble, subghz, nfc, infrared, ethernet, usb) | ✅ Done |
| **Phase 2.8.1 Sub-GHz/RF capture slice** | ✅ Done |
| **Phase 2.8.2 NFC/RFID read slice** | ✅ Done |
| **Phase 2.8.3 Infrared (IR) slice** | ✅ Done |
| **Phase 2.8.4 Zigbee mesh slice** (`scan`/`inspect`/`join` on `ZigbeeNetwork`/`ZigbeeNode`, catalogue 26) | ✅ Done |
| Phase 2.8.5–2.8.9 (Ethernet / USB / cross-domain workflows / evidence generalization / freeze) | 🔲 TODO |
| Phase 2.5 Marauder hardware backend | 🟡 Architectural reference only (removed in Phase 2.7.4) |
| Mission agents (12 planned) | 🔲 TODO |

---

## Phase 2 — Deterministic Core & Simulator

Run the full mission loop **without hardware or an LLM**:

```bash
# From the repo root
python -m cli.phase2 capabilities            # capability catalogue (26 entries)
python -m cli.phase2 providers                # list backends (simulator only)
python -m cli.phase2 scenarios               # simulator scenarios
python -m cli.phase2 run --scenario home     # deterministic run → logs + report
python -m cli.phase2 run --scenario lab --seed 7 --json   # JSONL event stream (TUI)
python -m cli.phase2 show <run-id>           # summarize a stored run
python -m cli.phase2 report <run-id>         # regenerate HTML report
```

Flow: `ActionRequest → CapabilityRegistry.resolve() → PolicyEngine.validate() → provider.execute() → Observation → Run record`.

Artifacts are stored under `~/.suryafool/runs/<run-id>/` (`SURYAFOOL_RUNS_DIR` overrides):

```
run.json        # full structured run record
events.jsonl    # append-only JSONL audit trail
report.html     # standalone HTML report
```

### Current capability surface (Phase 2.8)

The catalogue exposes **26 entries** across 8 domains — Wi-Fi (discovery + capture), BLE (discovery + GATT), Sub-GHz (discovery + capture), NFC/RFID (discovery), Infrared (capture/analyze/transmit), Ethernet, USB, and Zigbee (discovery: scan/inspect/join). Implemented, stateful, evidence-producing slices:

- **Wi-Fi capture**: `wifi.capture.handshake` → `wifi_eapol_handshake`, `wifi.capture.pmkid` → `wifi_pmkid`
- **BLE GATT**: `ble.gatt.pair` → `ble_pairing`, `ble.gatt.write` → `ble_secure_write`
- **Sub-GHz**: `subghz.capture.signal` → `subghz_capture`, `subghz.discovery.analyze` → `subghz_analysis`
- **NFC/RFID**: `nfc.discovery.select` + `nfc.discovery.read` → `nfc_read`
- **Zigbee mesh**: `zigbee.discovery.join` → `zigbee_join` (end-device joins a PAN; parent/short-address assignment reflected on a later `inspect`)

Deterministic plans selectable via `--plan`: `exploration` (default), `active_inspection`, `wifi_capture`, `ble_gatt_workflow`, `subghz_capture`, `nfc_workflow`, `ir_workflow`, `zigbee_workflow`.

Evidence flows end-to-end: simulation success → `EvidenceRecord` → `run.json`/`events.jsonl` (`evidence.created`) → HTML report EVIDENCE section → live TUI `Evidence` tab. All failure and policy-rejected paths produce **zero evidence** and no environment mutation.

### Tests (stdlib-only runner, no pytest needed)

```bash
python -m tests.test_phase2_core
```

All **15 Python suites (523 tests)** + **60 Node tests** + 2 Node smokes + esbuild build are green.

---

## Phase 2.5 — Marauder Hardware Spike (Architectural Reference)

> **Phase 2.7.4 removed `backends/` from the runtime.** The ESP32 Marauder
> project ([github.com/justcallmekoko/ESP32Marauder](https://github.com/justcallmekoko/ESP32Marauder))
> remains an **architectural reference** for future firmware design — it is
> NOT a runtime dependency, provider, or CLI option.
>
> The spike proved the `CapabilityProvider` ABC serves real hardware with no
> core changes. That proof informed the decision to keep the ABC generic
> (in `capabilities/base.py`) and remove the Marauder-specific plumbing
> (transport, parser, provider, CLI flags, tests). The simulator is now the
> only runtime provider.

---

## Cyberpunk CLI (`suryafool-cli/`)

An interactive Ink/React terminal front-end for the Suryafool platform.

### Features

| Feature | Status |
|---|---|
| CLI commands (`scan`, `audit`, `explore`, `agents`, `config`, `doctor`) | ✅ |
| Interactive REPL mode (`--interactive`, `-i`) | ✅ |
| Cyberpunk + clean themes (`--clean`, `--hacker-mode`) | ✅ |
| Animated boot sequence (matrix rain, glitch, typewriter) | ✅ |
| Live scan panel with progress + severity-colored findings | ✅ |
| Agent status board (11 planned agents) | ✅ |
| Binary manager (auto-download, platform detection) | ✅ |
| Output parser (JSON event stream → panels) | ✅ |
| esbuild bundling to `dist/index.mjs` | ✅ |

### Install & run

```bash
cd suryafool-cli
npm install        # runs prepare → builds dist/index.mjs
npm run build      # rebuild bundle after editing src/

# Run
node bin/suryafool.js --help
node bin/suryafool.js --clean agents
node bin/suryafool.js -i          # interactive REPL
```

> Requires Node 18+ (Node 22 tested). The CLI spawns the Python bootstrap agent (`python -m bootstrap.agent`) for `doctor` commands.

### Known limitations

- `--interactive` needs a real TTY (Ink raw mode fails in piped/non-TTY shells).
- `doctor`/`agents` commands expect the Python environment to have `rich` installed (`pip install -r requirements.txt`).
- `ink-gradient` was removed (CJS `require("ink")` is incompatible with Ink 4 + Node 22 ESM); the logo now uses plain colored text.

---

## Prerequisites

| Platform | Requirements |
|---|---|
| **Windows** | Python 3.11+, PowerShell (WSL2 + usbipd set up by the Bootstrap Agent) |
| **Linux** | Python 3.11+, pip |
| **macOS** | Python 3.11+, pip3 |

---

## Installation

### 1. Clone

```bash
git clone https://github.com/your-username/suryafool.git
cd suryafool
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Open `.env` and fill in your API keys:

```env
# ── LLM Providers (Nemotron 3 Ultra via OpenAI-compatible endpoints) ────────────
# Primary: OpenRouter
OPENROUTER_API_KEY=

# Fallback: OpenCode Zen (has had recent reliability issues)
OPENCODE_API_KEY=

# Optional: Rate limit (default 32 req/min)
SURYAFOOL_RATE_LIMIT=32
```

> **Never commit `.env`** — it is gitignored.

---

## Running the Bootstrap Agent

The Bootstrap Agent (`suryafool doctor`) checks whether your system has everything Suryafool needs and guides you through fixing what's missing.

### Check-only (no changes made)

```bash
python -m bootstrap.agent --check-only
```

This runs all read-only checks for your OS and prints a status table — nothing is installed or modified.

**Example output (Windows):**

```
SURYAFOOL — Environment Check
OS: windows

 Dependency             Status   Notes
 ──────────────────────────────────────────────
 wsl2                   [OK]     
 wsl-ubuntu             [OK]     
 wsl-ubuntu-v2          [OK]     
 usbipd                 [OK]     
 usb-passthrough        [OK]     
 aircrack-ng            [OK]     
 python3                [OK]     
 scapy                  [OK]     
 python-deps            [OK]     

[OK] Environment ready.
```

### Full doctor run (installs missing dependencies)

```bash
python -m bootstrap.agent
```

The agent will:
1. Detect your OS
2. Run all applicable checks
3. For each failure:
   - **Known dependency** (in manifest): uses manifest `install_cmd` (zero LLM calls)
   - **Unknown dependency**: calls LLM to propose a fix
4. Display the EXACT command in a panel
5. Ask for approval via Provisioning Guardian (elevation-gated)
6. Execute verbatim on approval
7. Re-verify after remediation
8. Report `environment ready` when all checks pass

> **Note:** Run from an **elevated PowerShell (Run as Administrator)** for `windows_admin` dependencies (wsl2, wsl-ubuntu, usbipd). For `wsl_sudo` dependencies (aircrack-ng, python3), the sudo prompt will appear inside WSL.

---

## Running checks directly (developer mode)

```bash
python check_env.py
```

---

## Project Structure

```
suryafool/
├── AGENTS.md                    # AI assistant guide + agent roster
├── CONTEXT.md                   # Project overview and build order
├── requirements.txt
├── .env.example                 # Copy to .env, fill in your keys
├── check_env.py                 # Standalone read-only check script
│
├── docs/
│   ├── CONTEXT.md               # docs directory context
│   ├── PRD.md                   # Full product requirements
│   └── ARCHITECTURE.md          # Bootstrap agent design spec
│
├── bootstrap/                   # Environment setup agent (runs first, standalone)
│   ├── CONTEXT.md               # bootstrap module context
│   ├── __init__.py
│   ├── manifest.yaml            # Dependency manifest (never LLM-generated)
│   ├── platform.py              # OS detection (windows / linux / macos)
│   ├── checks.py                # Read-only dependency checks
│   ├── remediate.py             # Runs manifest install_cmd only
│   ├── provisioning_guardian.py # Elevation gate (3 types)
│   └── agent.py                 # Main agent loop
│
├── core/                        # Shared utilities + platform data model
│   ├── CONTEXT.md, llm.py, confidence.py, observation.py
│   ├── mission.py, evidence.py, events.py
│
├── capabilities/                # Capability catalogue + registry (Phase 2.8: 26 entries)
│   ├── base.py                  # Capability dataclass + DEFAULT_CAPABILITIES
│   └── registry.py              # CapabilityRegistry + provider binding
│
├── simulator/                   # Deterministic wireless simulator
│   ├── entities.py              # WifiNetwork/BleDevice/NfcTag/SubGhzSignal/IrSignal/...
│   ├── environment.py, rng.py, scenarios.py
│   └── simulator.py             # Action handlers → Observations (+ evidence)
│
├── policy/                      # Deterministic Scope-Guardian policy gate
│   └── policy.py                # RiskDeclarationRule, RiskTierAuthorizedRule
│
├── engine/                      # Deterministic run engine
│   ├── runner.py                # Plans (exploration/wifi_capture/ble_gatt/subghz/nfc)
│   └── logger.py                # RunLogger (run.json + events.jsonl)
│
├── reports/                     # HTML report generation (top-level EVIDENCE section)
│
├── cli/                         # `python -m cli.phase2` command suite
│
├── tests/                       # 15 stdlib-runnable suites (523 tests)
│
├── scripts/                     # 2 Node smoke scripts (event-stream + wiring contracts)
│
└── suryafool-cli/               # Ink/React cyberpunk TUI (v0.1.0)
    ├── bin/                     # suryafool.js CLI entry
    └── src/                     # app, components, animations, backend, state, styles
```

---

## LLM Providers

| Provider | Endpoint | Model | Env var | Priority |
|---|---|---|---|---|
| OpenRouter | https://openrouter.ai/api/v1 | nvidia/nemotron-3-ultra-550b-a55b:free | `OPENROUTER_API_KEY` | Primary |
| OpenCode Zen | https://opencode.ai/zen/v1 | opencode/nemotron-3-ultra-free | `OPENCODE_API_KEY` | Fallback |

**Get keys:**
- OpenRouter: https://openrouter.ai/keys
- OpenCode Zen: https://opencode.ai/

**Fallback behavior:** OpenRouter (10s timeout) → OpenCode Zen (10s timeout) → graceful "LLM unavailable" result.

---

## Design Principles

- **LLM = diagnosis only.** The model never generates shell commands. Every command comes from `manifest.yaml` (known) or LLM proposal (unknown).
- **Approve-before-generate ordering.** Command resolved → displayed in Panel → user approval → execute verbatim.
- **Single elevation type.** `requires_elevation: none | windows_admin | wsl_sudo` (not boolean).
- **Provider tracking.** Final report shows "Resolved via manifest" vs "Resolved via LLM (openrouter/opencode_zen)".
- **Scope Guardian is deterministic.** No LLM can reason its way past the wireless action gate.
- **Passive by default.** Active wireless interactions require explicit mission scope.
- **All actions are logged.** No silent mutations.
- **Platform detection is centralized.** Always use `bootstrap/platform.py → current_os()`.

---

## Contributing

Read [`AGENTS.md`](AGENTS.md) and the relevant `CONTEXT.md` before touching any directory.