#!/usr/bin/env python
from __future__ import annotations

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:45
# modify date       :
# description       :
from re import compile as re_compile
from sys import stdout
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

import public
from model import ihda_record_model


class Object(QtCore.QObject):
    signal_object = QtCore.Signal(object)
    mouse_signal_object = QtCore.Signal(object)


# tree view overwirte class
class InsideView(QtWidgets.QTreeView):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setHeaderHidden(False)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAlternatingRowColors(False)
        self.header().setStretchLastSection(True)
        self.resizeColumnToContents(0)
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

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(public.Type.mime_type):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if event.mimeData().hasText():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
            mime_dat = [
                x for x in self.__comp_space.split(event.mimeData().text()) if len(x)
            ]
            self.signal.signal_object.emit(mime_dat)
        elif event.mimeData().hasFormat(public.Type.mime_type):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
            self.signal.signal_object.emit(
                [event.mimeData().data(public.Type.mime_type)]
            )
        else:
            super().dropEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if not (event.buttons() & QtCore.Qt.MiddleButton):
            return
        indexes = self.selectionModel().selectedRows(
            public.Value.drag_column_record_view
        )
        if not len(indexes):
            return
        is_all_ihda_type = all(
            [
                x.data(ihda_record_model.RecordModel.record_type_role)
                == public.Type.ihda
                for x in indexes
            ]
        )
        if not is_all_ihda_type:
            return
        drag = QtGui.QDrag(self)
        model_data_lst = list()
        for index in indexes:
            if not index.isValid():
                continue
            model = index.model()
            mime_data = model.mimeData([index])
            model_data = mime_data.data(public.Type.mime_type).data()
            drag.setMimeData(mime_data)
            model_data_lst.append(model_data)
            pixmap = index.data(QtCore.Qt.DecorationRole)
            if pixmap is not None:
                drag.setHotSpot(
                    QtCore.QPoint(pixmap.width() // 3, pixmap.height() // 3)
                )
                drag.setPixmap(pixmap)
        drop_action = drag.exec(QtCore.Qt.CopyAction)
        self.signal.mouse_signal_object.emit([drop_action, model_data_lst])
        stdout.flush()
        super().mouseMoveEvent(event)
