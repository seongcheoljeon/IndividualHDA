# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.05.15 03:43:41
# modified date:    
# description:      

from imp import reload

from PySide2 import QtWidgets, QtGui, QtCore

import public

reload(public)

from widgets.detail_view import detail_view_ui

reload(detail_view_ui)


class DetailView(QtWidgets.QDialog, detail_view_ui.Ui_Dialog__detail_view):
    def __init__(self, parent=None):
        super(DetailView, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.resize(1200, 620)
        self.textBrowser__detail.setFontPointSize(12)
        self.__pixmap_size = 600

    def show_detail_ihda_data(self, data=None, is_histview=None):
        for key, val in sorted(data.iteritems()):
            if key in [public.Key.hda_icon, public.Key.History.icon]:
                continue
            if key in [public.Key.hda_id, public.Key.History.hda_id, public.Key.History.hist_id]:
                continue
            if key in [public.Key.hda_note]:
                continue
            self.textBrowser__detail.append('{0}: {1}'.format(key.replace('_', ' ').upper(), val))
        if is_histview:
            thumbnail_filename = data.get(public.Key.History.thumb_filename)
            thumbnail_filepath = data.get(public.Key.History.thumb_dirpath) / thumbnail_filename
        else:
            thumbnail_filename = data.get(public.Key.thumbnail_filename)
            thumbnail_filepath = data.get(public.Key.thumbnail_dirpath) / thumbnail_filename
        if thumbnail_filepath.exists():
            pixmap = QtGui.QPixmap(thumbnail_filepath.as_posix())
        else:
            pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
        self.label__pixmap.resize(self.__pixmap_size, self.__pixmap_size)
        self.label__pixmap.setPixmap(pixmap.scaled(self.label__pixmap.size(), QtCore.Qt.IgnoreAspectRatio))
        self.show()

    def show_detail_record_data(self, data=None):
        frinfo = data['FRAME INFO'] = '[{0} - {1}], fps: {2}'.format(
            data.get(public.Key.Record.sf), data.get(public.Key.Record.ef), data.get(public.Key.Record.fps))
        for key, val in sorted(data.iteritems()):
            if key in [public.Key.Record.record_id, public.Key.Record.hda_id]:
                continue
            if key in [public.Key.Record.sf, public.Key.Record.ef, public.Key.Record.fps]:
                continue
            self.textBrowser__detail.append('{0}: {1}'.format(key.replace('_', ' ').upper(), val))
        thumbnail_dirpath = data.get(public.Key.Record.thumb_dirpath)
        thumbnail_filename = data.get(public.Key.Record.thumb_filename)
        if (thumbnail_dirpath is None) or (thumbnail_filename is None):
            pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
        else:
            thumbnail_filepath = thumbnail_dirpath / thumbnail_filename
            if thumbnail_filepath.exists():
                pixmap = QtGui.QPixmap(thumbnail_filepath.as_posix())
            else:
                pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
        self.label__pixmap.resize(self.__pixmap_size, self.__pixmap_size)
        self.label__pixmap.setPixmap(pixmap.scaled(self.label__pixmap.size(), QtCore.Qt.IgnoreAspectRatio))
        self.show()
