"""
bootstrap/remediate.py

Executes the install_cmd for a manifest dependency.

DESIGN RULE:
  - Only commands from manifest entries may be run here.
  - This module never invents or modifies commands.
  - Always call provisioning_guardian.request_elevation() before calling
    remediate() if the entry has requires_elevation: true.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from bootstrap.checks import resolve_entry


@dataclass
class RemediationResult:
    """Outcome of a single remediation attempt."""

    dependency: str
    success: bool
    raw_output: str
    exit_code: int
    install_cmd: str

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"RemediationResult({self.dependency!r}, {status})"


def _decode_utf16le_if_needed(output: str) -> str:
    """
    Detect and decode UTF-16LE output from Windows WSL commands.
    UTF-16LE has lots of NULL bytes (every other byte).
    """
    if '\x00' in output and output.count('\x00') > len(output) / 3:
        try:
            return output.encode('latin1').decode('utf-16le')
        except Exception:
            pass
    return output


def remediate(entry: dict, os_name: str, timeout: int = 300, use_repair: bool = False, show_output: bool = False) -> RemediationResult:
    """
    Execute the manifest entry's install_cmd or repair_cmd for the given OS.

    Does NOT check requires_elevation — that must be handled by the caller
    via provisioning_guardian.request_elevation() before calling this.

    Args:
        entry:       Raw or resolved manifest entry dict.
        os_name:     OS platform string (e.g. 'windows', 'linux', 'macos').
        timeout:     Max seconds to wait for the install command (default 5 min).
        use_repair:  If True, use repair_cmd instead of install_cmd (for broken installations).
        show_output: If True, stream output to console in real-time.
    """
    resolved = resolve_entry(entry, os_name)
    name: str = resolved["name"]
    
    # Choose between repair_cmd and install_cmd
    if use_repair and "repair_cmd" in resolved:
        cmd: str = resolved["repair_cmd"]
    else:
        cmd: str = resolved["install_cmd"]

    try:
        if show_output:
            # Stream output in real-time
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            if process.stdout:
                for line in process.stdout:
                    print(f"  [dim]{line.rstrip()}[/dim]", flush=True)
                    output_lines.append(line)
            
            process.wait(timeout=timeout)
            combined = ''.join(output_lines)
            exit_code = process.returncode
        else:
            # Capture all output at once (original behavior)
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            combined = (result.stdout + result.stderr).strip()
            exit_code = result.returncode
        
        # Decode UTF-16LE if needed
        combined = _decode_utf16le_if_needed(combined)
        
        return RemediationResult(
            dependency=name,
            success=exit_code == 0,
            raw_output=combined,
            exit_code=exit_code,
            install_cmd=cmd,
        )
    except subprocess.TimeoutExpired:
        return RemediationResult(
            dependency=name,
            success=False,
            raw_output=f"[timeout after {timeout}s]",
            exit_code=-1,
            install_cmd=cmd,
        )
    except Exception as exc:  # noqa: BLE001
        return RemediationResult(
            dependency=name,
            success=False,
            raw_output=f"[exception: {exc}]",
            exit_code=-1,
            install_cmd=cmd,
        )
