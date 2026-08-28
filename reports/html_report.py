"""
reports/html_report.py

Generate a standalone HTML report from a Run record.

The report is intentionally plain: one self-contained HTML file with
embedded CSS in the Suryafool sunflower-gold palette. It reads ONLY from
the structured Run dataclass — nothing reconstructed from terminal text.

Sections:
  - Run header (ID, objective, status, timing, scenario/seed)
  - Capability summary (which capabilities ran, who provided them)
  - Timeline of actions (with policy + outcome)
  - Observations / findings (per-capability tables)
  - Errors / rejected actions
  - Final summary
"""

from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any

from core.confidence import Confidence
from core.mission import Run


_CSS = """
:root {
  --primary: #E8B339;
  --secondary: #D97706;
  --accent: #65A30D;
  --success: #65A30D;
  --error: #DC2626;
  --warning: #D97706;
  --bg: #0C0A09;
  --surface: #1C1917;
  --border: #44403C;
  --text: #FAFAF9;
  --muted: #A8A29E;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 32px;
  background: var(--bg);
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  line-height: 1.55;
}
.container { max-width: 1100px; margin: 0 auto; }
h1 {
  font-size: 28px;
  color: var(--primary);
  margin: 0 0 8px 0;
  letter-spacing: 0.04em;
}
h2 {
  font-size: 18px;
  color: var(--primary);
  margin: 32px 0 12px 0;
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}
h3 {
  font-size: 14px;
  color: var(--secondary);
  margin: 18px 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.meta { color: var(--muted); font-size: 12px; }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  margin: 12px 0;
}
table { width: 100%; border-collapse: collapse; margin: 8px 0; }
th, td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
th { color: var(--secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
td { font-size: 13px; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: 1px solid;
}
.badge.completed { color: var(--success); border-color: var(--success); }
.badge.failed    { color: var(--error);   border-color: var(--error); }
.badge.rejected  { color: var(--warning); border-color: var(--warning); }
.badge.running   { color: var(--primary); border-color: var(--primary); }
.badge.confirmed { color: var(--success); border-color: var(--success); }
.badge.likely    { color: var(--secondary); border-color: var(--secondary); }
.badge.possible  { color: var(--warning); border-color: var(--warning); }
.badge.unknown   { color: var(--muted); border-color: var(--muted); }
.code { color: var(--primary); }
.muted { color: var(--muted); }
.danger { color: var(--error); }
.success { color: var(--success); }
ul { padding-left: 22px; margin: 4px 0; }
li { margin: 2px 0; }
.footer { color: var(--muted); font-size: 11px; margin-top: 32px; text-align: center; }
.kv { display: grid; grid-template-columns: 180px 1fr; gap: 4px 12px; }
.kv .k { color: var(--muted); }
.kv .v { color: var(--text); }
.timeline-item { padding: 10px 12px; border-left: 2px solid var(--primary); margin: 6px 0; background: var(--surface); }
.timeline-item.rejected { border-left-color: var(--warning); }
.timeline-item.failed { border-left-color: var(--error); }
.timeline-item .ts { color: var(--muted); font-size: 11px; }
.attr-table th { background: transparent; }
.attr-table td.k { color: var(--muted); width: 30%; }
"""


def _badge(value: str, mapping: dict[str, str]) -> str:
    cls = mapping.get(value.lower(), "")
    return f'<span class="badge {cls}">{html.escape(value)}</span>'


_STATUS_BADGES = {
    "completed": "completed",
    "failed":    "failed",
    "rejected":  "rejected",
    "running":   "running",
}

_CONFIDENCE_BADGES = {
    "confirmed": "confirmed",
    "likely":    "likely",
    "possible":  "possible",
    "unknown":   "unknown",
}


def _fmt_ts(t: float | None) -> str:
    if t is None or t == 0:
        return "—"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def _attr_table(attrs: dict[str, Any]) -> str:
    if not attrs:
        return '<p class="muted">(no attributes)</p>'
    rows = "".join(
        f"<tr><td class='k'>{html.escape(str(k))}</td>"
        f"<td>{html.escape(str(v))}</td></tr>"
        for k, v in attrs.items()
    )
    return f"<table class='attr-table'>{rows}</table>"


def render_run(run: Run) -> str:
    cap_decisions = [
        a.capability_decision for a in run.actions if a.capability_decision is not None
    ]
    used_providers = sorted({d.provider for d in cap_decisions if d.supported})
    rejected = [a for a in run.actions if a.policy_decision and not a.policy_decision.allowed]
    failed   = [a for a in run.actions if a.error]

    parts: list[str] = []
    parts.append(f"<!DOCTYPE html><html><head><meta charset='utf-8'>")
    parts.append(f"<title>Suryafool Run Report — {html.escape(run.id)}</title>")
    parts.append(f"<style>{_CSS}</style></head><body><div class='container'>")

    # Header
    parts.append(f"<h1>SURYAFOOL :: RUN REPORT</h1>")
    parts.append(f"<p class='meta'>Generated {time.strftime('%Y-%m-%d %H:%M:%S')}</p>")
    parts.append(_badge(run.status.value, _STATUS_BADGES))
    parts.append("<div class='card'>")
    # Authorization line — PASSIVE-only shows as default; explicit grants show
    # the allowed tiers + escaped notes. Notes are user-supplied text.
    auth = run.authorization
    if auth.enabled:
        tiers = ", ".join(sorted(r.value for r in auth.allowed_risks))
        parts.append(
            f"<div class='kv'>"
            f"<div class='k'>Authorization</div><div class='v'><span class='badge running'>ENABLED</span> "
            f"allowed: <span class='code'>{html.escape(tiers)}</span>"
            + (f" &middot; label: {html.escape(auth.notes)}" if auth.notes else "")
            + f"</div>"
            f"</div>"
        )
    parts.append(f"<div class='kv'>"
                 f"<div class='k'>Run ID</div><div class='v'><span class='code'>{html.escape(run.id)}</span></div>"
                 f"<div class='k'>Objective</div><div class='v'>{html.escape(run.objective or '(none)')}</div>"
                 f"<div class='k'>Scenario</div><div class='v'>{html.escape(run.scenario or '(none)')}</div>"
                 f"<div class='k'>Backend</div><div class='v'>{html.escape(run.backend)}</div>"
                 f"<div class='k'>Seed</div><div class='v'>{html.escape(str(run.seed) if run.seed is not None else '—')}</div>"
                 f"<div class='k'>Started</div><div class='v'>{html.escape(_fmt_ts(run.started_at))}</div>"
                 f"<div class='k'>Completed</div><div class='v'>{html.escape(_fmt_ts(run.completed_at))}</div>"
                 f"<div class='k'>Duration</div><div class='v'>{run.duration():.2f}s</div>"
                 f"</div>")
    parts.append("</div>")

    # Capabilities
    parts.append("<h2>CAPABILITIES</h2>")
    if used_providers:
        parts.append("<p>Backend providers used by this run:</p>")
        parts.append("<ul>" + "".join(f"<li><span class='code'>{html.escape(p)}</span></li>" for p in used_providers) + "</ul>")
    else:
        parts.append("<p class='muted'>No capabilities were exercised.</p>")

    # Timeline
    parts.append("<h2>TIMELINE</h2>")
    if not run.actions:
        parts.append("<p class='muted'>No actions.</p>")
    else:
        for idx, a in enumerate(run.actions, start=1):
            request = a.request
            cls = ""
            status_label = "completed"
            if a.policy_decision and not a.policy_decision.allowed:
                cls = "rejected"
                status_label = "rejected"
            elif a.error:
                cls = "failed"
                status_label = "failed"
            parts.append(f"<div class='timeline-item {cls}'>")
            parts.append(
                f"<div class='ts'>#{idx}  "
                f"{_fmt_ts(a.started_at)} → {_fmt_ts(a.completed_at)}  "
                f"<span class='badge {status_label}'>{status_label}</span></div>"
            )
            # Authoritative risk (from the catalogue) — this is what the
            # policy layer consulted. Caller-declared request.risk stays in
            # run.json for forensic readers; the report shows the truth.
            risk_label = (a.authoritative_risk.value
                          if a.authoritative_risk is not None
                          else request.risk.value)
            parts.append(
                f"<div><b>{html.escape(request.capability)}.{html.escape(request.action)}</b>  "
                f"<span class='muted'>(risk={html.escape(risk_label)})</span></div>"
            )
            if a.capability_decision:
                parts.append(
                    f"<div class='muted'>provider: "
                    f"<span class='code'>{html.escape(a.capability_decision.provider or '—')}</span></div>"
                )
            if a.policy_decision:
                if a.policy_decision.allowed:
                    parts.append(f"<div class='success'>policy: ALLOW</div>")
                else:
                    parts.append(
                        "<div class='danger'>policy: REJECT</div>"
                        "<ul>" + "".join(f"<li class='danger'>{html.escape(r)}</li>" for r in a.policy_decision.reasons) + "</ul>"
                    )
            if a.observation:
                parts.append(f"<div>observation: {html.escape(a.observation.summary)}</div>")
            # Phase 2.7.5 — per-action evidence provenance (the report must
            # let the reader answer "what evidence did this action produce,
            # and where did it come from?").
            if a.evidence:
                parts.append("<div class='evidence'><b>Evidence produced:</b>")
                parts.append("<ul>")
                for ev in a.evidence:
                    parts.append(
                        f"<li><span class='code'>{html.escape(ev.kind)}</span> "
                        f"&middot; {html.escape(ev.summary)} "
                        f"<span class='muted'>target={html.escape(ev.target_entity_id)} "
                        f"({html.escape(ev.target_entity_type)})</span></li>"
                    )
                parts.append("</ul></div>")
            if a.error:
                parts.append(f"<div class='danger'>error: {html.escape(a.error)}</div>")
            parts.append("</div>")

    # Findings
    parts.append("<h2>FINDINGS</h2>")
    if not run.findings:
        parts.append("<p class='muted'>No findings recorded.</p>")
    else:
        parts.append("<table><tr><th>Type</th><th>Label / ID</th><th>Confidence</th><th>Attributes</th></tr>")
        for f in run.findings:
            conf = _badge(str(f.get("confidence", "")).upper(), _CONFIDENCE_BADGES)
            parts.append(
                f"<tr><td>{html.escape(str(f.get('entity_type', '')))}</td>"
                f"<td>{html.escape(str(f.get('label', '')))} "
                f"<div class='muted'>{html.escape(str(f.get('id', '')))}</div></td>"
                f"<td>{conf}</td>"
                f"<td>{_attr_table(f.get('attributes', {}))}</td></tr>"
            )
        parts.append("</table>")

    # Phase 2.7.5 — Evidence section. Distinct from Findings: findings are raw
    # entity observations surfaced by any executed action; evidence is durable
    # capture output produced by `produces_evidence=True` capabilities (Phase
    # 2.7.5 ships `wifi.capture.handshake`). The provenance pair
    # (source_action_id, source_capability.source_action) lets the reader
    # answer "what evidence did this action produce, and where did it come
    # from?" without re-running the simulator.
    parts.append("<h2>EVIDENCE</h2>")
    if not run.evidence:
        parts.append("<p class='muted'>No evidence captured by this run.</p>")
    else:
        parts.append("<table><tr><th>Kind</th><th>Target</th><th>Source (action)</th><th>Summary</th><th>Metadata</th></tr>")
        for ev in run.evidence:
            source = f"{html.escape(ev.source_capability)}.{html.escape(ev.source_action)}"
            source_id = html.escape(ev.source_action_id or "—")
            parts.append(
                f"<tr><td><span class='code'>{html.escape(ev.kind)}</span></td>"
                f"<td>{html.escape(ev.target_entity_id)} "
                f"<div class='muted'>{html.escape(ev.target_entity_type)}</div></td>"
                f"<td>{source}<div class='muted'>{source_id}</div></td>"
                f"<td>{html.escape(ev.summary)}</td>"
                f"<td>{_attr_table(ev.metadata)}</td></tr>"
            )
        parts.append("</table>")

    # Errors
    if run.errors:
        parts.append("<h2>ERRORS</h2>")
        parts.append("<ul>" + "".join(f"<li class='danger'>{html.escape(e)}</li>" for e in run.errors) + "</ul>")

    # Final summary
    parts.append("<h2>FINAL STATUS</h2>")
    parts.append(f"<div class='card'><b>{html.escape(run.final_summary or '(no summary)')}</b></div>")

    parts.append("<div class='footer'>Suryafool — universal agentic wireless platform — Phase 2 deterministic core.</div>")
    parts.append("</div></body></html>")
    return "".join(parts)


def write_report(run: Run, path: Path) -> Path:
    path.write_text(render_run(run), encoding="utf-8")
    return path
