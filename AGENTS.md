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
└── core/                    ← ✅ COMPLETE (llm.py)
    ├── CONTEXT.md             ← core module context
    └── llm.py                 ← LLM factory + sliding-window rate limiter (32 req/min)
```

Each directory has a `CONTEXT.md`. **Read it before editing files in that directory.**

---

## Agent Roster

### Implemented

| Agent | Module | Status |
|---|---|---|
| **Bootstrap / Environment Agent** | `/bootstrap` | 🟢 Complete |

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