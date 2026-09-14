"""Web view factory: falls back to a placeholder when QtWebEngine is missing."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6 import QtCore, QtWidgets

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


def make_web_view(
    help_site: str | Callable[[], str] | None, parent: QtWidgets.QWidget | None
) -> QtWidgets.QWidget:
    try:
        from widgets.web_view.web_view import WebView
    except ImportError as error:
        logging.getLogger(__name__).warning("%s (%s)", _MESSAGE, error)
        return UnavailableWebView(parent)
    return WebView(help_site=help_site, parent=parent)
