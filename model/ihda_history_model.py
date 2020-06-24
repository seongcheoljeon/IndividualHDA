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


class HistoryModel(QtCore.QAbstractTableModel):
    data_role = QtCore.Qt.UserRole
    row_role = QtCore.Qt.UserRole + 1
    col_role = QtCore.Qt.UserRole + 2
    id_role = QtCore.Qt.UserRole + 3
    filepath_role = QtCore.Qt.UserRole + 4
    name_role = QtCore.Qt.UserRole + 5
    hist_id_role = QtCore.Qt.UserRole + 6
    cate_role = QtCore.Qt.UserRole + 7
    version_role = QtCore.Qt.UserRole + 8
    tag_role = QtCore.Qt.UserRole + 9
    type_role = QtCore.Qt.UserRole + 10
    datetime_role = QtCore.Qt.UserRole + 11

    def __init__(self, items=None, pixmap_ihda_data=None, pixmap_cate_data=None, pixmap_hist_thumb_data=None,
                 font_size=None, font_style=None, icon_size=None, thumb_size=None, parent=None):
        super(HistoryModel, self).__init__(parent)
        self.__items = items
        self.__pixmap_ihda_data = pixmap_ihda_data
        self.__pixmap_cate_data = pixmap_cate_data
        self.__pixmap_hist_thumb_data = pixmap_hist_thumb_data
        self.__font_size = font_size
        self.__font_style = font_style
        self.__icon_size = icon_size
        self.__thumb_size = thumb_size
        self.__headers = [
            'ID', 'Name', 'Definition', 'Category', 'Comment', 'Version', 'Date Time', 'Type',
            'Node Path', 'Houdini', 'License', 'OS', 'HIP Folder', 'HIP File']
        self.__keys = [
            public.Key.History.hist_id, public.Key.History.org_hda_name, public.Key.History.node_def_desc,
            public.Key.History.node_category, public.Key.History.comment, public.Key.History.version,
            public.Key.History.reg_time, public.Key.History.node_type_name, public.Key.History.node_old_path,
            public.Key.History.hou_version, public.Key.History.hda_license, public.Key.History.os,
            public.Key.History.hip_dirpath, public.Key.History.hip_filename]
        assert len(self.__headers) == len(self.__keys)
        # hda name 컬럼 인덱스
        self.__hda_name_column = 1
        # hda def 컬럼 인덱스
        self.__hda_def_column = 2
        # hda category 컬럼 인덱스
        self.__hda_cate_column = 3
        # hda time 컬럼 인덱스
        self.__hda_datetime_column = 6
        # hda houdini version 컬럼 인덱스
        self.__hda_hou_ver_column = 9
        # hip dirpath 컬럼 인덱스
        self.__hda_dirpath_column = 12

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return '{0}'.format(self.__headers[section])
            else:
                return 'Hist {0}'.format(section + 1)
        if role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setPointSize(public.UISetting.view_font_size)
            return font
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__items) if self.__items is not None else 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.__headers)

    def set_row_col_in_item(self, row):
        self.__items[row][public.Key.History.item_row] = row

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        column = index.column()
        self.set_row_col_in_item(row)
        data = self.__items[row]
        if role == QtCore.Qt.DisplayRole:
            val = data.get(self.__keys[column])
            if column == self.__hda_dirpath_column:
                return val.as_posix()
            return val
        # elif role == QtCore.Qt.EditRole:
        #     return val
        elif role == QtCore.Qt.DecorationRole:
            other_icon_size = self.__icon_size * 0.7
            if column == self.__hda_name_column:
                hist_id = data.get(public.Key.History.hist_id)
                thumb_pixmap = self.__pixmap_hist_thumb_data.get(hist_id)
                if thumb_pixmap is None:
                    return QtGui.QPixmap(':/main/icons/no_img_available.png')
                if thumb_pixmap.isNull():
                    thumb_dirpath = data.get(public.Key.History.thumb_dirpath)
                    if thumb_dirpath is None:
                        thumb_pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
                    else:
                        thumb_filepath = thumb_dirpath / data.get(public.Key.History.thumb_filename)
                        if not thumb_filepath.exists():
                            thumb_pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
                        else:
                            thumb_pixmap = QtGui.QPixmap(thumb_filepath.fileName())
                        self.__pixmap_hist_thumb_data.update({hist_id: thumb_pixmap})
                return thumb_pixmap.scaled(QtCore.QSize(self.__thumb_size, self.__thumb_size),
                    QtCore.Qt.KeepAspectRatio)
            elif column == self.__hda_def_column:
                icon_pixmap = self.__pixmap_ihda_data.get(data.get(public.Key.History.hda_id))
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(self.__icon_size * 0.8, self.__icon_size * 0.8), QtCore.Qt.KeepAspectRatio)
            elif column == self.__hda_cate_column:
                hda_cate = data.get(public.Key.History.node_category)
                icon_pixmap = self.__pixmap_cate_data.get(hda_cate)
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(self.__icon_size * 0.8, self.__icon_size * 0.8), QtCore.Qt.KeepAspectRatio)
            elif column == self.__hda_datetime_column:
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
            if column in [1, 2, 3, 4, 8, 12, 13, 14]:
                return int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            return int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            hda_dirpath = data.get(public.Key.History.ihda_dirpath)
            if hda_dirpath is None:
                font.setItalic(True)
                font.setStrikeOut(True)
            else:
                hda_filepath = hda_dirpath / data.get(public.Key.History.ihda_filename)
                if not hda_filepath.exists():
                    font.setItalic(True)
                    font.setStrikeOut(True)
            return font
        elif role == HistoryModel.data_role:
            return data
        elif role == HistoryModel.row_role:
            return row
        elif role == HistoryModel.col_role:
            return column
        elif role == HistoryModel.id_role:
            return data.get(public.Key.History.hda_id)
        elif role == HistoryModel.hist_id_role:
            return data.get(public.Key.History.hist_id)
        elif role == HistoryModel.filepath_role:
            hda_dirpath = data.get(public.Key.History.ihda_dirpath)
            return hda_dirpath / data.get(public.Key.History.ihda_filename)
        elif role == HistoryModel.name_role:
            return data.get(public.Key.History.org_hda_name)
        elif role == HistoryModel.cate_role:
            return data.get(public.Key.History.node_category)
        elif role == HistoryModel.version_role:
            return data.get(public.Key.History.version)
        elif role == HistoryModel.tag_role:
            return data.get(public.Key.History.tags)
        elif role == HistoryModel.type_role:
            return data.get(public.Key.History.node_type_name)
        elif role == HistoryModel.datetime_role:
            return data.get(public.Key.History.reg_time)

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
        flags = super(HistoryModel, self).flags(index)
        if index.isValid():
            hda_filepath = index.data(HistoryModel.filepath_role)
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

    def update_item_data(self, row=None, key=None, val=None):
        self.__items[row][key] = val

    # hkey_id 단위의 업데이트
    def update_item_data_by_hkey_id_from_model(self, hkey_id=None, key=None, val=None):
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) != hkey_id:
                continue
            row = index.data(HistoryModel.row_role)
            try:
                hist_data = self.__items[row]
            except IndexError as err:
                continue
            data_row = hist_data.get(public.Key.History.item_row)
            if data_row is None:
                continue
            if row == data_row:
                self.update_item_data(row=row, key=key, val=val)

    # hkey_id & version 단위의 업데이트
    def update_item_data_by_hkey_id_version_from_model(self, hkey_id=None, version=None, key=None, val=None):
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) == hkey_id:
                if index.data(HistoryModel.version_role) == version:
                    self.update_item_data(row=row, key=key, val=val)

    # 히스토리 아이템이 존재하는지
    def is_exist_ihda_item_from_model(self, hkey_id=None):
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) == hkey_id:
                return True
        return False

    def get_history_id_from_model(self, hkey_id=None, version=None):
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) == hkey_id:
                if index.data(HistoryModel.version_role) == version:
                    return index.data(HistoryModel.hist_id_role)
        return None

    def get_hist_data_by_hkey_id_from_model(self, hkey_id=None):
        hist_data_lst = list()
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            hda_id = index.data(HistoryModel.id_role)
            if hkey_id == hda_id:
                hist_data_lst.append(index.data(HistoryModel.data_role))
        return hist_data_lst

    # hist_id와 item_row의 맵 데이터
    def get_hist_id_row_map_from_model(self):
        map_lst = list()
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            map_lst.append((index.data(HistoryModel.hist_id_role), row))
        return dict(map_lst)

    # history 모델에서 hist_id와 같은 item row를 반환
    def get_hist_item_row_by_hist_id_from_model(self, hist_id=None):
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if hist_id == index.data(HistoryModel.hist_id_role):
                return row
        return None

    def remove_item(self, row=None):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        try:
            del self.__items[row]
        except IndexError as err:
            pass
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
        mime_data = super(HistoryModel, self).mimeData(indexes)
        # 원래 2번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[public.Value.drag_column_history_view]]
        for index in indexes:
            if index.isValid():
                data = str(self.data(index, role=HistoryModel.data_role))
                mime_data.setData(public.Type.mime_type, QtCore.QByteArray(data))
        return mime_data

    def dropMimeData(self, mime_data, action, row, column, parent):
        return True

