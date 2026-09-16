"""Code-built DetailView layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QCoreApplication,
    Qt,
)
from PySide6.QtGui import (
    QIcon,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)

from widgets.layout_helpers import make_font

from . import detail_view_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Dialog__detail_view", text)


class DetailViewLayout:
    def build_ui(self, window: QDialog) -> None:
        self._configure_window(window)
        self._build_content(window)

    def _configure_window(self, window: QDialog) -> None:
        if not window.objectName():
            window.setObjectName("Dialog__detail_view")
        window.resize(869, 524)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/detail_view_main/icons/viewport_logo_trans.png"))
        window.setWindowTitle(_translate("iHDA Detail View"))

    def _build_content(self, window: QDialog) -> None:
        self.verticalLayout__detail_dialog = QVBoxLayout(window)
        self.verticalLayout__detail_dialog.setSpacing(1)
        self.verticalLayout__detail_dialog.setObjectName(
            "verticalLayout__detail_dialog"
        )
        self.verticalLayout__detail_dialog.setContentsMargins(1, 1, 1, 1)
        self.horizontalLayout__detail_content = QHBoxLayout()
        self.horizontalLayout__detail_content.setSpacing(3)
        self.horizontalLayout__detail_content.setObjectName(
            "horizontalLayout__detail_content"
        )
        self.verticalLayout__preview = QVBoxLayout()
        self.verticalLayout__preview.setSpacing(3)
        self.verticalLayout__preview.setObjectName("verticalLayout__preview")
        self.label__pixmap = QLabel(window)
        self.label__pixmap.setObjectName("label__pixmap")
        self.label__pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__pixmap.setText("")
        self.verticalLayout__preview.addWidget(self.label__pixmap)
        self.horizontalLayout__detail_content.addLayout(self.verticalLayout__preview)
        self.textBrowser__detail = QTextBrowser(window)
        self.textBrowser__detail.setObjectName("textBrowser__detail")
        self.textBrowser__detail.setTabStopDistance(40.0)
        self.horizontalLayout__detail_content.addWidget(self.textBrowser__detail)
        self.verticalLayout__detail_dialog.addLayout(
            self.horizontalLayout__detail_content
        )
