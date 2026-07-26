"""
bootstrap/provisioning_guardian.py

Elevation gate for the Bootstrap Agent.

Elevation types:
  - none:              No elevation needed. Soft prompt only.
  - windows_admin:     Requires elevated Windows shell (Run as Administrator).
                       Commands: wsl --install, winget, dism, etc.
  - wsl_sudo:          Requires sudo inside WSL. Interactive password prompt
                       reaches user's terminal. Commands: apt install, etc.

RULES (non-negotiable):
  - Elevation type comes from manifest entry — not the LLM's justification.
  - The model cannot bypass this by rephrasing.
  - Always show the EXACT command before asking for approval.
  - Order: resolve command → display literal command → ask → execute verbatim.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from bootstrap.checks import resolve_entry

console = Console()


class ElevationType(str, Enum):
    NONE = "none"
    WINDOWS_ADMIN = "windows_admin"
    WSL_SUDO = "wsl_sudo"


def _is_windows_admin_required(elevation: str | ElevationType) -> bool:
    return elevation in (ElevationType.WINDOWS_ADMIN, "windows_admin", True)


def _is_wsl_sudo_required(elevation: str | ElevationType) -> bool:
    return elevation in (ElevationType.WSL_SUDO, "wsl_sudo")


def request_windows_admin(entry: dict, os_name: str) -> bool:
    """
    Gate for entries requiring windows_admin elevation.
    
    Shows the EXACT command and blocks until user approves/denies.
    """
    resolved = resolve_entry(entry, os_name)
    name: str = resolved["name"]
    cmd: str = resolved["install_cmd"]

    console.print()
    console.print(
        Panel(
            f"[bold yellow]This action requires an elevated Windows shell (Run as Administrator).[/bold yellow]\n\n"
            f"Dependency : [bold]{name}[/bold]\n"
            f"Command    : [bold cyan]{cmd}[/bold cyan]\n\n"
            f"[dim]The above command will be run exactly as shown. "
            f"No modifications will be made.[/dim]",
            title="[bold red]Elevation Required: Windows Admin[/bold red]",
            border_style="red",
        )
    )

    approved: bool = Confirm.ask(
        f"  Run this command in an elevated shell to install [bold]{name}[/bold]?",
        default=False,
    )

    if not approved:
        console.print(f"  [yellow]Skipped:[/yellow] {name} (denied by user)\n")

    return approved


def request_wsl_sudo(entry: dict, os_name: str) -> bool:
    """
    Gate for entries requiring wsl_sudo elevation.
    
    Shows the EXACT command. Note: sudo prompt will appear in user's terminal.
    """
    resolved = resolve_entry(entry, os_name)
    name: str = resolved["name"]
    cmd: str = resolved["install_cmd"]

    console.print()
    console.print(
        Panel(
            f"[bold yellow]This action requires sudo inside WSL.[/bold yellow]\n\n"
            f"Dependency : [bold]{name}[/bold]\n"
            f"Command    : [bold cyan]{cmd}[/bold cyan]\n\n"
            f"[dim]The command will run inside WSL. You will be prompted for your "
            f"Linux password in this terminal.[/dim]",
            title="[bold red]Elevation Required: WSL sudo[/bold red]",
            border_style="red",
        )
    )

    approved: bool = Confirm.ask(
        f"  Run this command with sudo in WSL to install [bold]{name}[/bold]?",
        default=False,
    )

    if not approved:
        console.print(f"  [yellow]Skipped:[/yellow] {name} (denied by user)\n")

    return approved


def request_auto(entry: dict, os_name: str) -> bool:
    """
    Soft prompt for entries with elevation: none.
    
    Asks if user wants the dependency installed automatically.
    """
    resolved = resolve_entry(entry, os_name)
    name: str = resolved["name"]
    cmd: str = resolved["install_cmd"]

    console.print()
    console.print(f"  [bold]{name}[/bold] is not installed.")
    console.print(f"  Install command: [dim]{cmd}[/dim]")

    approved: bool = Confirm.ask(
        f"  Install [bold]{name}[/bold] automatically?",
        default=True,
    )

    if not approved:
        console.print(f"  [yellow]Skipped:[/yellow] {name}\n")

    return approved


def check_and_prompt(entry: dict, os_name: str) -> bool:
    """
    Unified entry point: routes to the correct prompt based on
    the manifest entry's requires_elevation field.
    
    Elevation values: "none" | "windows_admin" | "wsl_sudo" (or ElevationType enum)
    
    Returns True if user approved, False if denied or skipped.
    """
    resolved = resolve_entry(entry, os_name)
    elevation_raw = resolved.get("requires_elevation", "none")
    elevation = elevation_raw.lower() if isinstance(elevation_raw, str) else str(elevation_raw).lower()

    if elevation == "windows_admin":
        return request_windows_admin(entry, os_name)
    elif elevation == "wsl_sudo":
        return request_wsl_sudo(entry, os_name)
    else:  # "none" or any other value
        return request_auto(entry, os_name)