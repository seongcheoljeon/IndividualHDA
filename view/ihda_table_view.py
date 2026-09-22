from __future__ import annotations

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:40
# modify date       :
# description       :
from re import compile as re_compile
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs import keys
from view.asset_drag import AssetDragMixin


class Object(QtCore.QObject):
    signal_object = QtCore.Signal(object)
    mouse_signal_object = QtCore.Signal(object)


# table view overwrite class
class TableView(AssetDragMixin, QtWidgets.QTableView):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.setMouseTracking(True)  # hover styling only; selection needs a click
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        # Modern table chrome: no grid or row numbers, banded rows, a quiet header.
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().hide()
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.horizontalHeader().setMinimumSectionSize(36)
        self.verticalHeader().setDefaultSectionSize(50)
        #
        self.__signal = Object()
        self.__comp_space = re_compile(r"\s")
        #

    @property
    def signal(self) -> Any:
        return self.__signal

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(keys.Type.mime_type):
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if event.mimeData().hasText():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.acceptProposedAction()
            mime_dat = [
                x for x in self.__comp_space.split(event.mimeData().text()) if len(x)
            ]
            self.signal.signal_object.emit(mime_dat)
        elif event.mimeData().hasFormat(keys.Type.mime_type):
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.acceptProposedAction()
            self.signal.signal_object.emit([event.mimeData().data(keys.Type.mime_type)])
        else:
            super().dropEvent(event)

    def drag_indexes(self) -> list[QtCore.QModelIndex]:
        return list(
            self.selectionModel().selectedRows(keys.Value.drag_column_table_view)
        )
