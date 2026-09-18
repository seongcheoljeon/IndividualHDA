from __future__ import annotations

from typing import Any

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.03.05 16:24
# modify date       :
# description       :
from PySide6 import QtCore, QtGui, QtWidgets

from libs.qt_helpers import sized_font


class Overlay(QtWidgets.QWidget):
    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.__text = text
        self.__fontsize = 30
        palette = QtGui.QPalette(self.palette())
        palette.setColor(
            QtGui.QPalette.ColorRole.Window, QtCore.Qt.GlobalColor.transparent
        )
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
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(0, 0, 0, 100)))
        painter.setPen(QtCore.Qt.GlobalColor.white)
        painter.setFont(sized_font(self.font(), self.fontsize))
        painter.drawText(
            event.rect(),
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignCenter,
            self.text,
        )
        painter.setPen(QtCore.Qt.GlobalColor.darkGray)
        painter.setFont(sized_font(self.font(), 13))
        painter.drawText(
            event.rect(),
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop,
            "Individual HDA",
        )
        painter.end()


if __name__ == "__main__":
    pass
