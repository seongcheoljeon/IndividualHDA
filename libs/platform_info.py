"""Which OS is this? Names match platform.system().lower()."""

from __future__ import annotations

from platform import system as _system

WINDOWS, LINUX, MAC = "windows", "linux", "darwin"


def platform_system() -> str:
    return _system()


def is_windows() -> bool:
    return _system().lower() == WINDOWS


def is_linux() -> bool:
    return _system().lower() == LINUX


def is_mac() -> bool:
    return _system().lower() == MAC
