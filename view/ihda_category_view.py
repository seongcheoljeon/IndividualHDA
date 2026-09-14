#!/usr/bin/env python
from __future__ import annotations

from typing import Any
from PySide6 import QtWidgets
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:45
# modify date       :
# description       :

from PySide6 import QtCore


class Object(QtCore.QObject):
    signal_object = QtCore.Signal(object)


# tree view overwirte class
class CategoryView(QtWidgets.QTreeView):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super(CategoryView, self).__init__(parent)
        self.__signal = Object()
        self.setHeaderHidden(False)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAlternatingRowColors(False)
        self.header().setStretchLastSection(True)
        self.resizeColumnToContents(0)

    @property
    def signal(self) -> Any:
        return self.__signal


if __name__ == "__main__":
    pass
