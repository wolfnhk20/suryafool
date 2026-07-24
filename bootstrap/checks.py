"""
bootstrap/checks.py

Read-only check() implementations for each manifest dependency.

DESIGN RULE: Every function here is safe to run without any gating.
No function in this module mutates system state.

Platform-aware:
    Manifest entries may have dict-form check_cmd / depends_on keyed by OS.
    Call resolve_entry() to flatten an entry for the current platform before
    passing it to check().
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional

from bootstrap.platform import OS, current_os, assert_supported


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    """Outcome of a single dependency check."""

    dependency: str
    passed: bool
    raw_output: str
    exit_code: int
    platform: str = ""          # which OS this check ran on
    reason: Optional[str] = None  # human-readable explanation when failed

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"CheckResult({self.dependency!r}, {status}, os={self.platform!r})"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run(cmd: str, timeout: int = 30) -> tuple[int, str]:
    """
    Run a shell command and return (exit_code, combined_output).
    Always uses shell=True because check_cmd strings may be composite
    (e.g. 'wsl -d Ubuntu -- python3 -c ...')
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = (result.stdout + result.stderr).strip()
        return result.returncode, combined
    except subprocess.TimeoutExpired:
        return -1, f"[timeout after {timeout}s]"
    except Exception as exc:  # noqa: BLE001
        return -1, f"[exception: {exc}]"


def _resolve_field(field_value: object, os_name: str) -> object:
    """
    Resolve a manifest field that may be a plain value (str / list) or a
    dict keyed by OS name.

    Examples:
        _resolve_field("which airmon-ng", "linux")
        → "which airmon-ng"

        _resolve_field({"windows": "wsl -d Ubuntu -- which airmon-ng",
                        "linux":   "which airmon-ng"}, "linux")
        → "which airmon-ng"

        _resolve_field({"windows": ["wsl-ubuntu"], "linux": []}, "linux")
        → []
    """
    if isinstance(field_value, dict):
        if os_name not in field_value:
            raise KeyError(
                f"Manifest field has no variant for platform {os_name!r}. "
                f"Available: {list(field_value.keys())}"
            )
        return field_value[os_name]
    return field_value


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_entry(entry: dict, os_name: str | None = None) -> dict:
    """
    Flatten a raw manifest entry into a platform-specific dict by resolving
    any dict-form fields (check_cmd, install_cmd, depends_on) into plain
    values for the given OS.

    If os_name is None, the current OS is detected automatically.

    Returns a new dict — the original is not mutated.
    """
    if os_name is None:
        os_name = current_os().value

    resolved = dict(entry)  # shallow copy

    for field in ("check_cmd", "install_cmd", "depends_on"):
        if field in resolved:
            resolved[field] = _resolve_field(resolved[field], os_name)

    return resolved


def filter_manifest(manifest: list[dict], os_name: str | None = None) -> list[dict]:
    """
    Return only the manifest entries that apply to the given OS.

    An entry without a 'platforms' key applies to ALL operating systems.
    An entry with 'platforms: [windows, linux, macos]' applies only to the
    listed platforms.
    """
    if os_name is None:
        os_name = current_os().value

    return [
        entry for entry in manifest
        if "platforms" not in entry or os_name in entry["platforms"]
    ]


def check(entry: dict, os_name: str | None = None) -> CheckResult:
    """
    Run the check_cmd for a manifest entry and evaluate success.

    Accepts either a raw entry (with dict-form fields) or an already-resolved
    entry. Resolves platform-specific fields internally if needed.

    Args:
        entry:   A single parsed manifest entry dict.
        os_name: Override the OS to resolve for. Defaults to current OS.
    """
    if os_name is None:
        os_name = current_os().value

    entry = resolve_entry(entry, os_name)

    name: str = entry["name"]
    cmd: str = entry["check_cmd"]

    exit_code, raw_output = _run(cmd)

    # ── Evaluate success ──────────────────────────────────────────────────────

    if "expect_contains" in entry:
        needle: str = entry["expect_contains"]
        passed = needle in raw_output
        reason = (
            None
            if passed
            else f"Expected {needle!r} in output but got:\n{raw_output}"
        )
        return CheckResult(
            dependency=name,
            passed=passed,
            raw_output=raw_output,
            exit_code=exit_code,
            platform=os_name,
            reason=reason,
        )

    if "expect_exit_code" in entry:
        expected: int = entry["expect_exit_code"]
        passed = exit_code == expected
        reason = (
            None
            if passed
            else (
                f"Expected exit code {expected}, got {exit_code}.\n"
                f"Output:\n{raw_output}"
            )
        )
        return CheckResult(
            dependency=name,
            passed=passed,
            raw_output=raw_output,
            exit_code=exit_code,
            platform=os_name,
            reason=reason,
        )

    # Fallback: exit code 0 = success
    passed = exit_code == 0
    return CheckResult(
        dependency=name,
        passed=passed,
        raw_output=raw_output,
        exit_code=exit_code,
        platform=os_name,
        reason=(
            None
            if passed
            else f"Non-zero exit code {exit_code}.\nOutput:\n{raw_output}"
        ),
    )


def check_all(manifest: list[dict], os_name: str | None = None) -> dict[str, CheckResult]:
    """
    Filter the manifest for the current OS, then run check() for every
    applicable entry in dependency order.

    Returns a mapping of dependency name → CheckResult.
    """
    if os_name is None:
        os_name = assert_supported().value

    applicable = filter_manifest(manifest, os_name)

    results: dict[str, CheckResult] = {}
    for entry in applicable:
        results[entry["name"]] = check(entry, os_name)
    return results
