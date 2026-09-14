#!/usr/bin/env python
from __future__ import annotations

import contextlib
from typing import Any

from PySide6 import QtCore, QtGui

from libs.domain import AssetData

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:34
# modify date       :
# description       :
from model.model_style import ModelStyleMixin

with contextlib.suppress(ImportError):
    pass

import public
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
        pixmap_thumb_data: dict[int, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        thumb_size: int | None = None,
        padding: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.__items = items if items is not None else []
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
        )
        self.__pixmap_thumb_data = (
            pixmap_thumb_data if pixmap_thumb_data is not None else {}
        )
        self._font_size = (
            font_size if font_size is not None else public.UISetting.view_font_size
        )
        self._font_style = (
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
        self._padding = padding if padding is not None else 0
        self.__show_thumbnail = False

    @property
    def show_thumbnail(self) -> bool:
        return self.__show_thumbnail

    @show_thumbnail.setter
    def show_thumbnail(self, val: Any) -> None:
        self.__show_thumbnail = val

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else 1

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.__items) if self.__items is not None else 0

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsDropEnabled
        flags = super().flags(index)
        if index.isValid():
            hda_filepath = index.data(ListModel.filepath_role)
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
                # flags |= QtCore.Qt.ItemFlag.ItemIsEditable
                flags |= QtCore.Qt.ItemFlag.ItemIsAutoTristate
        else:
            flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
            flags |= QtCore.Qt.ItemFlag.ItemIsEnabled
            flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def mimeTypes(self) -> list[str]:
        return [public.Type.mime_type]

    def supportedDropActions(self) -> QtCore.Qt.DropAction:
        return QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction

    def mimeData(self, indexes: list[QtCore.QModelIndex]) -> QtCore.QMimeData | None:
        if not len(indexes):
            return None
        mime_data = super().mimeData(indexes)
        for index in indexes:
            if index.isValid():
                data = encode_payload(self.data(index, role=ListModel.data_role))
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

    def set_row_col_in_item(self, row: int) -> None:
        self.__items[row][public.Key.item_row] = row

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if (index is None) or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        self.set_row_col_in_item(row)
        index_dat = self.__items[row]
        hda_name = index_dat.get(public.Key.hda_name)
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return hda_name
        # elif role == QtCore.Qt.ItemDataRole.EditRole:
        #     return hda_name
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            hda_id = index_dat.get(public.Key.hda_id)
            if self.show_thumbnail:
                thumb_pixmap = self.__pixmap_thumb_data.get(hda_id)
                if thumb_pixmap is None:
                    return QtGui.QPixmap(":/main/icons/no_img_available.png")
                if thumb_pixmap.isNull():
                    thumb_filename = index_dat.get(public.Key.thumbnail_filename)
                    thumb_filepath = (
                        index_dat.get(public.Key.thumbnail_dirpath) / thumb_filename
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
            else:
                icon_pixmap = self.__pixmap_ihda_data.get(hda_id)
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(self.__icon_size, self.__icon_size),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            hda_ver = index_dat.get(public.Key.hda_version)
            if hda_ver is not None:
                return f"{hda_name} (v{hda_ver})"
            return hda_name
        elif role == QtCore.Qt.ItemDataRole.StatusTipRole:
            return None
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self._font_style)
            font.setPointSize(self._font_size)
            hda_filepath = index_dat.get(public.Key.hda_dirpath) / index_dat.get(
                public.Key.hda_filename
            )
            if not hda_filepath.exists():
                font.setItalic(True)
                font.setStrikeOut(True)
            return font
        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            if self.show_thumbnail:
                return QtCore.QSize(
                    self.__thumb_size + self._font_size + self._padding,
                    self.__thumb_size + self._font_size + self._padding,
                )
            return QtCore.QSize(
                self.__icon_size + self._font_size + self._padding,
                self.__icon_size + self._font_size + self._padding,
            )
        elif role == ListModel.data_role:
            return index_dat
        elif role == ListModel.row_role:
            return row
        elif role == ListModel.id_role:
            return index_dat.get(public.Key.hda_id)
        elif role == ListModel.filepath_role:
            return index_dat.get(public.Key.hda_dirpath) / index_dat.get(
                public.Key.hda_filename
            )
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

    # def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
    #     if not index.isValid() or not (0 <= index.row() < len(self.__items)) or not value or (not len(value)):
    #         return False
    #     if role == QtCore.Qt.ItemDataRole.EditRole:
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
