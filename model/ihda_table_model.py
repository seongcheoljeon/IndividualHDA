#!/usr/bin/env python
from __future__ import annotations

from libs.domain import AssetData
from typing import Any
from PySide6 import QtCore

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 11:45
# modify date       :
# description       :


from PySide6 import QtGui

try:
    import hou
except ImportError as err:
    pass

import public
from libs.drag_payload import encode_payload


class TableModel(QtCore.QAbstractTableModel):
    data_role = QtCore.Qt.ItemDataRole.UserRole
    row_role = QtCore.Qt.ItemDataRole.UserRole + 1
    col_role = QtCore.Qt.ItemDataRole.UserRole + 2
    id_role = QtCore.Qt.ItemDataRole.UserRole + 3
    filepath_role = QtCore.Qt.ItemDataRole.UserRole + 4
    name_role = QtCore.Qt.ItemDataRole.UserRole + 5
    cate_role = QtCore.Qt.ItemDataRole.UserRole + 6
    version_role = QtCore.Qt.ItemDataRole.UserRole + 7
    favorite_role = QtCore.Qt.ItemDataRole.UserRole + 8
    tag_role = QtCore.Qt.ItemDataRole.UserRole + 9
    type_role = QtCore.Qt.ItemDataRole.UserRole + 10

    def __init__(
        self,
        items: list[AssetData] | None = None,
        pixmap_ihda_data: dict[int, QtGui.QPixmap] | None = None,
        pixmap_thumb_data: dict[int, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        thumb_size: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super(TableModel, self).__init__(parent)
        self.__items = items if items is not None else []
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
        )
        self.__pixmap_thumb_data = (
            pixmap_thumb_data if pixmap_thumb_data is not None else {}
        )
        self.__show_thumbnail = False
        self.__headers = [
            "Name",
            "Definition",
            "Like",
            "Version",
            "Count",
            "Created Date",
            "Modified Date",
            "Houdini",
            "License",
        ]
        self.__keys = [
            public.Key.hda_name,
            public.Key.node_def_desc,
            public.Key.is_favorite_hda,
            public.Key.hda_version,
            public.Key.hda_load_count,
            public.Key.hda_ctime,
            public.Key.hda_mtime,
            public.Key.hou_version,
            public.Key.hda_license,
        ]
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
        self.__font_size = (
            font_size if font_size is not None else public.UISetting.view_font_size
        )
        self.__font_style = (
            font_style if font_style is not None else public.UISetting.view_font_style
        )
        self.__icon_size = (
            icon_size
            if icon_size is not None
            else public.UISetting.treeview_node_icon_size
        )
        self.__thumb_size = (
            thumb_size if thumb_size is not None else 2 * self.__icon_size
        )

    @property
    def show_thumbnail(self) -> bool:
        return self.__show_thumbnail

    @show_thumbnail.setter
    def show_thumbnail(self, val: Any) -> None:
        self.__show_thumbnail = val

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return "{0}".format(self.__headers[section])
            else:
                return "iHDA {0}".format(section + 1)
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setPointSize(public.UISetting.view_font_size)
            return font
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.__items) if self.__items is not None else 0

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.__headers)
        # return len(self.__headers) if self.rowCount() else 0

    def set_row_col_in_item(self, row: int) -> None:
        self.__items[row][public.Key.item_row] = row

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        column = index.column()
        self.set_row_col_in_item(row)
        data = self.__items[row]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == self.__hda_favorite_column:
                return None
            return data.get(self.__keys[column])
        # elif role == QtCore.Qt.ItemDataRole.EditRole:
        #     return val
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            other_icon_size = self.__icon_size * 0.7
            node_icon_column = (
                self.__hda_name_column
                if not self.show_thumbnail
                else self.__hda_def_column
            )
            hda_id = data.get(public.Key.hda_id)
            if self.show_thumbnail:
                if column == self.__hda_name_column:
                    thumb_pixmap = self.__pixmap_thumb_data.get(hda_id)
                    if thumb_pixmap is None:
                        return QtGui.QPixmap(":/main/icons/no_img_available.png")
                    if thumb_pixmap.isNull():
                        thumb_filename = data.get(public.Key.thumbnail_filename)
                        thumb_filepath = (
                            data.get(public.Key.thumbnail_dirpath) / thumb_filename
                        )
                        if (thumb_filepath is None) or (not thumb_filepath.exists()):
                            thumb_pixmap = QtGui.QPixmap(
                                ":/main/icons/no_img_available.png"
                            )
                        else:
                            thumb_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
                            self.__pixmap_thumb_data.update({hda_id: thumb_pixmap})
                    return thumb_pixmap.scaled(
                        QtCore.QSize(self.__thumb_size, self.__thumb_size),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
            if column == node_icon_column:
                icon_pixmap = self.__pixmap_ihda_data.get(hda_id)
                if icon_pixmap is None:
                    return None
                if node_icon_column == 0:
                    return icon_pixmap.scaled(
                        QtCore.QSize(self.__icon_size, self.__icon_size),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
                elif node_icon_column == 1:
                    return icon_pixmap.scaled(
                        QtCore.QSize(
                            int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                        ),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
            elif column == self.__hda_favorite_column:
                favorite_icon = "ic_favorite_border_white.png"
                if data.get(public.Key.is_favorite_hda):
                    favorite_icon = "ic_favorite_white.png"
                return QtGui.QPixmap(":/main/icons/{0}".format(favorite_icon)).scaled(
                    QtCore.QSize(int(other_icon_size), int(other_icon_size)),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column in self.__hda_datetime_column:
                datetime_icon = "ic_query_builder_white.png"
                return QtGui.QPixmap(":/main/icons/{0}".format(datetime_icon)).scaled(
                    QtCore.QSize(
                        int(other_icon_size * 0.7), int(other_icon_size * 0.7)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == self.__hda_hou_ver_column:
                hou_icon = "houdini_logo.png"
                return QtGui.QPixmap(":/main/icons/{0}".format(hou_icon)).scaled(
                    QtCore.QSize(
                        int(other_icon_size * 0.7), int(other_icon_size * 0.7)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            else:
                return None
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if column in [0, 1]:
                return int(
                    QtCore.Qt.AlignmentFlag.AlignLeft
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return data.get(self.__keys[column])
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            hda_filepath = data.get(public.Key.hda_dirpath) / data.get(
                public.Key.hda_filename
            )
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

    # def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
    #     if not index.isValid() or not (0 <= index.row() < len(self.__items)) or not value or (not len(value)):
    #         return False
    #     if role == QtCore.Qt.ItemDataRole.EditRole:
    #         if index.column() != self.__hda_name_column:
    #             return False
    #         row = index.row()
    #         value = str(value.strip()).replace(' ', '_')
    #         index_data = self.__items[row]
    #         hda_name = index_data.get(public.Key.hda_name)
    #         if (hda_name == value) or (not len(value)):
    #             return False
    #         self.__items[row][public.Key.hda_name] = value
    #         self.dataChanged.emit(index, index, [QtCore.Qt.ItemDataRole.EditRole])
    #         return True
    #     return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsDropEnabled
        flags = super(TableModel, self).flags(index)
        if index.isValid():
            hda_filepath = index.data(TableModel.filepath_role)
            if not hda_filepath.exists():
                flags = (
                    QtCore.Qt.ItemFlag.ItemIsSelectable
                    | QtCore.Qt.ItemFlag.ItemIsEnabled
                )
                # flags = QtCore.Qt.ItemFlag.ItemIsSelectable
            else:
                flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
                flags |= QtCore.Qt.ItemFlag.ItemIsEnabled
                flags |= QtCore.Qt.ItemFlag.ItemIsDragEnabled
                flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
                flags |= QtCore.Qt.ItemFlag.ItemIsAutoTristate
        else:
            flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
            flags |= QtCore.Qt.ItemFlag.ItemIsEnabled
            flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def reload(self, data: Any = None) -> None:
        self.beginResetModel()
        self.__items = data if isinstance(data, list) else list(data or ())
        self.endResetModel()

    def add_items(self, data: Any = ()) -> None:
        self.beginResetModel()
        self.__items = data if isinstance(data, list) else list(data or ())
        self.endResetModel()

    def append_item(self, item: Any) -> None:
        index = len(self.__items)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self.__items.append(item)
        self.endInsertRows()

    def remove_item(self, row: int | None = None) -> bool:
        if row is None or not 0 <= row < len(self.__items):
            return False
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self.__items[row]
        self.endRemoveRows()
        return True

    def clear_item(self) -> None:
        self.beginResetModel()
        self.__items = []
        self.endResetModel()

    def set_icon_size(
        self, icon_size: int | None = None, thumb_size: int | None = None
    ) -> None:
        self.beginResetModel()
        self.__icon_size = (
            icon_size
            if icon_size is not None
            else public.UISetting.treeview_node_icon_size
        )
        self.__thumb_size = (
            thumb_size if thumb_size is not None else 2 * self.__icon_size
        )
        self.endResetModel()

    def set_font(self, style: str | None = None, size: int | None = None) -> None:
        self.beginResetModel()
        self.__font_style = style
        self.__font_size = size
        self.endResetModel()

    def insertRow(
        self, row: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> bool:
        return self.insertRows(row, 1, parent)

    def insertRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> bool:
        # Asset/history rows need complete domain data. Use append_item or the
        # panel's shared-model insertion coordinator, not empty Qt rows.
        return False

    def removeRows(
        self,
        position: Any,
        rows: int = 1,
        index: QtCore.QModelIndex = QtCore.QModelIndex(),
    ) -> bool:
        if (
            index.isValid()
            or rows <= 0
            or position < 0
            or position + rows > self.rowCount()
        ):
            return False
        self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows - 1)
        del self.__items[position : position + rows]
        self.endRemoveRows()
        return True

    def mimeTypes(self) -> list[str]:
        return [public.Type.mime_type]

    def supportedDropActions(self) -> QtCore.Qt.DropAction:
        return QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction

    def mimeData(self, indexes: list[QtCore.QModelIndex]) -> QtCore.QMimeData | None:
        if not len(indexes):
            return None
        mime_data = super(TableModel, self).mimeData(indexes)
        # 원래 0번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[public.Value.drag_column_table_view]]
        for index in indexes:
            if index.isValid():
                data = encode_payload(self.data(index, role=TableModel.data_role))
                mime_data.setData(public.Type.mime_type, QtCore.QByteArray(data))
        return mime_data

    def dropMimeData(
        self,
        mime_data: QtCore.QMimeData,
        action: QtCore.Qt.DropAction,
        row: int,
        column: int,
        parent: QtCore.QModelIndex,
    ) -> bool:
        # Domain drops are handled by view signals, not raw Qt row insertion.
        return action == QtCore.Qt.DropAction.IgnoreAction
