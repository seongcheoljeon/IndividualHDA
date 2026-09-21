"""What an item view shows when it has no rows: a title, a hint and one action.

The state sits on the view's viewport and follows its size. Visibility is driven
by the model, so callers only decide *what* to say (set_content), never when.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtWidgets


class EmptyState(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("empty_state")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)
        layout.addStretch(1)
        self.title = QtWidgets.QLabel(self)
        self.title.setObjectName("empty_state_title")
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        font = self.title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.hint = QtWidgets.QLabel(self)
        self.hint.setObjectName("empty_state_hint")
        self.hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: palette(mid);")
        layout.addWidget(self.hint)
        self.action = QtWidgets.QPushButton(self)
        self.action.setObjectName("empty_state_action")
        self.action.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.action.setVisible(False)
        self._on_action: Callable[[], None] | None = None
        self.action.clicked.connect(self._run_action)
        layout.addWidget(self.action, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self._model: QtCore.QAbstractItemModel | None = None
        self.setVisible(False)

    def set_content(
        self,
        title: str,
        hint: str = "",
        action: str | None = None,
        on_action: Callable[[], None] | None = None,
    ) -> None:
        self.title.setText(title)
        self.hint.setText(hint)
        self.hint.setVisible(bool(hint))
        self.action.setText(action or "")
        self.action.setVisible(bool(action))
        self._on_action = on_action if action else None

    def _run_action(self) -> None:
        if self._on_action is not None:
            self._on_action()

    def follow(self, model: QtCore.QAbstractItemModel) -> None:
        """Show whenever ``model`` has no rows."""
        self._model = model
        for signal in (
            model.modelReset,
            model.rowsInserted,
            model.rowsRemoved,
            model.layoutChanged,
        ):
            signal.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        empty = self._model is not None and self._model.rowCount() == 0
        self.setVisible(empty)
        if empty:
            self.raise_()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Resize and isinstance(
            watched, QtWidgets.QWidget
        ):
            self.resize(watched.size())
        return False


def attach_empty_state(view: QtWidgets.QAbstractItemView) -> EmptyState:
    """An EmptyState over ``view``'s viewport that tracks the view's current model."""
    viewport = view.viewport()
    state = EmptyState(viewport)
    state.resize(viewport.size())
    viewport.installEventFilter(state)
    model = view.model()
    if model is not None:
        state.follow(model)
    return state
