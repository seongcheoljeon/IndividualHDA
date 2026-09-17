#!/usr/bin/env python
from __future__ import annotations

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:45
# modify date       :
# description       :
from re import compile as re_compile
from typing import Any

from PySide6 import QtCore, QtWidgets


class Object(QtCore.QObject):
    signal_object = QtCore.Signal(object)
    mouse_signal_object = QtCore.Signal(object)


# tree view overwirte class
class InsideView(QtWidgets.QTreeView):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(False)
        self.setDragEnabled(False)
        self.setDropIndicatorShown(True)
        self.setMouseTracking(True)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.NoDragDrop)
        self.setHeaderHidden(False)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
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
