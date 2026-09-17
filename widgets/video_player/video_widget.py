from __future__ import annotations

from typing import Any

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.20 00:49:52
# modified date:
# description:
from PySide6 import QtCore, QtGui, QtMultimediaWidgets, QtWidgets

from widgets.video_player import video_widget_overlay


class VideoWidget(QtMultimediaWidgets.QVideoWidget):
    play_toggle_requested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored
        )
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtCore.Qt.GlobalColor.black)
        self.setPalette(palette)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self.__overlay = video_widget_overlay.Overlay(self)
        self.__overlay.show()

    @property
    def overlay(self) -> Any:
        return self.__overlay

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key.Key_Escape and self.isFullScreen():
            self.setFullScreen(False)
            event.accept()
        elif event.key() in [QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter]:
            self.setFullScreen(not self.isFullScreen())
            event.accept()
        elif event.key() == QtCore.Qt.Key.Key_Space:
            self.play_toggle_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.setFullScreen(not self.isFullScreen())
        event.accept()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.__overlay.resize(event.size())
        super().resizeEvent(event)


if __name__ == "__main__":
    pass
