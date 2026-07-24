# CONTEXT.md — docs/

> **For AI coding assistants:** This directory contains design documentation only.
> Do not write implementation code here.

---

## Purpose

This directory holds the authoritative design documents for Suryafool.  
All architectural decisions should trace back to these files.

---

## Files

### [`PRD.md`](PRD.md)
**Product Requirements Document** — the full product vision.

Key sections to know:
| Section | Topic |
|---|---|
| §5 | Core Capability Model (`DISCOVER`, `OBSERVE`, `CAPTURE`, …) |
| §7–8 | Mission system and mission types |
| §9 | Full multi-agent architecture (all 12 agents) |
| §10 | Lab Mode / Agentic Security Laboratory |
| §12 | Wireless Environment Graph schema |
| §13–14 | Hardware architecture + Hardware Abstraction Layer |
| §16–17 | MVP definition and required features |
| §19 | Safety requirements (read before touching Scope Guardian) |

### [`ARCHITECTURE.md`](ARCHITECTURE.md)
**Bootstrap / Environment Agent design spec** — the first module to implement.

Covers:
- Why the Bootstrap Agent is architecturally separate from mission agents
- The Provisioning Guardian pattern (elevation gate)
- Dependency manifest schema
- Tool interface (`check`, `propose_remediation`, `request_elevation`, `remediate`, `verify`)
- The agent's remediation loop

---

## Rules for This Directory

- **Do not add implementation files here.** Source code lives under `bootstrap/`, `agents/`, etc.
- **Do not edit PRD.md or ARCHITECTURE.md during implementation** unless documenting a deliberate design change. Treat them as source-of-truth.
- If you discover a gap or inconsistency during implementation, add a new `*.md` note file here (e.g. `DECISIONS.md`) rather than silently changing the PRD.
