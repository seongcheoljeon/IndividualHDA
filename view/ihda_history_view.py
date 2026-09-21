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


# history table view overwrite class
class HistoryView(AssetDragMixin, QtWidgets.QTableView):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.setAlternatingRowColors(False)
        self.setMouseTracking(True)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setWordWrap(True)
        self.verticalHeader().setDefaultSectionSize(46)
        #
        self.__signal = Object()
        self.__comp_space = re_compile(r"\s")
        #
        self.entered.connect(self.on_entered)

    @property
    def signal(self) -> Any:
        return self.__signal

    def on_entered(self, index: QtCore.QModelIndex) -> None:
        if index.isValid():
            self.setCurrentIndex(index)
            # self.edit(index, self.AllEditTriggers, None)

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
            self.selectionModel().selectedRows(keys.Value.drag_column_history_view)
        )
