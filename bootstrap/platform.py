"""
bootstrap/platform.py

Single source of truth for OS detection across the entire Bootstrap module.

Usage:
    from bootstrap.platform import current_os, OS

    if current_os() == OS.WINDOWS:
        ...
"""

from __future__ import annotations

import os
import sys
from enum import Enum


class OS(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


def current_os() -> OS:
    """
    Detect the OS the Bootstrap Agent is running on.

    Returns one of: OS.WINDOWS, OS.LINUX, OS.MACOS, OS.UNKNOWN.

    Note: On Windows, this returns OS.WINDOWS regardless of whether
    WSL is present. The manifest handles WSL as a *dependency* of
    Windows, not as a separate platform.
    """
    p = sys.platform

    if p == "win32":
        return OS.WINDOWS
    elif p == "darwin":
        return OS.MACOS
    elif p.startswith("linux"):
        return OS.LINUX
    else:
        return OS.UNKNOWN


def current_os_name() -> str:
    """Return the lowercase string name of the current OS (e.g. 'windows')."""
    return current_os().value


def is_admin() -> bool:
    """
    Check if the current process has elevated/admin privileges.

    On Windows: uses ctypes to call IsUserAnAdmin().
    On Linux/macOS: checks if effective UID is 0 (root).
    """
    if sys.platform == "win32":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False


def assert_supported() -> OS:
    """
    Assert that the current OS is one Suryafool supports.
    Raises RuntimeError with a clear message if not.
    """
    os = current_os()
    if os is OS.UNKNOWN:
        raise RuntimeError(
            f"Unsupported platform: {sys.platform!r}. "
            "Suryafool Bootstrap supports Windows, Linux, and macOS."
        )
    return os
