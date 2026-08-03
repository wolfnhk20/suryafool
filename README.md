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
| OS detection (`platform.py`) | ✅ Done |
| Dependency manifest (`manifest.yaml`) | ✅ Done |
| Check runner (`checks.py`) | ✅ Done |
| Remediation runner (`remediate.py`) | ✅ Done |
| Provisioning Guardian | ✅ Done |
| Bootstrap agent loop (`agent.py`) | ✅ Done |
| LLM factory + rate limiter (`core/llm.py`) | ✅ Done |
| **Cyberpunk CLI** (`suryafool-cli/`) | ✅ Done (v0.1.0) |
| Mission agents (12 planned) | 🔲 TODO |

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
└── core/                        # Shared utilities for all agents
    ├── CONTEXT.md               # core module context
    ├── llm.py                   # LLM factory + rate limiter (32 req/min)
    └── __init__.py
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