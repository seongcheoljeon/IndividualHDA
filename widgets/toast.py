"""Transient, non-modal notifications stacked at the bottom of a widget.

A toast says what just happened and, when the action is reversible, offers
the one thing worth doing about it ("Undo"). It never blocks: it fades after
a few seconds, and at most MAX_VISIBLE are shown; older ones are dropped.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from PySide6 import QtCore, QtGui, QtWidgets
from shiboken6 import isValid

Level = Literal["info", "warning", "error"]

MAX_VISIBLE = 3
TIMEOUT_MS = 4000
TIMEOUT_WITH_ACTION_MS = 8000
_ACCENT: dict[str, str] = {"info": "#4a90d9", "warning": "#d9a43a", "error": "#d9534f"}


class Toast(QtWidgets.QFrame):
    dismissed = QtCore.Signal(object)

    def __init__(
        self,
        message: str,
        *,
        action: str | None,
        on_action: Callable[[], None] | None,
        level: Level,
        parent: QtWidgets.QWidget,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.level = level
        self.setStyleSheet(
            "QFrame#toast {background: rgba(28, 28, 28, 235); border-radius: 6px;"
            f" border-left: 4px solid {_ACCENT[level]};}}"
            " QFrame#toast QLabel {color: #f2f2f2; background: transparent;}"
            " QFrame#toast QToolButton {color: #f2f2f2; background: transparent;"
            " font-weight: bold; padding: 2px 6px;}"
        )
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(8)
        self.message = QtWidgets.QLabel(message, self)
        self.message.setWordWrap(True)
        layout.addWidget(self.message, 1)
        self.action: QtWidgets.QToolButton | None = None
        if action:
            self.action = QtWidgets.QToolButton(self)
            self.action.setText(action)
            self.action.setAutoRaise(True)
            self.action.setCursor(
                QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            )
            self.action.clicked.connect(lambda: self._act(on_action))
            layout.addWidget(self.action)
        self.close_button = QtWidgets.QToolButton(self)
        self.close_button.setText("×")
        self.close_button.setAutoRaise(True)
        self.close_button.clicked.connect(self.dismiss)
        layout.addWidget(self.close_button)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(TIMEOUT_WITH_ACTION_MS if action else TIMEOUT_MS)
        self._timer.timeout.connect(self.dismiss)
        self._timer.start()

    def _act(self, on_action: Callable[[], None] | None) -> None:
        self.dismiss()
        if on_action is not None:
            on_action()

    def dismiss(self) -> None:
        if not isValid(self):
            return
        self._timer.stop()
        self.dismissed.emit(self)


class ToastStack(QtWidgets.QWidget):
    """Owns the visible toasts; hidden (and click-through) when there are none."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._toasts: list[Toast] = []
        self.setVisible(False)

    def toasts(self) -> list[Toast]:
        return list(self._toasts)

    def push(
        self,
        message: str,
        *,
        action: str | None = None,
        on_action: Callable[[], None] | None = None,
        level: Level = "info",
    ) -> Toast:
        toast = Toast(
            message, action=action, on_action=on_action, level=level, parent=self
        )
        toast.dismissed.connect(self._remove)
        self._toasts.append(toast)
        self._layout.addWidget(toast)
        while len(self._toasts) > MAX_VISIBLE:
            self._toasts[0].dismiss()
        self.reposition()
        self.raise_()
        return toast

    def _remove(self, toast: object) -> None:
        if toast in self._toasts and isinstance(toast, Toast):
            self._toasts.remove(toast)
            self._layout.removeWidget(toast)
            toast.setParent(None)
            toast.deleteLater()
        self.reposition()

    def reposition(self, size: QtCore.QSize | None = None) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        area = size or parent.size()
        self.setVisible(bool(self._toasts))
        if not self._toasts:
            return
        width = max(200, min(480, area.width() - 32))
        self.setFixedWidth(width)
        self.adjustSize()
        height = self._layout.sizeHint().height()
        self.setGeometry(
            (area.width() - width) // 2, area.height() - height - 40, width, height
        )
