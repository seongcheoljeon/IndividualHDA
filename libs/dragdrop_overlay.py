from __future__ import annotations

from typing import Any

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.03.05 16:24
# modify date       :
# description       :
from PySide6 import QtCore, QtGui, QtWidgets


class Overlay(QtWidgets.QWidget):
    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.__text = text
        self.__fontsize = 30
        palette = QtGui.QPalette(self.palette())
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtCore.Qt.transparent)
        self.setPalette(palette)

    @property
    def text(self) -> str:
        return self.__text

    @text.setter
    def text(self, val: Any) -> None:
        self.__text = val

    @property
    def fontsize(self) -> int:
        return self.__fontsize

    @fontsize.setter
    def fontsize(self, val: Any) -> None:
        self.__fontsize = val

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(0, 0, 0, 100)))
        painter.setPen(QtCore.Qt.white)
        painter.setFont(QtGui.QFont("Arial", self.fontsize))
        painter.drawText(
            event.rect(), QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter, self.text
        )
        painter.setPen(QtCore.Qt.darkGray)
        painter.setFont(QtGui.QFont("Arial", 13))
        painter.drawText(
            event.rect(), QtCore.Qt.AlignRight | QtCore.Qt.AlignTop, "Individual HDA"
        )
        painter.end()


if __name__ == "__main__":
    pass
