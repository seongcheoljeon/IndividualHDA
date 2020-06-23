# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.20 00:49:52
# modified date:    
# description:      

from imp import reload
from PySide2 import QtWidgets, QtGui, QtCore, QtMultimediaWidgets

import public
from widgets.video_player import video_widget_overlay

reload(public)
reload(video_widget_overlay)


class VideoWidget(QtMultimediaWidgets.QVideoWidget):
    def __init__(self, parent=None):
        super(VideoWidget, self).__init__(parent)
        self.__parent = parent
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtCore.Qt.black)
        self.setPalette(palette)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

        self.__overlay = video_widget_overlay.Overlay(self)
        self.__overlay.show()

    @property
    def overlay(self):
        return self.__overlay

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape and self.isFullScreen():
            self.setFullScreen(False)
            event.accept()
        elif event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            self.setFullScreen(not self.isFullScreen())
            event.accept()
        elif event.key() == QtCore.Qt.Key_Space:
            self.__parent.slot_play_toggle()
            event.accept()
        else:
            super(VideoWidget, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.setFullScreen(not self.isFullScreen())
        event.accept()

    def resizeEvent(self, event):
        self.__overlay.resize(event.size())
        super(VideoWidget, self).resizeEvent(event)


if __name__ == '__main__':
    pass
