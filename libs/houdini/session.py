"""Houdini session facts: windows, deferred execution, version and licence, frames.

Only libs.houdini_api and this package import hou.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable
from contextlib import nullcontext, suppress
from typing import Any

from libs.host import IS_HOUDINI

with suppress(ImportError):
    import hou

try:
    import hdefereval
except ImportError:  # not hosted by Houdini
    hdefereval = None

# Undo group label shared by the import paths in nodes and assets.
UNDO_NAME_IMPORT_IHDA = "import_individual_hda"


def main_window() -> Any | None:
    return hou.qt.mainWindow() if IS_HOUDINI else None


def help_server_url() -> Callable[[], str] | None:
    return hou.helpServerUrl if IS_HOUDINI else None


def qt_library_dirpath() -> pathlib.Path | None:
    """$HFS/bin -- where Houdini keeps the Qt DLLs its helper binaries need."""
    return pathlib.Path(hou.expandString("$HFS"), "bin") if IS_HOUDINI else None


def host_stylesheet() -> str:
    return str(hou.qt.styleSheet()) if IS_HOUDINI else ""


def host_icon(name: str, size: int = 128) -> Any | None:
    """QPixmap of a Houdini icon, or None when unavailable."""
    if not IS_HOUDINI:
        return None
    try:
        return hou.qt.Icon(name).pixmap(size, size)
    except (RuntimeError, hou.Error):
        return None


def scaled_size(value: int) -> int:
    return int(hou.ui.scaledSize(int(value))) if IS_HOUDINI else int(value)


def global_scale_factor() -> float:
    return float(hou.ui.globalScaleFactor()) if IS_HOUDINI else 1.0


def undo_group(name: str) -> Any:
    return hou.undos.group(name) if IS_HOUDINI else nullcontext()


def execute_deferred(func: Callable[[], object]) -> None:
    """Run on the Houdini main loop later; immediately when not hosted."""
    if hdefereval is not None:
        hdefereval.executeDeferred(func)
    else:
        func()


def add_event_loop_callback(func: Callable[..., Any]) -> None:
    if IS_HOUDINI and func not in hou.ui.eventLoopCallbacks():
        hou.ui.addEventLoopCallback(func)


def remove_event_loop_callback(func: Callable[..., Any]) -> None:
    if IS_HOUDINI and func in hou.ui.eventLoopCallbacks():
        hou.ui.removeEventLoopCallback(func)


def has_event_loop_callback(func: Callable[..., Any]) -> bool:
    return bool(IS_HOUDINI and func in hou.ui.eventLoopCallbacks())


def current_hipfile() -> pathlib.Path:
    return pathlib.Path(hou.hipFile.path())


def current_houdini_version() -> str:
    return hou.applicationVersionString()


def current_houdini_license() -> str:
    if IS_HOUDINI:
        return hou.licenseCategory().name()
    return "unknown"


def commercial_license() -> str:
    return hou.licenseCategoryType.Commercial.name()


def is_houdini_commercial_license() -> bool:
    return commercial_license() == current_houdini_license()


def frame_info() -> list[float]:
    sf, ef = map(int, hou.playbar.playbackRange())
    fps = hou.fps()
    return [sf, ef, fps]


def _set_frame_range_for_scene(
    sf: float = 1001, ef: float = 1240, fps: float = 24
) -> None:
    hou.playbar.setFrameRange(sf, ef)
    hou.playbar.setPlaybackRange(sf, ef)
    hou.setFrame(int(sf))


def vector2(x: float, y: float) -> Any:
    return hou.Vector2((x, y))
