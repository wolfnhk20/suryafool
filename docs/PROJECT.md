# PROJECT.md — Suryafool Complete Project Reference

> **Everything you need to know about Suryafool in one document.**  
> For AI assistants, new contributors, and stakeholders.

---

## 1. PROJECT IDENTITY

**Suryafool** = "Universal Agentic Wireless Platform"

An operating layer between **autonomous AI agents** and **heterogeneous wireless hardware** (Wi-Fi, BLE, Sub-GHz, NFC, RFID, IR, SDR).

**Mission Model:** Users give a natural-language objective (e.g., "Explore this environment", "Audit this device"). The platform autonomously **plans → executes → observes → re-plans → reports**.

**Core Philosophy:**  
- Passive observation by default  
- Active interaction only with explicit authorization  
- All actions logged with provenance  
- Confidence levels preserved (never collapsed to boolean)  
- Deterministic safety gates (Scope Guardian, Provisioning Guardian)

---

## 2. REPOSITORY STRUCTURE

```
suryafool/
├── AGENTS.md                 # AI assistant guide + agent roster
├── CONTEXT.md                # Root project context (this file's summary)
├── README.md                 # Setup + usage guide
├── requirements.txt          # Python deps
├── .env.example              # Env var template
├── check_env.py              # Read-only env check script
│
├── docs/
│   ├── CONTEXT.md            # Docs directory context
│   ├── PRD.md                # Full product requirements
│   ├── ARCHITECTURE.md       # Bootstrap agent design spec
│   └── PROJECT.md            # This file
│
├── bootstrap/                # ✅ COMPLETE - Environment Setup Agent
│   ├── CONTEXT.md
│   ├── __init__.py
│   ├── manifest.yaml         # Dependency manifest (human-authored)
│   ├── platform.py           # OS detection (windows/linux/macos)
│   ├── checks.py             # Read-only check() per dependency
│   ├── remediate.py          # Runs manifest install_cmd only
│   ├── provisioning_guardian.py  # Elevation gate (shows cmd + waits)
│   └── agent.py              # Full remediation loop with Rich UI
│
├── core/                     # ✅ COMPLETE (llm.py only so far)
│   ├── CONTEXT.md
│   └── llm.py                # LLM factory + sliding-window rate limiter (32 req/min)
│
└── suryafool-cli/            # ✅ COMPLETE (v0.1.0, Level 1000) - Ink/React Cyberpunk TUI
    ├── bin/suryafool.js      # CLI entry (yargs) → forks bin/run.mjs
    ├── bin/run.mjs           # Ink render entry (reads SURYAFOOL_ARGS env)
    ├── src/app.js            # Main App component (full-screen layout)
    ├── src/state/            # State management (useReducer + useContext)
    │   ├── context.js        # StateContext, DispatchContext, StateProvider
    │   ├── reducer.js        # Reducer with object-map handlers
    │   └── reducer.test.js   # 14 passing tests
    ├── src/utils/            # Shared utilities
    │   ├── platform.js       # OS detection
    │   ├── config.js         # ~/.suryafool/config.json
    │   └── repo-root.js      # Walks up to find bootstrap/manifest.yaml
    ├── src/components/       # 15 UI components (see roster below)
    │   ├── Header.js         # Cyberpunk/clean branding
    │   ├── Footer.js         # Hotkeys: [Tab] Switch | [Ctrl+C] Quit | [?] Help
    │   ├── TabPanel.js       # Clickable tabs (Dashboard/Agents/Findings)
    │   ├── CommandBar.js     # Input prompt with command submission
    │   ├── HelpOverlay.js    # Help documentation modal (? key)
    │   ├── ModalLayer.js     # Error/confirmation modals
    │   ├── Console.js        # Real-time output display
    │   ├── ScanDashboard.js  # Findings + progress bar
    │   ├── AgentsBoard.js    # Active agents list
    │   ├── ConfigView.js     # Theme switching
    │   └── index.js          # Barrel exports
    ├── src/backend/          # Persistent Python process wrapper
    │   ├── binary.js         # Platform detection, binary fetch/exec
    │   └── backend.js        # BackendManager with run()/checkHealth()
    ├── src/styles/theme.js   # Cyberpunk + clean themes
    ├── src/app.test.jsx      # Smoke test
    ├── vitest.config.js      # Vitest config
    ├── package.json
    ├── bugs/                 # Known environmental issues
    │   └── bootstrap-agent-not-installed.md
    └── dist/index.mjs        # Built output (esbuild)
```

---

## 3. IMPLEMENTED COMPONENTS

### 3.1 Bootstrap Agent (`bootstrap/`) — **COMPLETE**
- **Purpose:** Environment setup, dependency installation, OS configuration
- **Key Files:**
  - `platform.py` → `current_os()` returns `'windows'|'linux'|'macos'`
  - `manifest.yaml` — 17 deps: python, node, esbuild, winget/apt/brew packages, pip packages, WSL+usbipd on Windows
  - `checks.py` — `check(dep)` returns `{status: 'ok'|'missing'|'version_mismatch', ...}`
  - `remediate.py` — Runs `install_cmd` from manifest only
  - `provisioning_guardian.py` — Gates elevation (`windows_admin`, `wsl_sudo`); shows exact command, waits for human
  - `agent.py` — Full loop: check → propose → request elevation → remediate → verify; Rich TUI

### 3.2 Core LLM Factory (`core/llm.py`) — **COMPLETE**
- **Purpose:** Unified LLM interface with provider fallback + rate limiting
- **Providers:**
  1. OpenRouter (`OPENROUTER_API_KEY`) — primary, 10s timeout
  2. OpenCode Zen (`OPENCODE_API_KEY`) — fallback, 10s timeout
- **Model:** NVIDIA Nemotron 3 Ultra (free tier)
- **Rate Limiter:** Sliding window, 32 requests/minute
- **API:** `get_llm()` → returns LangChain `ChatOpenAI` instance

### 3.3 Suryafool CLI (`suryafool-cli/`) — **COMPLETE (Level 1000)**

#### Architecture
- **ESM build** via esbuild: `src/app.js` → `dist/index.mjs`
- **Externals:** react, ink, ink-text-input, chalk, gradient-string, yargs, adm-zip
- **Entry:** `bin/suryafool.js` (yargs) → forks `bin/run.mjs` with `SURYAFOOL_ARGS`
- **Renderer:** `bin/run.mjs` — Ink render with **fake TTY stdin** workaround for non-TTY environments

#### State Management (`src/state/`)
- **Pattern:** `useReducer` + `useContext` (two contexts: `StateContext`, `DispatchContext`)
- **State Shape:**
  ```js
  {
    theme: 'cyberpunk'|'clean',
    activeTab: 'dashboard'|'agents'|'findings'|'config',
    dashboard: { findings: [], progress: 0 },
    agents: [],
    logs: [],                    // {message, level, timestamp}
    modal: null,                 // {type, title, message, ...}
    commandHistory: [],
    currentCommand: null,
    commandStatus: 'idle'|'running'|'success'|'error',
  }
  ```
- **Actions:** `SET_THEME`, `SET_TAB`, `ADD_FINDING`, `SET_PROGRESS`, `AGENT_STATUS`, `ADD_LOG`, `SET_MODAL`, `CLEAR_MODAL`, `PUSH_HISTORY`, `SET_CURRENT_COMMAND`, `SET_COMMAND_STATUS`, `CLEAR_LOGS`
- **Tests:** 14/14 passing (`reducer.test.js`)

#### UI Components (`src/components/`)
| Component | Wired in `app.js`? | Purpose |
|---|---|---|
| `Header` | yes | Branding, theme indicator |
| `Footer` | yes | Hotkey hints |
| `TabPanel` | yes | 4 tabs: Dashboard / Agents / Findings / Config (click + keyboard) |
| `CommandBar` | yes | Text input, Enter=submit, Up/Down=history |
| `HelpOverlay` | yes | Full-screen help modal (? key) |
| `ModalLayer` | yes | Renders modal stack (error/confirm/prompt) |
| `Console` | yes | Real-time log streaming (auto-scroll, level colors) |
| `ScanDashboard` | yes (via TabPanel) | Findings + hand-rolled progress bar |
| `AgentsBoard` | yes (via TabPanel) | Agent cards with status |
| `ConfigView` | yes (via TabPanel) | Theme toggle |
| `BootSequence`, `ProgressWidget`, `ScanPanel`, `AgentStatus`, `REPL`, `Logo`, `InputPrompt`, `Glyph` | no | On disk, kept for future use |
| `index.js` | n/a | Barrel exports |

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Header (1 line)                                             │
├─────────────────────────────┬───────────────────────────────┤
│ TabPanel (2/3 width)        │ Console (1/3 width)           │
│  - Dashboard: findings,     │  - Real-time backend output   │
│    progress                 │  - Auto-scroll, level colors  │
│  - Agents: agent cards      │                               │
│  - Findings: detailed list  │                               │
├─────────────────────────────┴───────────────────────────────┤
│ Footer (hotkeys)                                           │
├─────────────────────────────────────────────────────────────┤
│ CommandBar (input)                                         │
└─────────────────────────────────────────────────────────────┘
Modals overlay: HelpOverlay, ModalLayer
```

#### Backend Integration (`src/backend/`)
- **`binary.js`** — Platform detection, downloads/runs Python bootstrap agent
  - Falls back to `python -m bootstrap.agent` if binary missing
- **`backend.js`** — `BackendManager` class
  - `run(command, args)` → spawns persistent process, streams stdout
  - Parses JSON lines: `{type: 'log'|'finding'|'progress'|'agent', payload}`
  - Updates state via dispatched actions
  - `checkHealth()` — verifies bootstrap agent importable
- **Integration:** `app.js` initializes `BackendManager`, runs `doctor` on mount, handles command execution

#### CLI Commands (via yargs)
| Command | Description |
|---|---|
| `scan <target>` | Scan wireless environment |
| `audit <target>` | Security audit a device |
| `explore` | Discover all wireless devices |
| `agents` | List all mission agents |
| `config [get|set] [key] [value]` | View/set configuration |
| `doctor` | Check environment setup |

#### Themes
- **Cyberpunk (default):** Sunflower-gold/amber palette, restrained accents. `src/styles/theme.js`
- **Clean:** Minimal, professional

#### Repo-root resolution
- `src/utils/repo-root.js` walks up from the CLI package dir to find `bootstrap/manifest.yaml`.
- `bin/suryafool.js` forwards the resolved root via `SURYAFOOL_REPO_ROOT` env to `bin/run.mjs`, which `process.chdir()`s before importing the dist bundle.
- `BinaryManager.run()` passes `cwd: getRepoRoot()` to `spawn()` so Python's `-m bootstrap.agent` resolves its manifest regardless of the user's cwd.
- Tests: `src/utils/repo-root.test.js` (5/5 passing).

#### Known Issue
- **Bootstrap agent not installed** in development environment → commands fail with `ModuleNotFoundError: No module named 'rich'`
- Handled gracefully: errors appear in Console panel, UI remains responsive
- Fix: `pip install -r requirements.txt` from repo root (or use `python -m bootstrap.agent` which auto-installs)
- Documented in `suryafool-cli/bugs/bootstrap-agent-not-installed.md`

---

## 4. PLANNED COMPONENTS (From PRD §9)

| Agent | Role | Module |
|---|---|---|
| **Mission Orchestrator** | Central coordinator — interprets objectives, delegates, replans | `/agents/orchestrator` |
| **Discovery Agent** | Broad passive reconnaissance across all wireless protocols | `/agents/discovery` |
| **Signal Intelligence Agent** | Characterizes signals, detects patterns, classifies signal families | `/agents/signal_intel` |
| **Device Intelligence Agent** | Builds logical device hypotheses from multi-protocol observations | `/agents/device_intel` |
| **Correlation Agent** | Links observations across protocols into unified environment model | `/agents/correlation` |
| **Experiment Agent** | Designs controlled investigations to resolve hypotheses | `/agents/experiment` |
| **Security Research Agent** | Maps attack surfaces, matches weakness classes, selects permitted tests | `/agents/security_research` |
| **Attack Planning Agent** | Active only during authorized security missions — reasons about test paths | `/agents/attack_planning` |
| **Verification Agent** | Independently verifies security findings, checks reproducibility | `/agents/verification` |
| **Skeptic Agent** | Challenges conclusions from other agents, reduces overconfidence | `/agents/skeptic` |
| **Memory Agent** | Persistent environmental and mission knowledge store | `/agents/memory` |
| **Scope Guardian** | **Deterministic** policy enforcement — not an LLM advisory agent | `/scope_guardian` |

> **Scope Guardian is mandatory.** No active wireless action bypasses it.

---

## 5. HARDWARE TARGETS (MVP)

| Hardware | Protocols | Role | Budget |
|---|---|---|---|
| ESP32 | Wi-Fi, BLE | Discovery + passive observation | ~₹500 |
| CC1101 | Sub-GHz (300-928 MHz) | Signal capture + transmission | ~₹1,200 |
| NFC/RFID module (PN532/RFID-RC522) | NFC, RFID | Detection + inspection | ~₹300 |
| IR Tx/Rx (TSOP38238 + IR LED) | Infrared | Capture + replay | ~₹200 |
| **Total** | | | **~₹2,200 / ₹3,000 max** |

---

## 6. OS SUPPORT MATRIX

| Platform | WSL Needed | USB Access | Package Manager |
|---|---|---|---|
| Windows | Yes (WSL2 + usbipd) | Via usbipd passthrough | winget / apt (inside WSL) |
| Linux | No | Native | apt / pip |
| macOS | No | Native | Homebrew / pip3 |

**Centralized detection:** `bootstrap/platform.py → current_os()` — never use `sys.platform` directly.

---

## 7. LLM PROVIDER STACK

| Provider | Package | Env Var | Priority |
|---|---|---|---|
| OpenRouter | `langchain-openai` | `OPENROUTER_API_KEY` | Primary |
| OpenCode Zen | `langchain-openai` | `OPENCODE_API_KEY` | Fallback |

- Auto-fallback: OpenRouter (10s) → OpenCode Zen (10s) → "LLM unavailable"
- Model: **NVIDIA Nemotron 3 Ultra** (free tier) on both
- Rate limiter: 32 req/min sliding window (`core/llm.py`)

---

## 8. CORE DESIGN RULES (Non-Negotiable)

1. **LLM = diagnosis/interpretation only** — Never generates shell commands. Selects from human-authored manifest.
2. **Scope Guardian is deterministic** — Code gate, not prompt. LLM cannot reason past it.
3. **Provisioning Guardian mirrors this** — Elevation always pauses, shows exact command, waits for human.
4. **Passive is default** — Active requires explicit mission scope. Security testing requires Lab Mode.
5. **All actions logged** — No silent mutations.
6. **Platform detection centralized** — Use `bootstrap/platform.py`.
7. **Manifest never LLM-generated** — `bootstrap/manifest.yaml` is ground truth.

---

## 9. KEY CAPABILITY ABSTRACTIONS (HAL)

Agents reason using these operations, not hardware specifics:

```
DISCOVER  OBSERVE  CAPTURE  IDENTIFY  ANALYZE
COMPARE   CORRELATE  EXPERIMENT  INTERACT  TEST  VERIFY
```

Hardware modules register supported ops in **Capability Registry** (planned: `/capability_registry`).

---

## 10. MISSION DATA MODEL (Planned)

```js
{
  objective: "natural-language goal",
  authorization_scope: { targets: [], permissions: [] },
  available_capabilities: [],  // from Capability Registry
  observations: [],            // raw wireless data
  hypotheses: [],              // {claim, confidence: CONFIRMED|LIKELY|POSSIBLE|UNKNOWN, evidence}
  planned_actions: [],
  executed_actions: [],        // full history with provenance
  evidence: [],                // findings with sources
  agent_reasoning_state: {},   // per-agent scratchpad
  results: {}                  // final report
}
```

---

## 11. CONFIDENCE LEVELS (Mandatory)

Signal Intel & Device Intel **must** tag all conclusions:

```
CONFIRMED  |  LIKELY  |  POSSIBLE  |  UNKNOWN
```

Never collapse to boolean. Preserve uncertainty.

---

## 12. BUILD & DEV COMMANDS

### Root Project
```bash
# Check environment
python check_env.py

# Install Python deps
pip install -r requirements.txt

# Run bootstrap agent
python -m bootstrap.agent
```

### Suryafool CLI
```bash
cd suryafool-cli

# Install deps
npm install

# Build (esbuild → dist/index.mjs)
npm run build

# Dev (direct node, no build)
npm run dev

# Run CLI
node bin/suryafool.js --help
node bin/suryafool.js --version
node bin/suryafool.js scan "target"
node bin/suryafool.js doctor

# Test
node --test src/**/*.test.js     # 39/39 passing (4 files: state/reducer, backend/backend, backend/parser, utils/repo-root)
# app.test.jsx is a smoke test requiring a configured vitest (see Known Issues §16)
```

---

## 13. KEY FILES QUICK REFERENCE

| File | Purpose |
|---|---|
| `AGENTS.md` | AI guide, agent roster, design rules |
| `CONTEXT.md` | Root context, implementation status |
| `docs/PRD.md` | Full product requirements |
| `docs/ARCHITECTURE.md` | Bootstrap agent spec |
| `bootstrap/manifest.yaml` | Dependency manifest (17 entries) |
| `bootstrap/platform.py` | `current_os()` — Windows/Linux/macOS |
| `bootstrap/agent.py` | Remediation loop with Rich TUI |
| `core/llm.py` | LLM factory + 32 req/min rate limiter |
| `suryafool-cli/bin/suryafool.js` | CLI entry (yargs) |
| `suryafool-cli/bin/run.mjs` | Ink renderer + fake TTY stdin |
| `suryafool-cli/src/app.js` | Full-screen App component |
| `suryafool-cli/src/utils/repo-root.js` | Walks up to find `bootstrap/manifest.yaml` |
| `suryafool-cli/src/state/context.js` | State/Dispatch contexts |
| `suryafool-cli/src/state/reducer.js` | State reducer (12 actions) |
| `suryafool-cli/src/backend/backend.js` | BackendManager (persistent process) |
| `suryafool-cli/src/backend/binary.js` | BinaryManager (spawns `python -m bootstrap.agent` with `cwd: getRepoRoot()`) |
| `suryafool-cli/src/components/*.js` | UI components (8 wired into `app.js`, 7 unused, kept on disk) |
| `suryafool-cli/package.json` | Deps, scripts, build config |

---

## 14. ENVIRONMENT VARIABLES

| Var | Purpose | Required |
|---|---|---|
| `OPENROUTER_API_KEY` | Primary LLM provider | Yes |
| `OPENCODE_API_KEY` | Fallback LLM provider | No |
| `SURYAFOOL_ARGS` | Passed from CLI to renderer | Internal |
| `SURYAFOOL_REPO_ROOT` | Absolute path to repo root (mark: `bootstrap/manifest.yaml`) | Internal (set by `bin/suryafool.js`) |
| `OPENROUTER_API_KEY` | Primary LLM provider | Yes (for LLM-backed flows) |
| `OPENCODE_API_KEY` | Fallback LLM provider | No |

Theme is selected via the `--clean` CLI flag (not env). With no flag, default is `cyberpunk`.

---

## 15. DEVELOPMENT PRINCIPLES (Ponytail)

- **YAGNI** — Does this need to exist? Skip speculative features.
- **Reuse first** — Check codebase for existing helpers/utils before writing.
- **Stdlib over deps** — Native platform features > libraries.
- **Fewest files** — Shortest working diff wins.
- **Deletion over addition** — Boring > clever.
- **One-liner when possible** — `@lru_cache` over custom cache class.
- **Mark simplifications** — `ponytail:` comment names ceiling + upgrade path.
- **Test non-trivial logic** — One runnable check per branch/loop/parser.

---

## 16. KNOWN ISSUES & WORKAROUNDS

| Issue | Location | Workaround |
|---|---|---|
| Bootstrap agent not installed in dev env | `suryafool-cli/` | Errors caught & displayed in Console; UI stays responsive. See `bugs/bootstrap-agent-not-installed.md` |
| Stdin raw mode in non-TTY | `bin/run.mjs` | Fake TTY stdin stream with `isTTY=true`, no-op `setRawMode/ref/unref` |
| `app.test.jsx` runner mismatch | `suryafool-cli/` | Vitest can't discover `node:test` syntax; Node can't load `.jsx` without transform. Use `node --test src/**/*.test.js` (excludes `.jsx`) or fix `vitest.config.js` to wire `unplugin-node-resolver`/`unplugin-vitest`. |
| Transitive vuln alerts | `npm audit` | Non-blocking; deferred |

---

## 17. NEXT MILESTONES (Priority Order)

**Recently shipped (Aug 2026):**
- TUI wiring + bootstrap path fix (`docs/superpowers/plans/2026-08-11-tui-wiring-bootstrap-path.md`)
- Repo-root utility (`suryafool-cli/src/utils/repo-root.js`)

**Next up:**
1. **Fix `app.test.jsx` runner mismatch** — `vitest.config.js` needs to discover `node:test` syntax, OR move the test to `.test.js` and inline JSX as `React.createElement`. Blocks CI.
2. **Install Python deps** — `pip install -r requirements.txt` to unblock `doctor` / `scan` / etc. flow.
3. **Resolve working tree** — 20+ files dirty; commit or stash.
4. **Capability Registry** (`capability_registry/`) — Hardware→capability mapping
5. **Scope Guardian** (`scope_guardian/`) — Deterministic policy gate (MANDATORY)
6. **Hardware Abstraction Layer** (`hal/`) — Base interfaces + ESP32/CC1101 drivers
7. **Core Mission Types** (`core/mission.py`, `core/observation.py`, `core/confidence.py`)
8. **Agents** — Bottom-up: Memory → Discovery → Orchestrator → others
9. **Wireless Environment Graph** (`graph/`) — Unified environment model
10. **Lab Mode** (`lab/`) — Authorized target management for security missions

---

## 18. QUICK START FOR NEW CONTRIBUTORS

```bash
# 1. Clone
git clone https://github.com/wolfnhk20/suryafool.git
cd suryafool

# 2. Check environment
python check_env.py

# 3. Run bootstrap agent (installs deps)
python -m bootstrap.agent

# 4. Build CLI
cd suryafool-cli
npm install
npm run build

# 5. Test CLI
node bin/suryafool.js --help
node bin/suryafool.js doctor

# 6. Run state tests
node src/state/reducer.test.js
```

---

## 19. ARCHITECTURE DIAGRAM (Text)

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER MISSION                              │
│                  (Natural Language Objective)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MISSION ORCHESTRATOR                          │
│            (Plans, delegates, replans, reports)                 │
└───────┬──────────────┬──────────────┬──────────────┬────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Discovery    │ │ Signal Intel  │ │ Device Intel  │ │ Correlation   │
│  (Passive)    │ │ (Classify)    │ │ (Hypothesize) │ │ (Unify)       │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │                 │
        └─────────────────┼─────────────────┼─────────────────┘
                          ▼
              ┌───────────────────────┐
              │  Wireless Environment  │
              │        Graph           │
              └───────────┬────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Experiment   │ │ Security Rsch │ │ Verification  │
│  (Test Hyp.)  │ │ (Attack Surf) │ │ (Reproduce)   │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
              ┌───────────────────────┐
              │    SCOPE GUARDIAN      │
              │  (Deterministic Gate)  │
              └───────────┬────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      ┌───────────────┐       ┌───────────────┐
      │  Attack Plan  │       │   Hardware    │
      │  (Authorized) │       │  Abstraction  │
      └───────────────┘       └───────────────┘
```

---

## 20. CONTACT & LINKS

- **Repository:** https://github.com/wolfnhk20/suryafool
- **PRD:** `docs/PRD.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Bootstrap Agent:** `bootstrap/agent.py`
- **CLI:** `suryafool-cli/`

---

*Last updated: 2026-08-13 after TUI wiring + bootstrap path fix plan.*