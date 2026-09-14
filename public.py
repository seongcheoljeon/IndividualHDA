"""Compatibility facade over libs.keys / libs.paths / libs.platform_info / libs.host.

Existing modules import `public`; new code imports the real homes directly. The
architecture test keeps the list of `public` importers from growing.
"""

from __future__ import annotations

from libs.host import IS_HOUDINI
from libs.keys import Extensions, InvalidNode, Key, Name, Type, UISetting, Value
from libs.paths import Paths, SQLite, hda_base_dirpath
from libs.platform_info import is_linux, is_mac, is_windows, platform_system

__all__ = [
    "IS_HOUDINI",
    "Extensions",
    "InvalidNode",
    "Key",
    "Name",
    "Paths",
    "SQLite",
    "Type",
    "UISetting",
    "Value",
    "hda_base_dirpath",
    "is_linux",
    "is_mac",
    "is_windows",
    "platform_system",
]
