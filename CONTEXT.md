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
| Cyberpunk CLI (Ink/React TUI) | ✅ Done (v0.1.0) | [`suryafool-cli/`](suryafool-cli/) |
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