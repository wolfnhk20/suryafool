"""
bootstrap/agent.py

Bootstrap / Environment Agent entry point.

Usage:
    python -m bootstrap.agent --check-only   # read-only status table, no changes
    python -m bootstrap.agent                # full doctor run with remediation

New flow:
  1. CHECK all dependencies (read-only, no LLM)
  2. For each failure:
     a. If dependency in manifest → use manifest install_cmd (known)
     b. If NOT in manifest → call LLM to propose fix (unknown)
     c. Display EXACT command → ask for approval → execute verbatim
  3. Always re-verify after remediation
  4. Final report distinguishes manifest vs LLM resolution, tracks LLM provider
"""

from __future__ import annotations

import argparse
import io
import sys

# Force UTF-8 output on Windows terminals that default to cp1252.
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load .env before anything reads os.environ (provider keys, rate limit, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional — env vars may be set by the shell instead

import os
from dataclasses import dataclass
from typing import Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box

from bootstrap.platform import assert_supported, is_admin
from bootstrap.checks import check_all, check, filter_manifest, resolve_entry
from bootstrap.remediate import remediate
from bootstrap.provisioning_guardian import check_and_prompt
from core.llm import llm_call, LLMResult

console = Console()


# ── Result tracking ─────────────────────────────────────────────────────────────

@dataclass
class RemediationRecord:
    """Tracks how a dependency was resolved."""
    dependency: str
    resolved: bool
    method: str          # "manifest" | "llm" | "manual" | "failed"
    provider: Optional[str] = None  # "openrouter" | "opencode_zen" | None
    install_cmd: Optional[str] = None
    error: Optional[str] = None


# ── Manifest loader ───────────────────────────────────────────────────────────

def load_manifest(path: str = "bootstrap/manifest.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["dependencies"]


# ── LLM: Propose remediation for UNKNOWN dependencies ──────────────────────────

def propose_remediation_llm(
    entry: dict,
    os_name: str,
    check_raw_output: str,
    check_expected: str,
) -> Optional[str]:
    """
    Ask LLM to propose a remediation command for a dependency NOT in manifest.
    
    Returns the proposed command string, or None if LLM unavailable.
    """
    system = (
        "You are the Suryafool Bootstrap Agent's remediation planner.\n"
        "A dependency check failed and there is NO manifest entry for it.\n"
        "Propose a SINGLE shell command to fix it.\n\n"
        "RULES:\n"
        "- Output ONLY the command. No markdown, no explanation, no formatting.\n"
        "- Command must be appropriate for the OS.\n"
        "- Use package managers (apt, winget, brew), not manual downloads.\n"
        "- For Windows WSL dependencies, prefix with 'wsl -d Ubuntu -- '\n"
        "- If the dependency is likely already installed but check fails, "
        "propose a VERIFICATION command instead of install.\n"
        "- Maximum 1 command. No pipes to multiple commands unless essential.\n"
        "- The command will be shown to the user for approval before execution.\n"
    )

    human = (
        f"Dependency: {entry['name']}\n"
        f"OS: {os_name}\n\n"
        f"Check command: {entry['check_cmd']}\n"
        f"Check failed: {check_raw_output[:500]}\n"
        f"Expected: {check_expected}\n\n"
        "Propose the single best remediation command:"
    )

    result: LLMResult = llm_call(
        prompt=f"{system}\n\n{human}",
        max_tokens=500,
    )

    if not result.success:
        console.print(f"  [dim]LLM unavailable: {result.error}[/dim]")
        return None

    cmd = result.content.strip()
    # Clean up any markdown formatting
    cmd = cmd.replace("```bash", "").replace("```sh", "").replace("```", "").strip()
    
    console.print(f"  [dim]LLM proposed via {result.provider_used}: {cmd}[/dim]")
    return cmd


# ── Display helpers ───────────────────────────────────────────────────────────

def print_results_table(results: dict, os_name: str, title: str = "Environment Check") -> bool:
    """Print a Rich status table. Returns True if all checks passed."""
    table = Table(
        title=f"SURYAFOOL - {title}  [dim](OS: {os_name})[/dim]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        min_width=60,
    )
    table.add_column("Dependency", style="bold white", min_width=22)
    table.add_column("Status", min_width=8)
    table.add_column("Notes", style="dim", max_width=50)

    all_pass = True
    for name, result in results.items():
        if result.passed:
            status = "[green][OK][/green]"
            notes = ""
        else:
            status = "[red][FAIL][/red]"
            first_line = (result.reason or "").splitlines()[0]
            notes = first_line[:90] if first_line else ""
            all_pass = False
        table.add_row(name, status, notes)

    console.print()
    console.print(table)
    console.print()
    return all_pass


# ── Dependency order helpers ──────────────────────────────────────────────────

def deps_satisfied(entry: dict, os_name: str, results: dict) -> tuple[bool, list[str]]:
    resolved = resolve_entry(entry, os_name)
    depends_on: list[str] = resolved.get("depends_on", [])
    blocking = [d for d in depends_on if d in results and not results[d].passed]
    return (len(blocking) == 0), blocking


# ── Modes ─────────────────────────────────────────────────────────────────────

def run_check_only(manifest: list[dict], os_name: str) -> int:
    """Read-only mode: run checks, print results, exit. No system changes."""
    console.print("[bold cyan]Running checks (read-only - no changes will be made)...[/bold cyan]")

    results = check_all(manifest, os_name)
    all_pass = print_results_table(results, os_name)

    if all_pass:
        console.print("[bold green][OK] Environment ready.[/bold green]\n")
        return 0
    else:
        failed = [n for n, r in results.items() if not r.passed]
        console.print(
            f"[bold red][FAIL] {len(failed)} check(s) failed:[/bold red] "
            + ", ".join(failed)
        )
        console.print(
            "[dim]Run without --check-only to attempt automatic remediation.[/dim]\n"
        )
        return 1


def run_full_agent(manifest: list[dict], os_name: str) -> int:
    """
    Full doctor run with hybrid remediation:
      1. Check all dependencies.
      2. For each failure:
         - If in manifest: use manifest install_cmd (known)
         - If NOT in manifest: call LLM to propose fix (unknown)
      3. Display EXACT command → ask for approval → execute verbatim
      4. Always re-verify after remediation
      5. Final report distinguishes manifest vs LLM resolution
    """
    console.print(Rule("[bold cyan]SURYAFOOL Bootstrap Agent[/bold cyan]"))
    console.print(f"[dim]OS detected: {os_name}[/dim]\n")

    # Step 1: Initial check
    console.print("[bold]Step 1:[/bold] Running environment checks...\n")
    applicable = filter_manifest(manifest, os_name)
    results = check_all(manifest, os_name)
    all_pass = print_results_table(results, os_name, title="Initial Check")

    if all_pass:
        console.print("[bold green][OK] All dependencies satisfied. Environment ready.[/bold green]\n")
        return 0

    # Admin privilege warning
    if not is_admin():
        elevated_needed = []
        for entry in applicable:
            resolved = resolve_entry(entry, os_name)
            elevation = str(resolved.get("requires_elevation", "none")).lower()
            if elevation in ("windows_admin", "wsl_sudo") and results.get(entry["name"]) and not results[entry["name"]].passed:
                elevated_needed.append(entry["name"])
        if elevated_needed:
            console.print()
            console.print(
                Panel(
                    "These failed dependencies need elevated privileges to fix:\n"
                    f"  {', '.join(elevated_needed)}\n\n"
                    "You are NOT running as Administrator. Commands requiring elevation will fail.\n"
                    "Close this window and re-run from an elevated PowerShell (Run as Administrator).",
                    title="[bold red]Warning — Not Running as Admin[/bold red]",
                    border_style="red",
                    expand=False,
                )
            )
            console.print()

    # Step 2: Remediation loop
    console.print(Rule("[bold yellow]Remediation[/bold yellow]"))
    console.print("[dim]Processing failed dependencies in order...[/dim]\n")

    skipped: list[str] = []
    records: list[RemediationRecord] = []

    for entry in applicable:
        name = entry["name"]
        result = results.get(name)

        # Already passing
        if result and result.passed:
            continue

        # Check if dependencies are satisfied
        satisfied, blocking = deps_satisfied(entry, os_name, results)
        if not satisfied:
            console.print(
                f"  [dim]Skipping [bold]{name}[/bold] — blocked by: "
                + ", ".join(f"[red]{b}[/red]" for b in blocking)
                + "[/dim]"
            )
            records.append(RemediationRecord(
                dependency=name, resolved=False, method="skipped",
                error=f"Blocked by: {', '.join(blocking)}"
            ))
            continue

        # Resolve the install command (manifest or LLM)
        resolved = resolve_entry(entry, os_name)
        install_cmd = resolved.get("install_cmd")
        method = "manifest"
        provider = None

        if not install_cmd:
            # UNKNOWN dependency - call LLM to propose
            check_expected = (
                entry.get("expect_contains")
                or str(entry.get("expect_exit_code", "exit 0"))
            )
            console.print(f"  [bold cyan]No manifest entry — asking LLM for remediation...[/bold cyan]")
            install_cmd = propose_remediation_llm(
                entry=entry,
                os_name=os_name,
                check_raw_output=result.raw_output,
                check_expected=check_expected,
            )
            method = "llm"
            if install_cmd:
                provider = "openrouter"  # will be updated by actual provider used
            else:
                console.print(f"  [red]LLM could not propose a fix.[/red]")

        if not install_cmd:
            records.append(RemediationRecord(
                dependency=name, resolved=False, method="failed",
                error="No install command available (not in manifest, LLM failed)"
            ))
            continue

        # Show the EXACT command and ask for approval
        console.print()
        console.print(
            Panel(
                f"[bold]Proposed remediation for [cyan]{name}[/cyan] [dim](via {method})[/dim]:[/bold]\n\n"
                f"[bold cyan]{install_cmd}[/bold cyan]",
                title=f"[bold]Confirm Command — {name}[/bold]",
                border_style="cyan",
                expand=False,
            )
        )

        # Ask via Provisioning Guardian
        # Create a temporary entry with the resolved command
        temp_entry = dict(resolved)
        temp_entry["install_cmd"] = install_cmd
        approved = check_and_prompt(temp_entry, os_name)

        if not approved:
            records.append(RemediationRecord(
                dependency=name, resolved=False, method="skipped",
                install_cmd=install_cmd, error="Denied by user"
            ))
            continue

        # Execute
        console.print(f"  Executing [bold]{name}[/bold]...")
        rem_result = remediate(temp_entry, os_name, show_output=True)

        # Re-verify
        console.print(f"  Verifying [bold]{name}[/bold]...")
        verify = check(temp_entry, os_name)
        results[name] = verify

        if verify.passed:
            console.print(f"  [green][OK][/green] {name} fixed and verified.\n")
            records.append(RemediationRecord(
                dependency=name, resolved=True, method=method,
                provider=provider, install_cmd=install_cmd
            ))
        else:
            console.print(f"  [red][FAIL][/red] {name} still failing: {verify.reason[:100]}\n")
            records.append(RemediationRecord(
                dependency=name, resolved=False, method=method,
                provider=provider, install_cmd=install_cmd,
                error=verify.reason
            ))

    # Step 3: Final report
    console.print(Rule("[bold]Final Report[/bold]"))

    fixed_manifest = [r.dependency for r in records if r.resolved and r.method == "manifest"]
    fixed_llm = [r.dependency for r in records if r.resolved and r.method == "llm"]
    skipped = [r.dependency for r in records if not r.resolved and r.method == "skipped"]
    failed = [r.dependency for r in records if not r.resolved and r.method in ("failed", "llm")]

    if fixed_manifest:
        console.print(f"  [green]Resolved via manifest ({len(fixed_manifest)}):[/green] " + ", ".join(fixed_manifest))
    if fixed_llm:
        console.print(f"  [green]Resolved via LLM ({len(fixed_llm)}):[/green] " + ", ".join(fixed_llm))
        # Show provider breakdown
        providers = {}
        for r in records:
            if r.resolved and r.method == "llm" and r.provider:
                providers[r.provider] = providers.get(r.provider, 0) + 1
        for prov, count in providers.items():
            console.print(f"    [dim]→ {count} via {prov}[/dim]")
    if skipped:
        console.print(f"  [yellow]Skipped ({len(skipped)}):[/yellow] " + ", ".join(skipped))
    if failed:
        console.print(f"  [red]Failed ({len(failed)}):[/red] " + ", ".join(failed))

    console.print()

    if not failed and not skipped:
        console.print("[bold green][OK] Environment ready. Mission agents can now run.[/bold green]\n")
        return 0
    elif not failed:
        console.print(
            "[yellow]Environment partially ready.[/yellow] "
            f"[dim]{len(skipped)} skipped.[/dim]\n"
        )
        return 0
    else:
        console.print(
            "[bold red][FAIL] Environment not fully ready.[/bold red] "
            "Resolve the failing dependencies above and re-run.\n"
        )
        return 1


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="suryafool-bootstrap",
        description="Suryafool Bootstrap Agent - verify and repair the host environment.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run read-only checks and print status. No system changes.",
    )
    parser.add_argument(
        "--manifest",
        default="bootstrap/manifest.yaml",
        help="Path to the dependency manifest (default: bootstrap/manifest.yaml).",
    )
    args = parser.parse_args()

    try:
        os_platform = assert_supported()
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    manifest = load_manifest(args.manifest)

    if args.check_only:
        sys.exit(run_check_only(manifest, os_platform.value))
    else:
        sys.exit(run_full_agent(manifest, os_platform.value))


if __name__ == "__main__":
    main()