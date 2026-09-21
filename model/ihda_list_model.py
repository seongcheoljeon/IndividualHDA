#!/usr/bin/env python
from __future__ import annotations

import contextlib
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from PySide6 import QtCore, QtGui

from libs.asset_contracts import AssetData, numbered
from libs.item_paths import item_path
from model.item_media import PixmapSource, thumbnail

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:34
# modify date       :
# description       :
from model.model_style import ModelStyleMixin

with contextlib.suppress(ImportError):
    pass

from libs import keys
from libs.drag_payload import encode_payload


class ListModel(QtCore.QAbstractListModel, ModelStyleMixin):
    data_role = QtCore.Qt.ItemDataRole.UserRole
    row_role = QtCore.Qt.ItemDataRole.UserRole + 1
    id_role = QtCore.Qt.ItemDataRole.UserRole + 2
    filepath_role = QtCore.Qt.ItemDataRole.UserRole + 3
    name_role = QtCore.Qt.ItemDataRole.UserRole + 4
    cate_role = QtCore.Qt.ItemDataRole.UserRole + 5
    version_role = QtCore.Qt.ItemDataRole.UserRole + 6
    favorite_role = QtCore.Qt.ItemDataRole.UserRole + 7
    tag_role = QtCore.Qt.ItemDataRole.UserRole + 8
    type_role = QtCore.Qt.ItemDataRole.UserRole + 9

    def __init__(
        self,
        items: list[AssetData] | None = None,
        pixmap_ihda_data: dict[int, QtGui.QPixmap] | None = None,
        pixmap_thumb_data: PixmapSource | dict[int, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        thumb_size: int | None = None,
        padding: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        # Keep the caller's list: AssetStore shares its rows with the models.
        self.__items = items if isinstance(items, list) else list(items or ())
        self.__items[:] = numbered(self.__items)
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
        )
        self.__pixmap_thumb_data: PixmapSource | dict[int, QtGui.QPixmap] = (
            pixmap_thumb_data if pixmap_thumb_data is not None else {}
        )
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
        self._padding = padding if padding is not None else 0
        self.__show_thumbnail = False

    @property
    def show_thumbnail(self) -> bool:
        return self.__show_thumbnail

    @show_thumbnail.setter
    def show_thumbnail(self, val: Any) -> None:
        self.__show_thumbnail = val

    def columnCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return 0 if parent.isValid() else 1

    def rowCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self.__items) if self.__items is not None else 0

    def flags(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsDropEnabled
        flags = super().flags(index)
        if index.isValid():
            data = index.data(ListModel.data_role)
            if not data.available and not data.remote:
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
                # flags |= QtCore.Qt.ItemFlag.ItemIsEditable
                flags |= QtCore.Qt.ItemFlag.ItemIsAutoTristate
        else:
            flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
            flags |= QtCore.Qt.ItemFlag.ItemIsEnabled
            flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def mimeTypes(self) -> list[str]:
        return [keys.Type.mime_type]

    def supportedDropActions(self) -> QtCore.Qt.DropAction:
        return QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction

    def mimeData(self, indexes: Sequence[QtCore.QModelIndex]) -> QtCore.QMimeData:
        if not len(indexes):
            return QtCore.QMimeData()
        mime_data = super().mimeData(indexes)
        for index in indexes:
            if index.isValid():
                data = encode_payload(self.data(index, role=ListModel.data_role))
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

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (index is None) or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        index_dat = self.__items[row]
        hda_name = index_dat.hda_name
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return hda_name
        # elif role == QtCore.Qt.ItemDataRole.EditRole:
        #     return hda_name
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            hda_id = index_dat.hda_id
            if self.show_thumbnail:
                return thumbnail(
                    self.__pixmap_thumb_data,
                    hda_id,
                    self.__thumb_size,
                )
            else:
                icon_pixmap = (
                    self.__pixmap_ihda_data.get(hda_id) if hda_id is not None else None
                )
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(int(self.__icon_size), int(self.__icon_size)),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            hda_ver = index_dat.hda_version
            if hda_ver is not None:
                return f"{hda_name} (v{hda_ver})"
            return hda_name
        elif role == QtCore.Qt.ItemDataRole.StatusTipRole:
            return None
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self._font_style)
            font.setPointSize(self._font_size)
            if not index_dat.available and not index_dat.remote:
                font.setItalic(True)
                font.setStrikeOut(True)
            return font
        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            if self.show_thumbnail:
                return QtCore.QSize(
                    int(self.__thumb_size + self._font_size + self._padding),
                    int(self.__thumb_size + self._font_size + self._padding),
                )
            return QtCore.QSize(
                int(self.__icon_size + self._font_size + self._padding),
                int(self.__icon_size + self._font_size + self._padding),
            )
        elif role == ListModel.data_role:
            return index_dat
        elif role == ListModel.row_role:
            return row
        elif role == ListModel.id_role:
            return index_dat.hda_id
        elif role == ListModel.filepath_role:
            return item_path(
                index_dat.hda_dirpath,
                index_dat.hda_filename,
            )
        elif role == ListModel.name_role:
            return hda_name
        elif role == ListModel.cate_role:
            return index_dat.hda_cate
        elif role == ListModel.version_role:
            return index_dat.hda_version
        elif role == ListModel.favorite_role:
            return index_dat.is_favorite_hda
        elif role == ListModel.tag_role:
            return index_dat.hda_tags
        elif role == ListModel.type_role:
            return index_dat.node_type_name

    # def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
    #     if not index.isValid() or not (0 <= index.row() < len(self.__items)) or not value or (not len(value)):
    #         return False
    #     if role == QtCore.Qt.ItemDataRole.EditRole:
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

    def add_items(self, data: Any = ()) -> None:
        self.beginResetModel()
        self.__items = data if isinstance(data, list) else list(data or ())
        self.__items[:] = numbered(self.__items)
        self.endResetModel()

    def append_item(self, item: Any) -> None:
        index = len(self.__items)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self.__items.append(replace(item, item_row=index))
        self.endInsertRows()

    def remove_item(self, row: int | None = None) -> bool:
        if row is None or not 0 <= row < len(self.__items):
            return False
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self.__items[row]
        self.__items[row:] = numbered(self.__items[row:], row)
        self.endRemoveRows()
        return True

    def clear_item(self) -> None:
        self.beginResetModel()
        self.__items = []
        self.endResetModel()
