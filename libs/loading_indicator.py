#!/usr/bin/env python
from __future__ import annotations

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.03.05 16:24
# modify date       :
# description       :
import math
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets


class Overlay(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.__counter = 0
        palette = QtGui.QPalette(self.palette())
        palette.setColor(
            QtGui.QPalette.ColorRole.Window, QtCore.Qt.GlobalColor.transparent
        )
        self.setPalette(palette)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(
            event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, int(127 * 0.5)))
        )
        painter.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
        range_num = 5
        for i in range(range_num):
            if (self.counter / (range_num - 1)) % range_num == i:
                painter.setBrush(
                    QtGui.QBrush(
                        QtGui.QColor(
                            127 + (self.counter % (range_num - 1)) * 32, 127, 127
                        )
                    )
                )
            else:
                painter.setBrush(
                    QtGui.QBrush(
                        QtGui.QColor(int(127 * 0.5), int(127 * 0.5), int(127 * 0.5))
                    )
                )
            painter.drawEllipse(
                QtCore.QRectF(
                    self.width() / 2
                    + 30 * math.cos(2 * math.pi * i / float(range_num))
                    - 10,
                    self.height() / 2
                    + 30 * math.sin(2 * math.pi * i / float(range_num))
                    - 10,
                    20,
                    20,
                )
            )
        painter.end()

    @property
    def counter(self) -> int:
        return self.__counter

    @counter.setter
    def counter(self, val: Any) -> None:
        self.__counter += val

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self.__counter = 0


if __name__ == "__main__":
    pass
