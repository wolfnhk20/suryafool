"""
engine/logger.py

Structured run logger.

Each run produces:

  - One JSON file with the full run record (machine-readable)
  - One JSONL file with an append-only stream of events (audit trail)

Both files are written under ~/.suryafool/runs/<run-id>/
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

from core.events import Event, emit
from core.mission import Run


def runs_root() -> Path:
    """Return the directory where run artifacts are stored."""
    base = Path(os.environ.get("SURYAFOOL_RUNS_DIR", str(Path.home() / ".suryafool" / "runs")))
    base.mkdir(parents=True, exist_ok=True)
    return base


def run_dir(run_id: str) -> Path:
    d = runs_root() / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


class RunLogger:
    """Writes a run record + event JSONL for a single Run."""

    def __init__(self, run: Run):
        self.run = run
        self.dir = run_dir(run.id)
        self.record_path = self.dir / "run.json"
        self.events_path = self.dir / "events.jsonl"
        self._events_file = open(self.events_path, "a", encoding="utf-8")

    def close(self) -> None:
        try:
            self._events_file.close()
        except Exception:
            pass

    # ── File writes ───────────────────────────────────────────────────────────
    def write_record(self) -> None:
        with open(self.record_path, "w", encoding="utf-8") as f:
            json.dump(self.run.to_dict(), f, indent=2, default=str)

    def append_event(self, event: Event) -> None:
        self._events_file.write(event.to_jsonl() + "\n")
        self._events_file.flush()

    # ── Convenience ──────────────────────────────────────────────────────────
    def log_event(self, type_: str, **data: Any) -> Event:
        e = Event(type=type_, data=data)
        self.append_event(e)
        return e

    @property
    def record_path_str(self) -> str:
        return str(self.record_path)

    @property
    def events_path_str(self) -> str:
        return str(self.events_path)
