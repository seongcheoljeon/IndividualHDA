#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 11:45
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


class TableModel(QtCore.QAbstractTableModel):
    data_role = QtCore.Qt.UserRole
    row_role = QtCore.Qt.UserRole + 1
    col_role = QtCore.Qt.UserRole + 2
    id_role = QtCore.Qt.UserRole + 3
    filepath_role = QtCore.Qt.UserRole + 4
    name_role = QtCore.Qt.UserRole + 5
    cate_role = QtCore.Qt.UserRole + 6
    version_role = QtCore.Qt.UserRole + 7
    favorite_role = QtCore.Qt.UserRole + 8
    tag_role = QtCore.Qt.UserRole + 9
    type_role = QtCore.Qt.UserRole + 10

    def __init__(self, items=None, pixmap_ihda_data=None, pixmap_thumb_data=None,
                 font_size=None, font_style=None, icon_size=None, thumb_size=None, parent=None):
        super(TableModel, self).__init__(parent)
        self.__items = items
        self.__pixmap_ihda_data = pixmap_ihda_data
        self.__pixmap_thumb_data = pixmap_thumb_data
        self.__show_thumbnail = False
        self.__headers = [
            'Name', 'Definition', 'Like', 'Version', 'Count', 'Created Date', 'Modified Date',
            'Houdini', 'License']
        self.__keys = [
            public.Key.hda_name, public.Key.node_def_desc, public.Key.is_favorite_hda, public.Key.hda_version,
            public.Key.hda_load_count, public.Key.hda_ctime, public.Key.hda_mtime, public.Key.hou_version,
            public.Key.hda_license]
        assert len(self.__headers) == len(self.__keys)
        # hda name 컬럼 인덱스
        self.__hda_name_column = 0
        # hda def 컬럼 인덱스
        self.__hda_def_column = 1
        # hda 즐겨찾기 컬럼 인덱스
        self.__hda_favorite_column = 2
        # hda time 컬럼 인덱스
        self.__hda_datetime_column = [5, 6]
        # hda houdini version 컬럼 인덱스
        self.__hda_hou_ver_column = 7
        #
        self.__font_size = font_size
        self.__font_style = font_style
        self.__icon_size = icon_size
        self.__thumb_size = thumb_size

    @property
    def show_thumbnail(self):
        return self.__show_thumbnail

    @show_thumbnail.setter
    def show_thumbnail(self, val):
        self.__show_thumbnail = val

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return '{0}'.format(self.__headers[section])
            else:
                return 'iHDA {0}'.format(section + 1)
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setPointSize(public.UISetting.view_font_size)
            return font
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__items) if self.__items is not None else 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.__headers)
        # return len(self.__headers) if self.rowCount() else 0

    def set_row_col_in_item(self, row):
        self.__items[row][public.Key.item_row] = row

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        column = index.column()
        self.set_row_col_in_item(row)
        data = self.__items[row]
        if role == QtCore.Qt.DisplayRole:
            if column == self.__hda_favorite_column:
                return None
            return data.get(self.__keys[column])
        # elif role == QtCore.Qt.EditRole:
        #     return val
        elif role == QtCore.Qt.DecorationRole:
            other_icon_size = self.__icon_size * 0.7
            node_icon_column = self.__hda_name_column if not self.show_thumbnail else self.__hda_def_column
            hda_id = data.get(public.Key.hda_id)
            if self.show_thumbnail:
                if column == self.__hda_name_column:
                    thumb_pixmap = self.__pixmap_thumb_data.get(hda_id)
                    if thumb_pixmap is None:
                        return QtGui.QPixmap(':/main/icons/no_img_available.png')
                    if thumb_pixmap.isNull():
                        thumb_filename = data.get(public.Key.thumbnail_filename)
                        thumb_filepath = data.get(public.Key.thumbnail_dirpath) / thumb_filename
                        if (thumb_filepath is None) or (not thumb_filepath.exists()):
                            thumb_pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
                        else:
                            thumb_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
                            self.__pixmap_thumb_data.update({hda_id: thumb_pixmap})
                    return thumb_pixmap.scaled(
                        QtCore.QSize(self.__thumb_size, self.__thumb_size), QtCore.Qt.KeepAspectRatio)
            if column == node_icon_column:
                icon_pixmap = self.__pixmap_ihda_data.get(hda_id)
                if icon_pixmap is None:
                    return None
                if node_icon_column == 0:
                    return icon_pixmap.scaled(
                        QtCore.QSize(self.__icon_size, self.__icon_size), QtCore.Qt.KeepAspectRatio)
                elif node_icon_column == 1:
                    return icon_pixmap.scaled(
                        QtCore.QSize(self.__icon_size * 0.8, self.__icon_size * 0.8), QtCore.Qt.KeepAspectRatio)
            elif column == self.__hda_favorite_column:
                favorite_icon = 'ic_favorite_border_white.png'
                if data.get(public.Key.is_favorite_hda):
                    favorite_icon = 'ic_favorite_white.png'
                return QtGui.QPixmap(':/main/icons/{0}'.format(favorite_icon)).scaled(
                    QtCore.QSize(other_icon_size, other_icon_size), QtCore.Qt.KeepAspectRatio)
            elif column in self.__hda_datetime_column:
                datetime_icon = 'ic_query_builder_white.png'
                return QtGui.QPixmap(':/main/icons/{0}'.format(datetime_icon)).scaled(
                    QtCore.QSize(other_icon_size * 0.7, other_icon_size * 0.7), QtCore.Qt.KeepAspectRatio)
            elif column == self.__hda_hou_ver_column:
                hou_icon = 'houdini_logo.png'
                return QtGui.QPixmap(':/main/icons/{0}'.format(hou_icon)).scaled(
                    QtCore.QSize(other_icon_size * 0.7, other_icon_size * 0.7), QtCore.Qt.KeepAspectRatio)
            else:
                return None
        elif role == QtCore.Qt.TextAlignmentRole:
            if column in [0, 1]:
                return int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            return int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        elif role == QtCore.Qt.ToolTipRole:
            return data.get(self.__keys[column])
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            hda_filepath = data.get(public.Key.hda_dirpath) / data.get(public.Key.hda_filename)
            if not hda_filepath.exists():
                font.setItalic(True)
                font.setStrikeOut(True)
            return font
        elif role == TableModel.data_role:
            return data
        elif role == TableModel.row_role:
            return row
        elif role == TableModel.col_role:
            return column
        elif role == TableModel.id_role:
            return data.get(public.Key.hda_id)
        elif role == TableModel.filepath_role:
            return data.get(public.Key.hda_dirpath) / data.get(public.Key.hda_filename)
        elif role == TableModel.name_role:
            return data.get(public.Key.hda_name)
        elif role == TableModel.cate_role:
            return data.get(public.Key.hda_cate)
        elif role == TableModel.version_role:
            return data.get(public.Key.hda_version)
        elif role == TableModel.favorite_role:
            return data.get(public.Key.is_favorite_hda)
        elif role == TableModel.tag_role:
            return data.get(public.Key.hda_tags)
        elif role == TableModel.type_role:
            return data.get(public.Key.node_type_name)

    # def setData(self, index, value, role=QtCore.Qt.EditRole):
    #     if not index.isValid() or not (0 <= index.row() < len(self.__items)) or not value or (not len(value)):
    #         return False
    #     if role == QtCore.Qt.EditRole:
    #         if index.column() != self.__hda_name_column:
    #             return False
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

    def flags(self, index):
        flags = super(TableModel, self).flags(index)
        if index.isValid():
            hda_filepath = index.data(TableModel.filepath_role)
            if not hda_filepath.exists():
                flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                # flags = QtCore.Qt.ItemIsSelectable
            else:
                flags |= QtCore.Qt.ItemIsSelectable
                flags |= QtCore.Qt.ItemIsEnabled
                flags |= QtCore.Qt.ItemIsDragEnabled
                flags |= QtCore.Qt.ItemIsDropEnabled
                flags |= QtCore.Qt.ItemIsTristate
        else:
            flags |= QtCore.Qt.ItemIsSelectable
            flags |= QtCore.Qt.ItemIsEnabled
            flags |= QtCore.Qt.ItemIsDropEnabled
        return flags

    def reload(self, data=None):
        self.beginResetModel()
        self.__items = data
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

    def insertRow(self, position, rows=1, data=None, index=QtCore.QModelIndex()):
        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows - 1)
        for row in range(rows):
            # self.__items.insert(position + row, ['asd', 'sss'])
            self.__items.insert(position + row, data)
        self.endInsertRows()
        return True

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows - 1)
        del self.__items[position:position + rows]
        self.endRemoveRows()
        return True

    def mimeTypes(self):
        return [public.Type.mime_type]

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        if not len(indexes):
            return False
        mime_data = super(TableModel, self).mimeData(indexes)
        # 원래 0번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[public.Value.drag_column_table_view]]
        for index in indexes:
            if index.isValid():
                data = str(self.data(index, role=TableModel.data_role))
                mime_data.setData(public.Type.mime_type, QtCore.QByteArray(data))
        return mime_data

    def dropMimeData(self, mime_data, action, row, column, parent):
        return True

