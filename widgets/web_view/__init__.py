"""Web view factory: falls back to a placeholder when QtWebEngine is missing."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from PySide6 import QtCore, QtWidgets

from libs.houdini_api import HoudiniAPI

_MESSAGE = (
    "Help browser unavailable: PySide6.QtWebEngine is missing in this Houdini build"
)


class UnavailableWebView(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        label = QtWidgets.QLabel(_MESSAGE, self)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label)


def _allow_render_process_to_start() -> None:
    """Let Chromium's helper process resolve Houdini's Qt DLLs.

    Houdini keeps QtWebEngineProcess.exe in $HFS/qt/bin but every Qt DLL in
    $HFS/bin. Windows resolves a child process's imports from its own directory,
    the system directories and PATH -- never from the parent's directory -- so the
    helper dies with STATUS_DLL_NOT_FOUND (0xC0000135) and *every* navigation
    fails with loadFinished(False), which is indistinguishable from an
    unreachable site. Houdini does not put $HFS/bin on PATH, so the panel does.

    Appended, not prepended: PATH is consulted after the system directories, which
    ship no Qt, while prepending would let Houdini's bundled avcodec/avformat
    shadow the libraries of unrelated child processes such as FFmpeg.
    """
    if os.name != "nt":
        return
    directory = HoudiniAPI.qt_library_dirpath()
    if directory is None:
        return
    search_path = path_with_qt_libraries(str(directory), os.environ.get("PATH", ""))
    if search_path is not None:
        os.environ["PATH"] = search_path


def path_with_qt_libraries(directory: str, search_path: str) -> str | None:
    """The PATH to set, or None when the directory is already searched."""
    if any(
        os.path.normcase(entry) == os.path.normcase(directory)
        for entry in search_path.split(os.pathsep)
    ):
        return None
    return search_path + os.pathsep + directory if search_path else directory


def make_web_view(
    help_site: str | Callable[[], str] | None, parent: QtWidgets.QWidget | None
) -> QtWidgets.QWidget:
    _allow_render_process_to_start()
    try:
        from widgets.web_view.web_view import WebView
    except ImportError as error:
        logging.getLogger(__name__).warning("%s (%s)", _MESSAGE, error)
        return UnavailableWebView(parent)
    return WebView(help_site=help_site, parent=parent)
