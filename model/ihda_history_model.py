#!/usr/bin/env python
from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui

from libs.domain import HistoryData
from libs.path_updates import PathMoves, relocated_path

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 11:45
# modify date       :
# description       :
from model.model_style import ModelStyleMixin

with contextlib.suppress(ImportError):
    pass

import public
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
        pixmap_hist_thumb_data: dict[int, QtGui.QPixmap] | None = None,
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
        self.__pixmap_cate_data = (
            pixmap_cate_data if pixmap_cate_data is not None else {}
        )
        self.__pixmap_hist_thumb_data = (
            pixmap_hist_thumb_data if pixmap_hist_thumb_data is not None else {}
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
        self.__headers = [
            "ID",
            "Name",
            "Definition",
            "Category",
            "Comment",
            "Version",
            "Date Time",
            "Type",
            "Node Path",
            "Houdini",
            "License",
            "OS",
            "HIP Folder",
            "HIP File",
        ]
        self.__keys = [
            public.Key.History.hist_id,
            public.Key.History.org_hda_name,
            public.Key.History.node_def_desc,
            public.Key.History.node_category,
            public.Key.History.comment,
            public.Key.History.version,
            public.Key.History.reg_time,
            public.Key.History.node_type_name,
            public.Key.History.node_old_path,
            public.Key.History.hou_version,
            public.Key.History.hda_license,
            public.Key.History.os,
            public.Key.History.hip_dirpath,
            public.Key.History.hip_filename,
        ]
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

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return f"{self.__headers[section]}"
            else:
                return f"Hist {section + 1}"
        if role == QtCore.Qt.ItemDataRole.FontRole:
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

    def set_row_col_in_item(self, row: int) -> None:
        self.__items[row][public.Key.History.item_row] = row

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
            val = data.get(self.__keys[column])
            if column == self.__hda_dirpath_column:
                return val.as_posix()
            return val
        # elif role == QtCore.Qt.ItemDataRole.EditRole:
        #     return val
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            other_icon_size = self.__icon_size * 0.7
            if column == self.__hda_name_column:
                hist_id = data.get(public.Key.History.hist_id)
                thumb_pixmap = self.__pixmap_hist_thumb_data.get(hist_id)
                if thumb_pixmap is None:
                    return QtGui.QPixmap(":/main/icons/no_img_available.png")
                if thumb_pixmap.isNull():
                    thumb_dirpath = data.get(public.Key.History.thumb_dirpath)
                    if thumb_dirpath is None:
                        thumb_pixmap = QtGui.QPixmap(
                            ":/main/icons/no_img_available.png"
                        )
                    else:
                        thumb_filepath = thumb_dirpath / data.get(
                            public.Key.History.thumb_filename
                        )
                        if not thumb_filepath.exists():
                            thumb_pixmap = QtGui.QPixmap(
                                ":/main/icons/no_img_available.png"
                            )
                        else:
                            thumb_pixmap = QtGui.QPixmap(str(thumb_filepath))
                        self.__pixmap_hist_thumb_data.update({hist_id: thumb_pixmap})
                return thumb_pixmap.scaled(
                    QtCore.QSize(self.__thumb_size, self.__thumb_size),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == self.__hda_def_column:
                icon_pixmap = self.__pixmap_ihda_data.get(
                    data.get(public.Key.History.hda_id)
                )
                if icon_pixmap is None:
                    return None
                return icon_pixmap.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == self.__hda_cate_column:
                hda_cate = data.get(public.Key.History.node_category)
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
            if column in [1, 2, 3, 4, 8, 12, 13, 14]:
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
            hda_dirpath = data.get(public.Key.History.ihda_dirpath)
            if hda_dirpath is None:
                font.setItalic(True)
                font.setStrikeOut(True)
            else:
                hda_filepath = hda_dirpath / data.get(public.Key.History.ihda_filename)
                if not hda_filepath.exists() and not index.data(
                    HistoryModel.data_role
                ).get("remote", False):
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
        flags = super().flags(index)
        if index.isValid():
            hda_filepath = index.data(HistoryModel.filepath_role)
            if not hda_filepath.exists() and not index.data(HistoryModel.data_role).get(
                "remote", False
            ):
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

    def relocate_asset_paths(
        self, asset_id: int, moves: PathMoves
    ) -> list[HistoryData]:
        changed = []
        for row, item in enumerate(self.__items):
            if item.get("hda_id") != asset_id:
                continue
            for directory_key, filename_key in (
                ("ihda_dirpath", "ihda_filename"),
                ("thumb_dirpath", "thumb_filename"),
                ("video_dirpath", "video_filename"),
            ):
                directory, filename = item.get(directory_key), item.get(filename_key)
                if directory is not None and filename is not None:
                    path = relocated_path(Path(directory) / filename, moves)
                    item[directory_key], item[filename_key] = path.parent, path.name
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
        self.__items[row][key] = val
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
            data_row = hist_data.get(public.Key.History.item_row)
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
                if index.data(HistoryModel.version_role) == version:
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
    def get_hist_id_row_map_from_model(self) -> dict[str, Any]:
        map_lst = []
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            map_lst.append((index.data(HistoryModel.hist_id_role), row))
        return dict(map_lst)

    # history 모델에서 hist_id와 같은 item row를 반환
    def get_hist_item_row_by_hist_id_from_model(
        self, hist_id: int | None = None
    ) -> int | None:
        for row in range(0, self.rowCount()):
            index = self.index(row, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if hist_id == index.data(HistoryModel.hist_id_role):
                return row
        return None

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
        mime_data = super().mimeData(indexes)
        # 원래 2번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[public.Value.drag_column_history_view]]
        for index in indexes:
            if index.isValid():
                data = encode_payload(self.data(index, role=HistoryModel.data_role))
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
