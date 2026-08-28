# CONTEXT.md — reports/

> **For AI coding assistants:** Phase 2 HTML report generation.
> Read [`AGENTS.md`](../AGENTS.md) before making changes.

---

## Purpose

Generates a standalone HTML report from a `Run` record — nothing is
reconstructed from terminal text. The report is plain (embedded CSS,
Suryafool sunflower-gold palette), and intentionally not over-engineered.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Package marker |
| `html_report.py` | ✅ Done | `render_run(run) -> str`, `write_report(run, path)` |

---

## Sections

- Run header (ID, objective, status badge, scenario, seed, timing, **Authorization** — Phase 2.6)
- Capabilities (which providers were exercised)
- Timeline (per-action: capability, **authoritative risk** (Phase 2.6),
  provider, policy verdict, observation summary, **per-action evidence** (Phase 2.7.5),
  errors; rejected/failed items highlighted)
- Findings (entity tables with confidence badges)
- **Evidence** (Phase 2.7.5): per-run table of `Run.evidence` with provenance
  columns (kind, target, source capability + source_action_id, summary,
  metadata) — distinct from Findings. Empty section renders as
  "No evidence captured by this run." so report consumers can rely on the
  section existing.
- Errors / rejected actions
- Final status

> **Phase 2.6:** The header carries an Authorization line — `ENABLED`
  badge + comma-joined allowed tiers + escaped `notes` when the run had a
  non-default scope. The per-action risk badge shows the AUTHORITATIVE
  catalogue `cap.risk` (resolved at executor time and persisted on
  `ActionRecord.authoritative_risk`), not the caller-declared
  `request.risk` — the latter stays in `run.json > actions[].request.risk`
  for forensic readers.

## Rules

- Pure function of the Run dataclass — no I/O inside `render_run`.
- Report must render even if a run has zero actions or all rejections.