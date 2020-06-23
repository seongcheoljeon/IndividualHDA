# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:40
# modify date       :
# description       :

from re import compile as re_compile
from imp import reload
from sys import stdout

from PySide2 import QtWidgets, QtCore, QtGui

import public

reload(public)


class Object(QtCore.QObject):
    signal_object = QtCore.Signal(object)
    mouse_signal_object = QtCore.Signal(object)


# history table view overwrite class
class HistoryView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super(HistoryView, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAlternatingRowColors(False)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setWordWrap(True)
        self.verticalHeader().setDefaultSectionSize(46)
        #
        self.__signal = Object()
        self.__comp_space = re_compile(r'\s')
        #
        self.entered.connect(self.on_entered)

    @property
    def signal(self):
        return self.__signal

    def on_entered(self, index):
        if index.isValid():
            self.setCurrentIndex(index)
            # self.edit(index, self.AllEditTriggers, None)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(public.Type.mime_type):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super(HistoryView, self).dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasText():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
            mime_dat = filter(lambda x: len(x), self.__comp_space.split(event.mimeData().data('text/plain')))
            self.signal.signal_object.emit(mime_dat)
        elif event.mimeData().hasFormat(public.Type.mime_type):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
            self.signal.signal_object.emit([event.mimeData().data(public.Type.mime_type)])
        else:
            super(HistoryView, self).dropEvent(event)
        stdout.flush()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.MiddleButton):
            return
        indexes = self.selectionModel().selectedRows(public.Value.drag_column_history_view)
        if not len(indexes):
            return
        drag = QtGui.QDrag(self)
        model_data_lst = list()
        for index in indexes:
            if not index.isValid():
                continue
            model = index.model()
            mime_data = model.mimeData([index])
            model_data = mime_data.data(public.Type.mime_type).data()
            drag.setMimeData(mime_data)
            model_data_lst.append(model_data)
            pixmap = index.data(QtCore.Qt.DecorationRole)
            if pixmap is not None:
                drag.setHotSpot(QtCore.QPoint(pixmap.width() / 3, pixmap.height() / 3))
                drag.setPixmap(pixmap)
        drop_action = drag.exec_(QtCore.Qt.CopyAction)
        self.signal.mouse_signal_object.emit([drop_action, model_data_lst])
        stdout.flush()
        super(HistoryView, self).mouseMoveEvent(event)

