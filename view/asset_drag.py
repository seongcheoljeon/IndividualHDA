"""Left- or middle-button drag of asset rows out of an item view.

One implementation for the list, table and history views. The payload is the
model's mime data; whoever receives ``mouse_signal_object`` (the Houdini import
or the team download) decides what to do with the drop result.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs import keys

if TYPE_CHECKING:
    _Base = QtWidgets.QAbstractItemView
else:
    _Base = object

_DRAG_BUTTONS = QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.MiddleButton


def payloads(indexes: Sequence[QtCore.QModelIndex]) -> list[bytes]:
    """The asset payload of each valid index, as the drag and the import expect it."""
    result: list[bytes] = []
    for index in indexes:
        if index.isValid():
            mime_data = index.model().mimeData([index])
            result.append(bytes(mime_data.data(keys.Type.mime_type).data()))
    return result


class AssetDragMixin(_Base):
    signal: Any
    _drag_origin: QtCore.QPoint | None = None

    def drag_indexes(self) -> list[QtCore.QModelIndex]:
        """Rows the drag carries; table-like views narrow this to one column."""
        return list(self.selectedIndexes())

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        pos = event.position().toPoint()
        pressed_item = (
            bool(event.button() & _DRAG_BUTTONS) and self.indexAt(pos).isValid()
        )
        self._drag_origin = pos if pressed_item else None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        origin = self._drag_origin
        if (
            origin is None
            or not (event.buttons() & _DRAG_BUTTONS)
            or (event.position().toPoint() - origin).manhattanLength()
            < QtWidgets.QApplication.startDragDistance()
        ):
            super().mouseMoveEvent(event)
            return
        self._drag_origin = None
        indexes = [index for index in self.drag_indexes() if index.isValid()]
        if not indexes:
            return
        drag = QtGui.QDrag(self)
        model_data_lst: list[bytes] = []
        for index in indexes:
            mime_data = index.model().mimeData([index])
            drag.setMimeData(mime_data)
            model_data_lst.append(bytes(mime_data.data(keys.Type.mime_type).data()))
            pixmap = index.data(QtCore.Qt.ItemDataRole.DecorationRole)
            if isinstance(pixmap, QtGui.QPixmap) and not pixmap.isNull():
                drag.setHotSpot(
                    QtCore.QPoint(pixmap.width() // 3, pixmap.height() // 3)
                )
                drag.setPixmap(pixmap)
        drop_action = drag.exec(QtCore.Qt.DropAction.CopyAction)
        self.signal.mouse_signal_object.emit([drop_action, model_data_lst])

    def startDrag(self, supported_actions: Any) -> None:
        """The base-class drag never runs: this mixin owns dragging."""
