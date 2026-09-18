from __future__ import annotations

# author            : SeongCheol Jeon
# email addr        : seongcheolzeon@gmail.com
# project name      : libs/loading_indicator
# create date       : 2020.03.05 16:24
# modify date       :
# description       :
from PySide6 import QtCore, QtGui, QtWidgets

from libs.qt_helpers import sized_font


class Overlay(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.__parent = parent
        palette = QtGui.QPalette(self.palette())
        palette.setColor(
            QtGui.QPalette.ColorRole.Window, QtCore.Qt.GlobalColor.transparent
        )
        self.setPalette(palette)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, 20)))
        painter.setPen(QtCore.Qt.GlobalColor.darkGray)
        painter.setFont(sized_font(self.font(), 33))
        painter.drawText(
            event.rect(),
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignCenter,
            "iHDA Video Player",
        )
        painter.setPen(QtCore.Qt.GlobalColor.darkGray)
        painter.setFont(sized_font(self.font(), 13))
        painter.drawText(
            event.rect(),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop,
            "Individual HDA",
        )
        painter.end()


if __name__ == "__main__":
    pass
