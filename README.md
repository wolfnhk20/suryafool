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
| Remediation runner (`remediate.py`) | 🔲 TODO |
| Provisioning Guardian | 🔲 TODO |
| Bootstrap agent loop | 🔲 TODO |
| Mission agents (12 planned) | 🔲 TODO |

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
# Choose your LLM provider: nim | groq
SURYAFOOL_LLM_PROVIDER=nim

# NVIDIA NIM — https://build.nvidia.com
NVIDIA_API_KEY=nvapi-...

# Groq fallback — https://console.groq.com
GROQ_API_KEY=gsk_...
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

 Dependency        Status   Notes
 ─────────────────────────────────────────────
 wsl2              ✓ PASS
 wsl-ubuntu        ✓ PASS
 usbipd            ✓ PASS
 usb-passthrough   ✗ FAIL   No adapter attached
 aircrack-ng       ✓ PASS
 python3           ✓ PASS
 scapy             ✓ PASS
 python-deps       ✗ FAIL   langchain_nvidia_ai_endpoints missing
```

### Full doctor run (installs missing dependencies)

```bash
python -m bootstrap.agent
```

The agent will:
1. Detect your OS
2. Run all applicable checks
3. For each failure, propose the fix from the manifest
4. For privileged commands (`requires_elevation: true`), **pause and show you the exact command** before running it — you must approve explicitly
5. Verify each fix after applying it
6. Report `environment ready` when all checks pass

> **Note:** `bootstrap/agent.py` is not yet implemented. The check runner (`checks.py`) is complete and can be exercised directly — see below.

---

## Running checks directly (developer mode)

While `agent.py` is being built, you can run the check layer standalone:

```python
import yaml
from bootstrap.checks import check_all
from bootstrap.platform import current_os

with open("bootstrap/manifest.yaml") as f:
    manifest = yaml.safe_load(f)["dependencies"]

results = check_all(manifest)

for name, result in results.items():
    status = "✓ PASS" if result.passed else "✗ FAIL"
    print(f"{name:25} {status}")
    if not result.passed:
        print(f"  → {result.reason}")
```

Run it from the project root:

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
│
├── docs/
│   ├── PRD.md                   # Full product requirements
│   └── ARCHITECTURE.md          # Bootstrap agent design spec
│
└── bootstrap/                   # Environment setup agent (runs first)
    ├── manifest.yaml            # Dependency manifest (never LLM-generated)
    ├── platform.py              # OS detection
    ├── checks.py                # Read-only dependency checks
    ├── remediate.py             # [TODO] Install manifest entries
    ├── provisioning_guardian.py # [TODO] Elevation gate
    └── agent.py                 # [TODO] LangGraph agent loop
```

---

## LLM Providers

| Provider | Env var | Priority | Where to get a key |
|---|---|---|---|
| NVIDIA NIM | `NVIDIA_API_KEY` | Primary | [build.nvidia.com](https://build.nvidia.com) |
| Groq | `GROQ_API_KEY` | Fallback | [console.groq.com](https://console.groq.com) |

Switch providers at any time:

```env
SURYAFOOL_LLM_PROVIDER=groq
```

---

## Design Principles

- **LLM = diagnosis only.** The model never generates shell commands. Every command comes from `manifest.yaml`.
- **Scope Guardian is deterministic.** No LLM can reason its way past the wireless action gate.
- **Passive by default.** Active wireless interactions require explicit mission scope.
- **All actions are logged.** No silent mutations.
- **Platform detection is centralized.** Always use `bootstrap/platform.py → current_os()`.

---

## Contributing

Read [`AGENTS.md`](AGENTS.md) and the relevant `CONTEXT.md` before touching any directory.
