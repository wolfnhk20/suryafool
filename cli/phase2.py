"""
cli/phase2.py

Phase 2 deterministic core CLI. Wired into the existing CLI/TUI as a separate
sub-command so Phase 1 (bootstrap.agent) is untouched.

Usage (from repo root):

  python -m cli.phase2 capabilities                     # list available capabilities
  python -m cli.phase2 providers                        # list available backends
  python -m cli.phase2 scenarios                        # list predefined scenarios
  python -m cli.phase2 run --scenario home              # deterministic sim run
  python -m cli.phase2 run --scenario lab --seed 7      # custom seed
  python -m cli.phase2 run --scenario lab --plan ble_gatt_workflow --allow-risk sensitive_active
  python -m cli.phase2 run --scenario home --json        # JSONL event stream
  python -m cli.phase2 show <run-id>                    # print run summary
  python -m cli.phase2 report <run-id>                   # regenerate HTML report
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

# UTF-8 safety on Windows terminals
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from capabilities.registry import available_providers, default_registry
from core.mission import ActionRisk, AuthorizationScope, Run, RunStatus
from engine.logger import RunLogger, run_dir
from engine.runner import (
    RunEngine,
    active_inspection_plan,
    ble_gatt_workflow_plan,
    default_exploration_plan,
    ir_workflow_plan,
    nfc_workflow_plan,
    subghz_capture_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import write_report
from simulator.scenarios import build_scenario, list_scenarios


# ── JSONL streaming for TUI consumption ────────────────────────────────────────

# CLI --allow-risk values map to cumulative risk tiers. Selecting a tier
# also grants every lower tier (see AuthorizationScope.with_cumulative_tier).
_ALLOW_RISK_CHOICES = {
    "safe_active":      ActionRisk.SAFE_ACTIVE,
    "sensitive_active": ActionRisk.SENSITIVE_ACTIVE,
    "restricted":       ActionRisk.RESTRICTED,
}


def _build_authorization(allow_risk: str, label: str) -> AuthorizationScope:
    """Translate the CLI --allow-risk + --authorization-label pair into an
    AuthorizationScope. No flag -> PASSIVE-only default (preserves Phase 2)."""
    if not allow_risk:
        return AuthorizationScope.default()
    max_tier = _ALLOW_RISK_CHOICES[allow_risk]
    return AuthorizationScope.with_cumulative_tier(max_tier, notes=label or "")


def _authorization_status_line(scope: AuthorizationScope) -> str:
    """One-line CLI summary of the run's authorization — makes additional
    authorization obvious without exposing secrets (there are none)."""
    tiers = ",".join(sorted(r.value for r in scope.allowed_risks))
    if scope.enabled:
        label_part = f"  label={scope.notes!r}" if scope.notes else ""
        return (f"[suryafool] authorization: ENABLED  allowed: {tiers}"
                f"{label_part}")
    return "[suryafool] authorization: default (PASSIVE only)"


def _make_run_logger(run: Run, stream) -> RunLogger:
    """Wrap RunLogger so every appended event is also emitted to `stream` (if given).

    Used by the CLI/TUI bridge: the same event stream goes to disk AND stdout JSONL.
    """
    logger = RunLogger(run)

    original_append = logger.append_event

    def append_event(event):
        original_append(event)
        if stream is not None:
            stream.write(event.to_jsonl() + "\n")
            stream.flush()

    logger.append_event = append_event  # type: ignore[assignment]
    return logger


def _build_run(scenario: str, seed: int, objective: str,
               allow_risk: str = "", auth_label: str = "",
               plan: str = "exploration"
               ) -> tuple[Run, RunEngine, RunLogger]:
    """Construct a Run + Engine + Logger ready to execute the plan.

    The simulator is the only runtime provider (Phase 2.7.4 removed the
    Phase 2.5 Marauder spike from the runtime — Suryafool now owns its
    capability model). A future real-hardware backend plugs in by subclassing
    `CapabilityProvider` and registering itself via `registry.add_provider(...)`;
    the CLI does not carry a backend selector for the simulator-only present.
    """
    plan_name = plan
    if plan == "active_inspection":
        plan = active_inspection_plan()
    elif plan == "wifi_capture":
        plan = wifi_capture_plan()
    elif plan == "ble_gatt_workflow":
        plan = ble_gatt_workflow_plan()
    elif plan == "subghz_capture":
        plan = subghz_capture_plan()
    elif plan == "nfc_workflow":  # Phase 2.8.2
        plan = nfc_workflow_plan()
    elif plan == "ir_workflow":  # Phase 2.8.3
        plan = ir_workflow_plan()
    elif plan == "exploration":
        plan = default_exploration_plan()
    else:
        raise SystemExit(f"[suryafool] unknown plan: {plan!r}")

    registry = default_registry(environment=build_scenario(scenario, seed=seed))
    policy = PolicyEngine(registry=registry)

    authorization = _build_authorization(allow_risk, auth_label)
    run = Run(
        objective=objective,
        scenario=scenario,
        backend="simulator",
        seed=seed,
        authorization=authorization,
    )

    # If --json was used, also stream events to stdout so the Node-side parser
    # can consume them via the existing BinaryManager pipeline.
    stream = sys.stdout if _is_json_mode() else None
    logger = _make_run_logger(run, stream)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    engine._plan = plan  # ponytail: stash for cmd_run; not a public API
    engine._plan_name = plan_name
    return run, engine, logger


def _is_json_mode() -> bool:
    return getattr(_is_json_mode, "_flag", False)


def _set_json_mode(flag: bool) -> None:
    _is_json_mode._flag = flag  # type: ignore[attr-defined]


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_capabilities(args) -> int:
    from capabilities.base import DEFAULT_CAPABILITIES
    # Phase 2.7.1 — surface domain + mutates_state alongside name/key/risk/description.
    # The TUI (CapabilitiesView.js) reads only name/key/risk; extra keys are ignored
    # by JSON consumers, so this is additive.
    # Phase 2.8.0 — surface `supported` (resolved via the simulator provider against
    # a null env) so catalogue-staked-but-unimplemented domains (infrared/ethernet/
    # usb) are explicit instead of pretending to work. JSON gains a `supported`
    # field; human mode tags them `[UNSUPPORTED]`.
    registry = default_registry()
    def _cap_dict(c: "object") -> dict:
        supported = registry.resolve(c.capability, c.action).supported
        return {
            "name": c.name, "key": c.key, "risk": c.risk.value,
            "description": c.description,
            "domain": c.domain,
            "mutates_state": c.mutates_state,
            "produces_evidence": c.produces_evidence,
            "supported": supported,
        }
    out = [_cap_dict(c) for c in DEFAULT_CAPABILITIES]
    if _is_json_mode():
        sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")
    else:
        print("Available capabilities:")
        print(f"  total: {len(out)}")
        for c in out:
            tag = "STATEFUL" if c["mutates_state"] else "OBSERVE"
            ev_tag = " EVIDENCE" if c["produces_evidence"] else ""
            sup_tag = "" if c["supported"] else " [UNSUPPORTED]"
            print(f"  - {c['name']:22}  {c['key']:30}  [{c['risk']:14}]  "
                  f"({c['domain']})  [{tag}{ev_tag}]{sup_tag}")
    return 0


def cmd_providers(_args) -> int:
    out = [{"name": p, "description": _provider_description(p)} for p in available_providers()]
    if _is_json_mode():
        sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")
    else:
        print("Available providers:")
        for p in out:
            print(f"  - {p['name']:12}  {p['description']}")
    return 0


def _provider_description(name: str) -> str:
    return {
        "simulator": "Deterministic wireless simulator (Phase 2 default, no hardware).",
    }.get(name, "")


def cmd_scenarios(_args) -> int:
    out = list_scenarios()
    if _is_json_mode():
        sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")
    else:
        print("Available scenarios:")
        for s in out:
            print(f"  - {s['name']:10}  {s['description']}")
    return 0


def cmd_run(args) -> int:
    run, engine, logger = _build_run(
        scenario=args.scenario,
        seed=args.seed,
        objective=args.objective,
        allow_risk=getattr(args, "allow_risk", "") or "",
        auth_label=getattr(args, "authorization_label", "") or "",
        plan=getattr(args, "plan", "exploration"),
    )
    plan = getattr(engine, "_plan", default_exploration_plan())

    try:
        if not _is_json_mode():
            print(f"[suryafool] run={run.id}  backend={run.backend}  "
                  f"scenario={run.scenario or '-'}  seed={run.seed if run.seed is not None else '-'}")
            print(f"[suryafool] objective: {run.objective}")
            print(_authorization_status_line(run.authorization))
            print(f"[suryafool] plan: {len(plan)} action(s) via provider='{run.backend}' "
                  f"(plan={getattr(engine, '_plan_name', 'exploration')})")
            print("[suryafool] executing plan...")

        engine.run_plan(plan)
        logger.write_record()
        report_path = run_dir(run.id) / "report.html"
        write_report(run, report_path)

        if not _is_json_mode():
            print(f"[suryafool] status={run.status.value}")
            print(f"[suryafool] summary: {run.final_summary}")
            print(f"[suryafool] record:  {logger.record_path_str}")
            print(f"[suryafool] events:  {logger.events_path_str}")
            print(f"[suryafool] report:  {report_path}")

        return 0 if run.status in (RunStatus.COMPLETED, RunStatus.REJECTED) else 1
    finally:
        logger.close()
        # Disconnect any provider whose lifecycle holds resources open.
        for p in engine.registry.providers():
            disconnect = getattr(p, "disconnect", None)
            if callable(disconnect):
                try:
                    disconnect()
                except Exception:
                    pass


def cmd_show(args) -> int:
    record = run_dir(args.run_id) / "run.json"
    if not record.exists():
        print(f"[suryafool] run not found: {args.run_id}", file=sys.stderr)
        return 1
    data = json.loads(record.read_text(encoding="utf-8"))
    if _is_json_mode():
        sys.stdout.write(json.dumps(data, separators=(",", ":"), default=str) + "\n")
    else:
        print(f"Run: {data['id']}")
        print(f"  objective : {data['objective']}")
        print(f"  scenario  : {data['scenario']}")
        print(f"  backend   : {data['backend']}")
        print(f"  status    : {data['status']}")
        print(f"  started   : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['started_at']))}")
        if data.get('completed_at'):
            print(f"  completed : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['completed_at']))}")
        print(f"  actions   : {len(data['actions'])}")
        print(f"  findings  : {len(data['findings'])}")
        print(f"  evidence  : {len(data.get('evidence', []))}")
        print(f"  errors    : {len(data['errors'])}")
    return 0


def cmd_report(args) -> int:
    record = run_dir(args.run_id) / "run.json"
    if not record.exists():
        print(f"[suryafool] run not found: {args.run_id}", file=sys.stderr)
        return 1
    from core.mission import Run as RunCls
    run = RunCls.from_dict(json.loads(record.read_text(encoding="utf-8")))
    out = Path(args.output) if args.output else run_dir(args.run_id) / "report.html"
    write_report(run, out)
    if not _is_json_mode():
        print(f"[suryafool] report written: {out}")
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="suryafool-phase2",
        description="Suryafool Phase 2: deterministic core execution + simulator.",
    )
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable JSON / JSONL instead of human text.")
    sub = p.add_subparsers(dest="cmd", required=True)

    scap = sub.add_parser("capabilities", help="List available capabilities.")
    scap.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    sscn = sub.add_parser("scenarios",    help="List predefined scenarios.")
    sscn.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    sprv = sub.add_parser("providers",   help="List available backends/providers.")
    sprv.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    prun = sub.add_parser("run", help="Execute a deterministic run against a scenario.")
    prun.add_argument("--scenario", required=True, choices=["home", "lab", "crowded"],
                      help="Scenario name (home/lab/crowded).")
    prun.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    prun.add_argument("--plan", choices=["exploration", "active_inspection", "wifi_capture", "ble_gatt_workflow", "subghz_capture", "nfc_workflow", "ir_workflow"], default="exploration",
                      help="Deterministic plan to execute (default: exploration). "
                           "'active_inspection' runs the Phase 2.7 BLE active lifecycle "
                           "(discover->inspect->connect->write->inspect); pair with "
                           "--scenario lab --allow-risk sensitive_active. "
                           "'wifi_capture' runs the Phase 2.7.2 Wi-Fi capture lifecycle "
                           "(discover->inspect->capture.handshake->capture.pmkid->inspect); pair with "
                           "--scenario lab --allow-risk sensitive_active. "
                           "'ble_gatt_workflow' runs the Phase 2.7.3 BLE GATT pairing lifecycle "
                           "(discover->inspect->connect->pair->gatt.write->inspect); pair with "
                           "--scenario lab --allow-risk sensitive_active.")
    prun.add_argument("--objective", default="Explore the simulated wireless environment.",
                      help="Mission objective text.")
    prun.add_argument("--allow-risk",
                      choices=list(_ALLOW_RISK_CHOICES.keys()),
                      default=None,
                      help="Explicitly authorize a higher risk tier for this run "
                           "(cumulative: selecting a tier also grants all lower "
                           "tiers). Required to exercise SAFE_ACTIVE+ actions. "
                           "Default: PASSIVE only.")
    prun.add_argument("--authorization-label", default="",
                      help="Optional human-readable context stored in the run "
                           "record's AuthorizationScope.notes. Never a secret.")
    prun.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    pshow = sub.add_parser("show", help="Show a stored run.")
    pshow.add_argument("run_id")
    pshow.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    prep = sub.add_parser("report", help="Regenerate the HTML report for a run.")
    prep.add_argument("run_id")
    prep.add_argument("--output", help="Output HTML path.")
    prep.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    return p


def main() -> None:
    args = build_parser().parse_args()
    _set_json_mode(bool(getattr(args, "json", False)))
    handler = {
        "capabilities": cmd_capabilities,
        "scenarios":    cmd_scenarios,
        "providers":    cmd_providers,
        "run":          cmd_run,
        "show":         cmd_show,
        "report":       cmd_report,
    }[args.cmd]
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
