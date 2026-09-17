#!/usr/bin/env python
from __future__ import annotations

import contextlib
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from PySide6 import QtCore, QtGui

from libs.asset_contracts import AssetData
from libs.item_paths import item_path
from libs.model_columns import AssetColumn
from model.item_media import PixmapSource, thumbnail

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 11:45
# modify date       :
# description       :
from model.model_style import ModelStyleMixin

with contextlib.suppress(ImportError):
    pass

from libs import keys
from libs.drag_payload import encode_payload


class TableModel(QtCore.QAbstractTableModel, ModelStyleMixin):
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
        pixmap_thumb_data: PixmapSource | dict[int, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        thumb_size: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.__items = items if items is not None else []
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
        )
        self.__pixmap_thumb_data: PixmapSource | dict[int, QtGui.QPixmap] = (
            pixmap_thumb_data if pixmap_thumb_data is not None else {}
        )
        self.__show_thumbnail = False
        # hda name 컬럼 인덱스
        self.__hda_name_column = AssetColumn.NAME
        # hda def 컬럼 인덱스
        self.__hda_def_column = AssetColumn.DEFINITION
        # hda 즐겨찾기 컬럼 인덱스
        self.__hda_favorite_column = AssetColumn.FAVORITE
        # hda time 컬럼 인덱스
        self.__hda_datetime_column = [AssetColumn.CREATED, AssetColumn.MODIFIED]
        # hda houdini version 컬럼 인덱스
        self.__hda_hou_ver_column = AssetColumn.HOUDINI
        #
        self._font_size = (
            font_size if font_size is not None else keys.UISetting.view_font_size
        )
        self._font_style = (
            font_style if font_style is not None else keys.UISetting.view_font_style
        )
        self.__icon_size = (
            icon_size
            if icon_size is not None
            else keys.UISetting.treeview_node_icon_size
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
                return f"{AssetColumn(section).label}"
            else:
                return f"iHDA {section + 1}"
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setPointSize(keys.UISetting.view_font_size)
            return font
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

    def rowCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self.__items) if self.__items is not None else 0

    def columnCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return len(AssetColumn)
        # return len(AssetColumn) if self.rowCount() else 0

    def set_row_col_in_item(self, row: int) -> None:
        self.__items[row] = replace(self.__items[row], item_row=row)

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
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
            return getattr(data, AssetColumn(column).field)
        # elif role == QtCore.Qt.ItemDataRole.EditRole:
        #     return val
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            other_icon_size = self.__icon_size * 0.7
            node_icon_column = (
                self.__hda_name_column
                if not self.show_thumbnail
                else self.__hda_def_column
            )
            hda_id = data.hda_id
            if self.show_thumbnail and column == self.__hda_name_column:
                return thumbnail(
                    self.__pixmap_thumb_data,
                    hda_id,
                    data.thumbnail_dirpath,
                    data.thumbnail_filename,
                    self.__thumb_size,
                )
            if column == node_icon_column:
                icon_pixmap = (
                    self.__pixmap_ihda_data.get(hda_id) if hda_id is not None else None
                )
                if icon_pixmap is None:
                    return None
                if node_icon_column == AssetColumn.NAME:
                    return icon_pixmap.scaled(
                        QtCore.QSize(int(self.__icon_size), int(self.__icon_size)),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
                elif node_icon_column == AssetColumn.DEFINITION:
                    return icon_pixmap.scaled(
                        QtCore.QSize(
                            int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                        ),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
            elif column == self.__hda_favorite_column:
                favorite_icon = "ic_favorite_border_white.png"
                if data.is_favorite_hda:
                    favorite_icon = "ic_favorite_white.png"
                return QtGui.QPixmap(f":/main/icons/{favorite_icon}").scaled(
                    QtCore.QSize(int(other_icon_size), int(other_icon_size)),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column in self.__hda_datetime_column:
                datetime_icon = "ic_query_builder_white.png"
                return QtGui.QPixmap(f":/main/icons/{datetime_icon}").scaled(
                    QtCore.QSize(
                        int(other_icon_size * 0.7), int(other_icon_size * 0.7)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == self.__hda_hou_ver_column:
                hou_icon = "houdini_logo.png"
                return QtGui.QPixmap(f":/main/icons/{hou_icon}").scaled(
                    QtCore.QSize(
                        int(other_icon_size * 0.7), int(other_icon_size * 0.7)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            else:
                return None
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if column in [AssetColumn.NAME, AssetColumn.DEFINITION]:
                return int(
                    QtCore.Qt.AlignmentFlag.AlignLeft
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return getattr(data, AssetColumn(column).field)
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self._font_style)
            font.setPointSize(self._font_size)
            hda_filepath = item_path(data.hda_dirpath, data.hda_filename)
            if (hda_filepath is None or not hda_filepath.exists()) and not index.data(
                TableModel.data_role
            ).remote:
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
            return data.hda_id
        elif role == TableModel.filepath_role:
            return item_path(data.hda_dirpath, data.hda_filename)
        elif role == TableModel.name_role:
            return data.hda_name
        elif role == TableModel.cate_role:
            return data.hda_cate
        elif role == TableModel.version_role:
            return data.hda_version
        elif role == TableModel.favorite_role:
            return data.is_favorite_hda
        elif role == TableModel.tag_role:
            return data.hda_tags
        elif role == TableModel.type_role:
            return data.node_type_name

    # def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
    #     if not index.isValid() or not (0 <= index.row() < len(self.__items)) or not value or (not len(value)):
    #         return False
    #     if role == QtCore.Qt.ItemDataRole.EditRole:
    #         if index.column() != self.__hda_name_column:
    #             return False
    #         row = index.row()
    #         value = str(value.strip()).replace(' ', '_')
    #         index_data = self.__items[row]
    #         hda_name = index_data.get(keys.Key.hda_name)
    #         if (hda_name == value) or (not len(value)):
    #             return False
    #         self.__items[row][keys.Key.hda_name] = value
    #         self.dataChanged.emit(index, index, [QtCore.Qt.ItemDataRole.EditRole])
    #         return True
    #     return False

    def flags(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsDropEnabled
        flags = super().flags(index)
        if index.isValid():
            hda_filepath = index.data(TableModel.filepath_role)
            if (hda_filepath is None or not hda_filepath.exists()) and not index.data(
                TableModel.data_role
            ).remote:
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
            else keys.UISetting.treeview_node_icon_size
        )
        self.__thumb_size = (
            thumb_size if thumb_size is not None else 2 * self.__icon_size
        )
        self.endResetModel()

    def insertRow(
        self,
        row: int,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> bool:
        return self.insertRows(row, 1, parent)

    def insertRows(
        self,
        row: int,
        count: int,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> bool:
        # Asset/history rows need complete domain data. Use append_item or the
        # panel's shared-model insertion coordinator, not empty Qt rows.
        return False

    def removeRows(
        self,
        position: Any,
        rows: int = 1,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
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
        return [keys.Type.mime_type]

    def supportedDropActions(self) -> QtCore.Qt.DropAction:
        return QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction

    def mimeData(self, indexes: Sequence[QtCore.QModelIndex]) -> QtCore.QMimeData:
        if not len(indexes):
            return QtCore.QMimeData()
        mime_data = super().mimeData(indexes)
        # 원래 0번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[keys.Value.drag_column_table_view]]
        for index in indexes:
            if index.isValid():
                data = encode_payload(self.data(index, role=TableModel.data_role))
                mime_data.setData(keys.Type.mime_type, QtCore.QByteArray(data))
        return mime_data

    def dropMimeData(
        self,
        mime_data: QtCore.QMimeData,
        action: QtCore.Qt.DropAction,
        row: int,
        column: int,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> bool:
        # Domain drops are handled by view signals, not raw Qt row insertion.
        return action == QtCore.Qt.DropAction.IgnoreAction
