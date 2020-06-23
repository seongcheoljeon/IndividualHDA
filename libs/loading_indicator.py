#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.03.05 16:24
# modify date       :
# description       :

import math
from PySide2 import QtWidgets, QtGui, QtCore


class Overlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)
        self.__counter = 0
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, 127 * 0.5)))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        range_num = 5
        for i in range(range_num):
            if (self.counter / (range_num - 1)) % range_num == i:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(127 + (self.counter % (range_num - 1)) * 32, 127, 127)))
            else:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(127 * 0.5, 127 * 0.5, 127 * 0.5)))
            painter.drawEllipse(
                self.width() / 2 + 30 * math.cos(2 * math.pi * i / float(range_num)) - 10,
                self.height() / 2 + 30 * math.sin(2 * math.pi * i / float(range_num)) - 10,
                20, 20)
        painter.end()

    @property
    def counter(self):
        return self.__counter

    @counter.setter
    def counter(self, val):
        self.__counter += val
        
    def showEvent(self, event):
        self.__counter = 0
        

if __name__ == '__main__':
    pass
