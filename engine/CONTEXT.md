# CONTEXT.md — engine/

> **For AI coding assistants:** Phase 2 core execution engine + logging.
> Read [`AGENTS.md`](../AGENTS.md) before making changes.

---

## Purpose

The RunEngine is the central coordinator of a Suryafool run. It wires
together the capability registry, policy gate, and providers, and records
**everything** — actions, decisions, observations, errors — into the Run
dataclass and JSONL event log.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Package marker |
| `runner.py` | ✅ Done | `RunEngine`, `default_exploration_plan()` (simulator, 4 actions), `active_inspection_plan()` (Phase 2.7, 5 actions: ble discover→inspect→connect→write→inspect), `wifi_capture_plan()` (Phase 2.7.2, 5 actions: wifi discover→inspect→capture.handshake→capture.pmkid→inspect), `ble_gatt_workflow_plan()` (Phase 2.7.3, 6 actions: ble discover→inspect→connect→pair→gatt.write→inspect) |
| `logger.py` | ✅ Done | `RunLogger` (run.json + events.jsonl), `runs_root()`, `run_dir()` |

---

## Flow

```
ActionRequest
  → registry.resolve()          → CapabilityDecision
  → resolve cap.risk            → record.authoritative_risk   (Phase 2.6)
  → policy.validate()           → PolicyDecision (ALLOW/REJECT)
  → provider.execute()          → Observation   (only if ALLOW)
  → ActionRecord stored in Run  (with authoritative_risk + evidence mirror)
  → run.json + events.jsonl updated on every action
  → one evidence.created JSONL event per EvidenceRecord (Phase 2.7.5)
```

> **Phase 2.6:** The RunEngine no longer derives authorization from scenario
> selection. `PolicyContext` is built from `self.run.authorization` (an
> explicit `AuthorizationScope`), and the authoritative `cap.risk` from the
> catalogue is resolved ONCE per action and persisted to the action record
> so reports can show it without a live registry.

> **Phase 2.7.5:** After a successful `provider.execute()`, the engine mirrors
> `observation.evidence` to both `record.evidence` and `run.evidence`, stamps
> each item's `source_action_id` with the originating `ActionRequest.id`
> (which the simulator deliberately cannot see), and emits one
> `evidence.created` JSONL event per item. Policy-rejected actions never
> reach this code path so they produce zero evidence; failed simulator paths
> return `Observation(evidence=[])` so the propagation loop is a no-op for
> them. The simulator is the source of truth for WHAT was captured; the
> engine is the source of truth for provenance the simulator can't see.

On rejection the action is recorded (not executed), errors are tracked, and
the run continues with the next plan step. An unexpected provider crash
flips the run to FAILED.

---

## Artifacts (per run)

```
~/.suryafool/runs/<run-id>/
├── run.json        # full structured run record (single JSON)
├── events.jsonl    # append-only JSONL audit trail
└── report.html     # generated HTML report (by reports/)
```

`SURYAFOOL_RUNS_DIR` env var overrides the base directory.

---

## Rules

No LLM in the core loop — the plan comes from `default_exploration_plan()`
(simulator). The CLI selects the plan via `--plan {exploration,active_inspection,wifi_capture,ble_gatt_workflow}`.
- Every executed action must be recorded before the run completes.
- Never bury important state only in terminal output — it lives in run.json.