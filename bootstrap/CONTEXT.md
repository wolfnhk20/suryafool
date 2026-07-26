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
| `__init__.py` | ✅ Done | Makes `bootstrap` a Python package |
| `manifest.yaml` | ✅ Done | Human-authored dependency list — the ground truth for "ready" |
| `platform.py` | ✅ Done | OS detection — `current_os()` → `windows / linux / macos` |
| `checks.py` | ✅ Done | Read-only `check()` per dependency, platform-aware |
| `remediate.py` | ✅ Done | `remediate()` — executes manifest `install_cmd` entries, never invents commands |
| `provisioning_guardian.py` | ✅ Done | Elevation gate — always pauses for human OK on privileged commands |
| `agent.py` | ✅ Done | Full remediation loop with Rich UI and dependency-aware ordering |

---

## Manifest Schema

`manifest.yaml` is **never modified at runtime**. The LLM reads it — never writes it.

Fields per entry:

```yaml
- name: <str>                      # unique dependency identifier
  platforms: [windows|linux|macos]  # omit = all platforms
  check_cmd: <str|{os: str}>        # read-only, always safe to run
  expect_contains: <str>            # OR
  expect_exit_code: <int>           # success criteria
  install_cmd: <str|{os: str}>      # ONLY remediation allowed for this dep
  requires_elevation: none|windows_admin|wsl_sudo  # elevation type
  depends_on: <list|{os: list}>     # ordering constraint
```

`check_cmd`, `install_cmd`, and `depends_on` can be plain strings/lists (all platforms)
or dicts keyed by OS name for platform-specific variants.

---

## Elevation Types

| Type | When used | Example commands |
|---|---|---|
| `none` | No elevation needed | `pip install`, `which`, `python -c` |
| `windows_admin` | Elevated Windows shell (Run as Administrator) | `wsl --install`, `winget install`, `dism` |
| `wsl_sudo` | sudo inside WSL (interactive password prompt) | `apt install`, `sudo apt update` |

The Provisioning Guardian keys off the manifest entry — the LLM cannot bypass this.

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

## Agent Loop (implemented in `agent.py`)

```
1. Detect OS via platform.py → assert_supported()
2. Load and filter manifest.yaml for current OS
3. Run check_all() — print initial status table (Rich)
4. If all pass → report "environment ready", exit 0
5. Remediation phase (in manifest order):
   a. Skip entries whose depends_on are not yet satisfied (blocked)
   b. Resolve install command:
        - In manifest → use manifest install_cmd (known, zero LLM)
        - Not in manifest → call LLM to propose fix (unknown)
   c. Display EXACT command in Panel, route through Provisioning Guardian:
        - requires_elevation: windows_admin → Windows Admin prompt
        - requires_elevation: wsl_sudo → WSL sudo prompt
        - requires_elevation: none → soft auto-install prompt
   d. If approved → remediate() with show_output=True (live streaming)
   e. verify() — re-run check(); update live results so dependents see new state
   f. If still failing → report, continue (no silent retry)
6. Final report:
   - Resolved via manifest (count + list)
   - Resolved via LLM (count + list + provider breakdown)
   - Skipped / Failed
```

---

## LLM Responsibilities in This Module

**The model does:**
- Parse noisy check command output (e.g. distinguish `docker-desktop` from `Ubuntu` in `wsl -l -v`)
- Propose remediation commands for **unknown** dependencies (not in manifest)
- Explain to the user in plain language what is missing and why
- Confirm success after `verify()`
- Produce a final "environment ready" / "environment blocked, here's why" report

**The model does NOT:**
- Invent or edit shell commands for known dependencies
- Run elevation-gated commands without explicit human confirmation
- Modify `manifest.yaml`

---

## Dependencies (Python packages)

```
langchain-openai          # OpenAI-compatible client for OpenRouter + OpenCode Zen
python-dotenv             # loads .env at startup
pyyaml                    # parse manifest.yaml
rich                      # terminal UI (tables, spinners, prompts)
```

Install: `pip install langchain-openai python-dotenv pyyaml rich`

---

## Invocation

```bash
# Check environment status (read-only, no changes)
python -m bootstrap.agent --check-only

# Full doctor run — asks user per failure, prompts for elevation on privileged installs
python -m bootstrap.agent

# Standalone check script (no agent loop, developer shortcut)
python check_env.py
```

> Run from the project root (`suryafool/`) so the default manifest path `bootstrap/manifest.yaml` resolves correctly.

This module is **never invoked mid-mission** by any of the wireless agents.