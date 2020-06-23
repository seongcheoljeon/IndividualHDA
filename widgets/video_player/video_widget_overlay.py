# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : seongcheolzeon@gmail.com
# project name      : libs/loading_indicator
# create date       : 2020.03.05 16:24
# modify date       :
# description       :

from PySide2 import QtWidgets, QtGui, QtCore


class Overlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)
        self.__parent = parent
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)
        
    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, 20)))
        painter.setPen(QtCore.Qt.darkGray)
        painter.setFont(QtGui.QFont('Arial', 33))
        painter.drawText(event.rect(), QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter, 'iHDA Video Player')
        painter.setPen(QtCore.Qt.darkGray)
        painter.setFont(QtGui.QFont('Arial', 13))
        painter.drawText(event.rect(), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, 'Individual HDA')
        painter.end()


if __name__ == '__main__':
    pass
