#!/usr/bin/env python
from __future__ import annotations

import contextlib
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from PySide6 import QtCore, QtGui

from libs.asset_contracts import HistoryData, numbered
from libs.item_paths import item_path
from libs.model_columns import HistoryColumn
from libs.path_updates import PathMoves, relocate_history
from model.item_media import PixmapSource, thumbnail

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 11:45
# modify date       :
# description       :
from model.model_style import UNHANDLED, ModelStyleMixin, header_data

with contextlib.suppress(ImportError):
    pass

from libs import keys
from libs.drag_payload import encode_payload


class HistoryModel(QtCore.QAbstractTableModel, ModelStyleMixin):
    data_role = QtCore.Qt.ItemDataRole.UserRole
    row_role = QtCore.Qt.ItemDataRole.UserRole + 1
    col_role = QtCore.Qt.ItemDataRole.UserRole + 2
    id_role = QtCore.Qt.ItemDataRole.UserRole + 3
    filepath_role = QtCore.Qt.ItemDataRole.UserRole + 4
    name_role = QtCore.Qt.ItemDataRole.UserRole + 5
    hist_id_role = QtCore.Qt.ItemDataRole.UserRole + 6
    cate_role = QtCore.Qt.ItemDataRole.UserRole + 7
    version_role = QtCore.Qt.ItemDataRole.UserRole + 8
    tag_role = QtCore.Qt.ItemDataRole.UserRole + 9
    type_role = QtCore.Qt.ItemDataRole.UserRole + 10
    datetime_role = QtCore.Qt.ItemDataRole.UserRole + 11

    def __init__(
        self,
        items: list[HistoryData] | None = None,
        pixmap_ihda_data: dict[int, QtGui.QPixmap] | None = None,
        pixmap_cate_data: dict[str, QtGui.QPixmap] | None = None,
        pixmap_hist_thumb_data: PixmapSource | dict[int, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        thumb_size: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        # Keep the caller's list: AssetStore shares its rows with the models.
        self.__items = items if isinstance(items, list) else list(items or ())
        self.__items[:] = numbered(self.__items)
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
        )
        self.__pixmap_cate_data = (
            pixmap_cate_data if pixmap_cate_data is not None else {}
        )
        self.__pixmap_hist_thumb_data: PixmapSource | dict[int, QtGui.QPixmap] = (
            pixmap_hist_thumb_data if pixmap_hist_thumb_data is not None else {}
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
        # hda name 컬럼 인덱스
        self.__hda_name_column = HistoryColumn.NAME
        # hda def 컬럼 인덱스
        self.__hda_def_column = HistoryColumn.DEFINITION
        # hda category 컬럼 인덱스
        self.__hda_cate_column = HistoryColumn.CATEGORY
        # hda time 컬럼 인덱스
        self.__hda_datetime_column = HistoryColumn.CREATED
        # hda houdini version 컬럼 인덱스
        self.__hda_hou_ver_column = HistoryColumn.HOUDINI
        # hip dirpath 컬럼 인덱스
        self.__hda_dirpath_column = HistoryColumn.HIP_FOLDER

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        value = header_data(
            HistoryColumn, section, orientation, role, row_prefix="Hist"
        )
        if value is not UNHANDLED:
            return value
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
        return len(HistoryColumn)

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self.__items)):
            return None
        row = index.row()
        column = index.column()
        data = self.__items[row]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == HistoryColumn.ID and not data.is_version:
                return ""  # activity rows have no history id
            val = getattr(data, HistoryColumn(column).field)
            if column == self.__hda_dirpath_column:
                return str(val) if val is not None else ""
            return val
        # elif role == QtCore.Qt.ItemDataRole.EditRole:
        #     return val
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            other_icon_size = self.__icon_size * 0.7
            if column == self.__hda_name_column:
                if not data.is_version:
                    return None
                return thumbnail(
                    self.__pixmap_hist_thumb_data,
                    data.hist_id,
                    data.thumb_dirpath,
                    data.thumb_filename,
                    self.__thumb_size,
                )
            elif column == self.__hda_def_column:
                icon_pixmap = self.__pixmap_ihda_data.get(data.hda_id)
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == self.__hda_cate_column:
                hda_cate = data.node_category
                icon_pixmap = self.__pixmap_cate_data.get(hda_cate)
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == self.__hda_datetime_column:
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
            if column in [
                HistoryColumn.NAME,
                HistoryColumn.DEFINITION,
                HistoryColumn.CATEGORY,
                HistoryColumn.COMMENT,
                HistoryColumn.NODE_PATH,
                HistoryColumn.HIP_FOLDER,
                HistoryColumn.HIP_FILE,
            ]:
                return int(
                    QtCore.Qt.AlignmentFlag.AlignLeft
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self._font_style)
            font.setPointSize(self._font_size)
            if not data.is_version:
                font.setItalic(True)  # no file behind it, but nothing is missing
                return font
            if not data.available and not data.remote:
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
            return data.hda_id
        elif role == HistoryModel.hist_id_role:
            return data.hist_id
        elif role == HistoryModel.filepath_role:
            hda_dirpath = data.ihda_dirpath
            return item_path(hda_dirpath, data.ihda_filename)
        elif role == HistoryModel.name_role:
            return data.org_hda_name
        elif role == HistoryModel.cate_role:
            return data.node_category
        elif role == HistoryModel.version_role:
            return data.version
        elif role == HistoryModel.tag_role:
            return data.tags
        elif role == HistoryModel.type_role:
            return data.node_type_name
        elif role == HistoryModel.datetime_role:
            return data.reg_time

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
        if not index.data(HistoryModel.data_role).is_version:
            # Activity rows are readable but never dragged into Houdini.
            return (
                QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
        if index.isValid():
            data = index.data(HistoryModel.data_role)
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
                flags |= QtCore.Qt.ItemFlag.ItemIsAutoTristate
        else:
            flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
            flags |= QtCore.Qt.ItemFlag.ItemIsEnabled
            flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def reload(self, data: Any = None) -> None:
        self.beginResetModel()
        self.__items = data if isinstance(data, list) else list(data or ())
        self.__items[:] = numbered(self.__items)
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

    def relocate_asset_paths(
        self, asset_id: int, moves: PathMoves
    ) -> list[HistoryData]:
        changed = []
        for row, item in enumerate(self.__items):
            if item.hda_id != asset_id or not item.is_version:
                continue
            item = relocate_history(item, moves)
            self.__items[row] = item
            changed.append(item)
            self.dataChanged.emit(
                self.index(row, 0), self.index(row, self.columnCount() - 1), []
            )
        return changed

    def update_item_data(
        self, row: int | None = None, key: Any = None, val: Any = None
    ) -> None:
        if row is None:
            return
        self.__items[row] = replace(self.__items[row], **{key: val})
        self.dataChanged.emit(
            self.index(row, 0), self.index(row, self.columnCount() - 1), []
        )

    # hkey_id 단위의 업데이트
    def update_item_data_by_hkey_id_from_model(
        self, hkey_id: int | None = None, key: Any = None, val: Any = None
    ) -> None:
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) != hkey_id:
                continue
            row = index.data(HistoryModel.row_role)
            try:
                hist_data = self.__items[row]
            except IndexError:
                continue
            data_row = hist_data.item_row
            if data_row is None:
                continue
            if row == data_row:
                self.update_item_data(row=row, key=key, val=val)

    # hkey_id & version 단위의 업데이트
    # 히스토리 아이템이 존재하는지
    def is_exist_ihda_item_from_model(self, hkey_id: int | None = None) -> bool:
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) == hkey_id:
                return True
        return False

    def get_history_id_from_model(
        self, hkey_id: int | None = None, version: str | None = None
    ) -> int | None:
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if index.data(HistoryModel.id_role) == hkey_id:
                if (
                    index.data(HistoryModel.version_role) == version
                    and index.data(HistoryModel.data_role).is_version
                ):
                    return index.data(HistoryModel.hist_id_role)
        return None

    def get_hist_data_by_hkey_id_from_model(
        self, hkey_id: int | None = None
    ) -> list[Any]:
        hist_data_lst = []
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            hda_id = index.data(HistoryModel.id_role)
            if hkey_id == hda_id:
                hist_data_lst.append(index.data(HistoryModel.data_role))
        return hist_data_lst

    # hist_id와 item_row의 맵 데이터
    def get_hist_id_row_map_from_model(self) -> dict[int, int]:
        map_lst = []
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            map_lst.append((index.data(HistoryModel.hist_id_role), row))
        return dict(map_lst)

    # history 모델에서 hist_id와 같은 item row를 반환

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
        self.__items[position:] = numbered(self.__items[position:], position)
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
        # 원래 2번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[keys.Value.drag_column_history_view]]
        for index in indexes:
            if index.isValid():
                data = encode_payload(self.data(index, role=HistoryModel.data_role))
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
