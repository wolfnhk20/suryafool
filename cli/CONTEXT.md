# CONTEXT.md — cli/

> **For AI coding assistants:** Phase 2 CLI entry points.
> Read [`AGENTS.md`](../AGENTS.md) before making changes.

---

## Purpose

Python-side CLI for Phase 2. The Node/TUI side (`suryafool-cli/`) routes
the Phase 2 commands here via `python -m cli.phase2 ... --json` and consumes
the JSONL event stream.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Package marker |
| `phase2.py` | ✅ Done | CLI argparse entry: `capabilities`, `scenarios`, `run`, `show`, `report` |

---

## CLI usage (from repo root)

```bash
python -m cli.phase2 capabilities
python -m cli.phase2 scenarios
python -m cli.phase2 run --scenario home --seed 42
python -m cli.phase2 run --scenario lab --json       # JSONL events to stdout
python -m cli.phase2 run --scenario lab --allow-risk safe_active  # explicit tier auth
python -m cli.phase2 run --scenario lab --allow-risk restricted --authorization-label "audit run"
python -m cli.phase2 show <run-id>
python -m cli.phase2 report <run-id>
```

## JSONL contract

With `--json`, `run` streams the same events the Node side already parses
(`agent.status`, `finding.created`, `error`, ...) to stdout, one per line.
The on-disk `events.jsonl` is identical.

## Authorization (Phase 2.6)

`--scenario` selects the simulated environment and grants **nothing**
authorization-wise. A run defaults to a PASSIVE-only `AuthorizationScope`.
To exercise SAFE_ACTIVE+ actions, provide `--allow-risk` (cumulative:
choosing a tier also grants all lower tiers):

| Flag value | Scope built |
|---|---|
| (no flag) | PASSIVE only |
| `--allow-risk safe_active` | PASSIVE + SAFE_ACTIVE |
| `--allow-risk sensitive_active` | PASSIVE + SAFE_ACTIVE + SENSITIVE_ACTIVE |
| `--allow-risk restricted` | PASSIVE + SAFE_ACTIVE + SENSITIVE_ACTIVE + RESTRICTED |

`--authorization-label TEXT` is optional human-readable context stored in
the run record's `AuthorizationScope.notes` (never a secret). When a higher
tier is granted, the CLI prints an `authorization: ENABLED ...` status line.

## Rules

- Human text output is for humans; JSON mode is the machine contract.
- Exit code 0 = completed/rejected (rejections are still valid runs),
  non-zero = failed run or bad arguments.