"""
core/events.py

JSONL event types emitted by the Python backend to the CLI.
These mirror src/backend/events.js so the TUI parser can consume them.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Event type constants (kept in sync with suryafool-cli/src/backend/events.js) ──

COMMAND_STARTED = "command.started"
COMMAND_OUTPUT = "command.output"
COMMAND_PROGRESS = "command.progress"
COMMAND_COMPLETED = "command.completed"
COMMAND_FAILED = "command.failed"

FINDING_CREATED = "finding.created"
SCAN_STARTED = "scan.started"
SCAN_PROGRESS = "scan.progress"
SCAN_COMPLETED = "scan.completed"

AGENT_STATUS = "agent.status"
AGENT_STARTED = "agent.started"
AGENT_STOPPED = "agent.stopped"

VULN_FOUND = "vuln.found"

# Phase 2.7.5 — durable evidence record produced by a capture-style
# capability. Mirror in suryafool-cli/src/backend/events.js.
EVIDENCE_CREATED = "evidence.created"

LOG = "log"
ERROR = "error"

LLM_RESPONSE = "llm.response"


@dataclass
class Event:
    type: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        payload = {"type": self.type, "timestamp": self.timestamp, **self.data}
        return json.dumps(payload, separators=(",", ":"), default=str)


# ── Helpers ────────────────────────────────────────────────────────────────────

def event(type_: str, **data: Any) -> Event:
    return Event(type=type_, data=data)


def emit(stream, type_: str, **data: Any) -> None:
    """Emit a JSONL event to a writable stream. Safe no-op if stream is None."""
    if stream is None:
        return
    e = event(type_, **data)
    stream.write(e.to_jsonl() + "\n")
    stream.flush()
