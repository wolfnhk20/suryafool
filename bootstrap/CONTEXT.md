# CONTEXT.md — bootstrap/

> **For AI coding assistants:** This directory contains the Bootstrap / Environment Agent.
> Read [`AGENTS.md`](../AGENTS.md) and [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) before editing.

---

## Purpose

The Bootstrap Agent (`suryafool doctor`) runs **before any wireless mission**.  
Its job: verify the host machine has everything Suryafool needs, and fix it if not.

This is a **Diagnose mission** (PRD §8.5) pointed at the dev environment:

```
DISCOVER → OBSERVE → COMPARE → HYPOTHESIZE → REMEDIATE → VERIFY
```

It is **not** a Suryafool mission agent. It has no access to wireless hardware or mission state.  
It runs with OS-level access (installing packages, enabling WSL) — a different risk category.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `manifest.yaml` | ✅ Done | Human-authored dependency list — the ground truth for "ready" |
| `platform.py` | ✅ Done | OS detection — `current_os()` → `windows / linux / macos` |
| `checks.py` | ✅ Done | Read-only `check()` per dependency, platform-aware |
| `remediate.py` | 🔲 TODO | `remediate()` — executes manifest `install_cmd` entries only |
| `provisioning_guardian.py` | 🔲 TODO | Elevation gate — always pauses for human OK on privileged commands |
| `agent.py` | 🔲 TODO | LangGraph agent loop wiring all tools together |

---

## Manifest Schema

`manifest.yaml` is **never modified at runtime**. The LLM reads it — never writes it.

Fields per entry:

```yaml
- name: <str>                   # unique dependency identifier
  platforms: [windows|linux|macos]  # omit = all platforms
  check_cmd: <str|{os: str}>    # read-only, always safe to run
  expect_contains: <str>        # OR
  expect_exit_code: <int>       # success criteria
  install_cmd: <str|{os: str}>  # ONLY remediation allowed for this dep
  requires_elevation: <bool>    # if true → always show command + wait for human
  depends_on: <list|{os: list}> # ordering constraint
```

`check_cmd`, `install_cmd`, and `depends_on` can be plain strings/lists (all platforms)
or dicts keyed by OS name for platform-specific variants.

---

## Platform Support

OS detection is centralized in `platform.py`. Never use `sys.platform` directly.

| Platform | What changes |
|---|---|
| `windows` | WSL2 + usbipd + USB passthrough added; tools run via `wsl -d Ubuntu --` |
| `linux` | No WSL; tools run natively; apt for packages |
| `macos` | Homebrew prerequisite; tools via brew + pip3 |

`checks.py` exposes:
- `filter_manifest(manifest, os)` — drops entries not applicable to this OS
- `resolve_entry(entry, os)` — flattens dict-form fields into plain strings
- `check_all(manifest)` — detects OS, filters, and runs all applicable checks

---

## Provisioning Guardian Rules

Mirrors the Scope Guardian pattern but for system provisioning:

- `requires_elevation: true` → **always** show the exact command to the human and wait for explicit approval before running — every single time, not just the first.
- `requires_elevation: false` → may run automatically (read-only or non-privileged).
- The gate keys off the **manifest entry**, not the LLM's stated justification. The model cannot bypass this by rephrasing.

---

## Agent Loop (to implement in `agent.py`)

```
1. Detect OS via platform.py
2. Load manifest.yaml
3. filter_manifest() for current OS
4. For each dependency in dependency order:
   a. check()
   b. If failed → propose_remediation()
   c. If requires_elevation → request_elevation() — stop if denied
   d. remediate()
   e. verify() — if still failing, surface raw output to user, do not silently retry
5. When all pass → report "environment ready" → hand off to Mission Orchestrator
```

---

## LLM Responsibilities in This Module

**The model does:**
- Parse noisy check command output (e.g. distinguish `docker-desktop` from `Ubuntu` in `wsl -l -v`)
- Decide dependency order when a check fails unexpectedly
- Explain to the user in plain language what is missing and why
- Select which manifest entry's `install_cmd` to propose next
- Confirm success after `verify()`
- Produce a final "environment ready" / "environment blocked, here's why" report

**The model does NOT:**
- Invent or edit shell commands
- Run `requires_elevation: true` entries without explicit human confirmation
- Modify `manifest.yaml`

---

## Dependencies (Python packages)

```
pyyaml                          # parse manifest.yaml
rich                            # terminal UI (tables, spinners, prompts)
langchain                       # LLM tool-calling backbone
langgraph                       # agent state machine / loop
langchain-nvidia-ai-endpoints   # NVIDIA NIM (primary LLM provider)
langchain-groq                  # Groq (fallback LLM provider)
```

Install: `pip install pyyaml rich langchain langgraph langchain-nvidia-ai-endpoints langchain-groq`

---

## Invocation

```bash
# Check environment status (read-only, no changes)
python -m bootstrap.agent --check-only

# Full doctor run (may prompt for elevation)
python -m bootstrap.agent
```

This module is **never invoked mid-mission** by any of the wireless agents.
