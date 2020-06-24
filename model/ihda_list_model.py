#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:34
# modify date       :
# description       :

from imp import reload

from PySide2 import QtGui, QtCore

try:
    import hou
except ImportError as err:
    pass

import public

reload(public)


class ListModel(QtCore.QAbstractListModel):
    data_role = QtCore.Qt.UserRole
    row_role = QtCore.Qt.UserRole + 1
    id_role = QtCore.Qt.UserRole + 2
    filepath_role = QtCore.Qt.UserRole + 3
    name_role = QtCore.Qt.UserRole + 4
    cate_role = QtCore.Qt.UserRole + 5
    version_role = QtCore.Qt.UserRole + 6
    favorite_role = QtCore.Qt.UserRole + 7
    tag_role = QtCore.Qt.UserRole + 8
    type_role = QtCore.Qt.UserRole + 9

    def __init__(self, items=None, pixmap_ihda_data=None, pixmap_thumb_data=None, font_size=None,
                 font_style=None, icon_size=None, thumb_size=None, padding=None, parent=None):
        super(ListModel, self).__init__(parent)
        self.__items = items
        self.__pixmap_ihda_data = pixmap_ihda_data
        self.__pixmap_thumb_data = pixmap_thumb_data
        self.__font_size = font_size
        self.__font_style = font_style
        self.__icon_size = icon_size
        self.__thumb_size = thumb_size
        self.__padding = padding
        self.__show_thumbnail = False

    @property
    def show_thumbnail(self):
        return self.__show_thumbnail

    @show_thumbnail.setter
    def show_thumbnail(self, val):
        self.__show_thumbnail = val

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__items) if self.__items is not None else 0

    def flags(self, index):
        flags = super(ListModel, self).flags(index)
        if index.isValid():
            hda_filepath = index.data(ListModel.filepath_role)
            if not hda_filepath.exists():
                flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                # flags = QtCore.Qt.ItemIsSelectable
            else:
                flags |= QtCore.Qt.ItemIsSelectable
                flags |= QtCore.Qt.ItemIsEnabled
                flags |= QtCore.Qt.ItemIsDragEnabled
                flags |= QtCore.Qt.ItemIsDropEnabled
                # flags |= QtCore.Qt.ItemIsEditable
                flags |= QtCore.Qt.ItemIsTristate
        else:
            flags |= QtCore.Qt.ItemIsSelectable
            flags |= QtCore.Qt.ItemIsEnabled
            flags |= QtCore.Qt.ItemIsDropEnabled
        return flags

    def mimeTypes(self):
        return [public.Type.mime_type]

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        if not len(indexes):
            return False
        mime_data = super(ListModel, self).mimeData(indexes)
        for index in indexes:
            if index.isValid():
                data = str(self.data(index, role=ListModel.data_role))
                mime_data.setData(public.Type.mime_type, QtCore.QByteArray(data))
        return mime_data

    def dropMimeData(self, mime_data, action, row, column, parent):
        return True

    def set_row_col_in_item(self, row):
        self.__items[row][public.Key.item_row] = row

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if (index is None) or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        self.set_row_col_in_item(row)
        index_dat = self.__items[row]
        hda_name = index_dat.get(public.Key.hda_name)
        if role == QtCore.Qt.DisplayRole:
            return hda_name
        # elif role == QtCore.Qt.EditRole:
        #     return hda_name
        elif role == QtCore.Qt.DecorationRole:
            hda_id = index_dat.get(public.Key.hda_id)
            if self.show_thumbnail:
                thumb_pixmap = self.__pixmap_thumb_data.get(hda_id)
                if thumb_pixmap is None:
                    return QtGui.QPixmap(':/main/icons/no_img_available.png')
                if thumb_pixmap.isNull():
                    thumb_filename = index_dat.get(public.Key.thumbnail_filename)
                    thumb_filepath = index_dat.get(public.Key.thumbnail_dirpath) / thumb_filename
                    if (thumb_filepath is None) or (not thumb_filepath.exists()):
                        thumb_pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
                    else:
                        thumb_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
                        self.__pixmap_thumb_data.update({hda_id: thumb_pixmap})
                return thumb_pixmap.scaled(
                    QtCore.QSize(self.__thumb_size, self.__thumb_size), QtCore.Qt.KeepAspectRatio)
            else:
                icon_pixmap = self.__pixmap_ihda_data.get(hda_id)
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(self.__icon_size, self.__icon_size), QtCore.Qt.KeepAspectRatio)
        elif role == QtCore.Qt.TextAlignmentRole:
            return int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        elif role == QtCore.Qt.ToolTipRole:
            hda_ver = index_dat.get(public.Key.hda_version)
            if hda_ver is not None:
                return '{0} (v{1})'.format(hda_name, hda_ver)
            return hda_name
        elif role == QtCore.Qt.StatusTipRole:
            return None
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            hda_filepath = index_dat.get(public.Key.hda_dirpath) / index_dat.get(public.Key.hda_filename)
            if not hda_filepath.exists():
                font.setItalic(True)
                font.setStrikeOut(True)
            return font
        elif role == QtCore.Qt.SizeHintRole:
            if self.show_thumbnail:
                return QtCore.QSize(
                    self.__thumb_size + self.__font_size + self.__padding,
                    self.__thumb_size + self.__font_size + self.__padding)
            return QtCore.QSize(
                self.__icon_size + self.__font_size + self.__padding,
                self.__icon_size + self.__font_size + self.__padding)
        elif role == ListModel.data_role:
            return index_dat
        elif role == ListModel.row_role:
            return row
        elif role == ListModel.id_role:
            return index_dat.get(public.Key.hda_id)
        elif role == ListModel.filepath_role:
            return index_dat.get(public.Key.hda_dirpath) / index_dat.get(public.Key.hda_filename)
        elif role == ListModel.name_role:
            return hda_name
        elif role == ListModel.cate_role:
            return index_dat.get(public.Key.hda_cate)
        elif role == ListModel.version_role:
            return index_dat.get(public.Key.hda_version)
        elif role == ListModel.favorite_role:
            return index_dat.get(public.Key.is_favorite_hda)
        elif role == ListModel.tag_role:
            return index_dat.get(public.Key.hda_tags)
        elif role == ListModel.type_role:
            return index_dat.get(public.Key.node_type_name)

    # def setData(self, index, value, role=QtCore.Qt.EditRole):
    #     if not index.isValid() or not (0 <= index.row() < len(self.__items)) or not value or (not len(value)):
    #         return False
    #     if role == QtCore.Qt.EditRole:
    #         row = index.row()
    #         value = str(value.strip()).replace(' ', '_')
    #         index_data = self.__items[row]
    #         hda_name = index_data.get(public.Key.hda_name)
    #         if (hda_name == value) or (not len(value)):
    #             return False
    #         self.__items[row][public.Key.hda_name] = value
    #         self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
    #         return True
    #     return False

    def set_icon_size(self, icon_size=None, thumb_size=None):
        self.beginResetModel()
        self.__icon_size = icon_size
        self.__thumb_size = thumb_size
        self.endResetModel()

    def set_font(self, style=None, size=None):
        self.beginResetModel()
        self.__font_style = style.decode('utf8')
        self.__font_size = size
        self.endResetModel()

    def set_padding(self, val):
        self.beginResetModel()
        self.__padding = val
        self.endResetModel()

    def add_items(self, data=()):
        if (data is None) or (not len(data)):
            return
        index = QtCore.QModelIndex()
        self.beginInsertRows(index, 0, 0)
        self.__items = data
        self.endInsertRows()

    def append_item(self, item):
        index = len(self.__items)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self.__items.append(item)
        self.endInsertRows()

    def remove_item(self, row=None):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.endRemoveRows()

    def clear_item(self):
        self.beginRemoveRows(QtCore.QModelIndex(), 0, len(self.__items))
        self.__items = list()
        self.endRemoveRows()
