#!/usr/bin/env python
from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Sequence
from dataclasses import replace

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.05.14 01:55
# modify date       :
# description       :
from operator import itemgetter
from typing import Any, overload

from PySide6 import QtCore, QtGui

from libs.item_paths import item_path
from libs.model_columns import RecordColumn
from libs.scene_contracts import SceneRecord
from libs.ui_icons import Icon
from model.model_style import UNHANDLED, ModelStyleMixin, header_data
from model.tree_nodes import Node

with contextlib.suppress(ImportError):
    pass

import contextlib

from libs import keys
from libs.drag_payload import encode_payload


class NodeData(Node):
    def __init__(
        self,
        node_name: str | None = None,
        node_type: str | None = None,
        icon: QtGui.QPixmap | None = None,
        hip_dirpath: pathlib.Path | None = None,
        hip_filename: str | None = None,
        category: str | None = None,
        ctime: Any = None,
        mtime: Any = None,
        record_id: int | None = None,
        hda_id: int | None = None,
        node_depth: int | None = None,
        node_ver: str | None = None,
        hda_dirpath: pathlib.Path | None = None,
        hda_filename: str | None = None,
        record_data: SceneRecord | None = None,
        pnode_path: str | None = None,
        parent: Node | None = None,
    ) -> None:
        super().__init__(node_name=node_name, node_depth=node_depth, parent=parent)
        self.__node_type = node_type
        self.__icon = icon
        self.__hip_dirpath = hip_dirpath
        self.__hip_filename = hip_filename
        self.__hip_filepath = item_path(hip_dirpath, hip_filename)
        self.__hda_dirpath = hda_dirpath
        self.__hda_filename = hda_filename
        self.__hda_filepath = item_path(hda_dirpath, hda_filename)
        self.__category = category
        self.__ctime = ctime
        self.__mtime = mtime
        self.__record_id = record_id
        self.__hda_id = hda_id
        self.__hda_ver = node_ver
        self.__record_data = record_data
        self.__pnode_path = pnode_path

    @property
    def node_type(self) -> str | None:
        return self.__node_type

    @property
    def icon(self) -> QtGui.QPixmap | None:
        return self.__icon if self.__icon is not None else None

    @property
    def hip_dirpath(self) -> pathlib.Path | None:
        return self.__hip_dirpath

    @property
    def hip_filename(self) -> str | None:
        return self.__hip_filename

    @property
    def hip_filepath(self) -> pathlib.Path | None:
        return self.__hip_filepath

    @property
    def hda_dirpath(self) -> pathlib.Path | None:
        return self.__hda_dirpath

    @property
    def hda_filename(self) -> str | None:
        return self.__hda_filename

    @property
    def hda_filepath(self) -> pathlib.Path | None:
        return self.__hda_filepath

    @property
    def category(self) -> str | None:
        return self.__category

    @property
    def record_id(self) -> int | None:
        return self.__record_id

    @property
    def hda_id(self) -> int | None:
        return self.__hda_id

    @property
    def version(self) -> str | None:
        return self.__hda_ver

    @property
    def ctime(self) -> Any:
        return self.__ctime

    @property
    def mtime(self) -> Any:
        return self.__mtime

    @property
    def record_data(self) -> SceneRecord | None:
        return self.__record_data

    @property
    def pnode_path(self) -> Any:
        return self.__pnode_path


class RecordModel(QtCore.QAbstractItemModel, ModelStyleMixin):
    record_id_role = QtCore.Qt.ItemDataRole.UserRole
    hda_id_role = QtCore.Qt.ItemDataRole.UserRole + 1
    name_role = QtCore.Qt.ItemDataRole.UserRole + 2
    depth_role = QtCore.Qt.ItemDataRole.UserRole + 3
    hip_dirpath_role = QtCore.Qt.ItemDataRole.UserRole + 4
    hip_filepath_role = QtCore.Qt.ItemDataRole.UserRole + 5
    hda_filepath_role = QtCore.Qt.ItemDataRole.UserRole + 6
    record_type_role = QtCore.Qt.ItemDataRole.UserRole + 7
    is_record_type_role = QtCore.Qt.ItemDataRole.UserRole + 8
    record_data_role = QtCore.Qt.ItemDataRole.UserRole + 9
    pnode_path_role = QtCore.Qt.ItemDataRole.UserRole + 10

    def __init__(
        self,
        data: Any = None,
        pixmap_cate_data: dict[str, QtGui.QPixmap] | None = None,
        pixmap_ihda_data: dict[int, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        padding: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._records = {record.record_id: record for record in (data or ())}
        self.__pixmap_cate_data = (
            pixmap_cate_data if pixmap_cate_data is not None else {}
        )
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
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
        self._padding = padding if padding is not None else 0
        self.__root: NodeData
        self.__network_pixmap = QtGui.QPixmap(":/main/icons/layer.png")
        self.__folder_pixmap = QtGui.QPixmap(":/main/icons/folder_open.png")
        self.__file_pixmap = QtGui.QPixmap(":/main/icons/houdini_logo.png")
        self.__init_set_data()

    def __init_set_data(self) -> None:
        self.__root = NodeData(
            node_name=keys.Type.root, node_type="", node_depth=0, parent=None
        )
        root_pixmap = self.__pixmap_cate_data.get(keys.Type.root)

        grouped: dict[str, Any] = {}
        for record in self._records.values():
            directory = str(record.hip_dirpath or "")
            grouped.setdefault(directory, {}).setdefault(
                record.hip_filename or "", {}
            ).setdefault(record.parent_node_path, []).append(record)
        parent_node = NodeData(
            node_name=keys.Type.root,
            node_type=keys.Type.root,
            node_depth=0,
            icon=root_pixmap,
            parent=self.__root,
        )
        self.set_treemodel_data(
            data=grouped, root_type=keys.Type.root, depth=1, parent=parent_node
        )

    def set_treemodel_data(
        self,
        data: Any = None,
        root_type: Any = None,
        depth: int = 1,
        parent: NodeData | None = None,
    ) -> None:
        if parent is None:
            parent = self.__root
        if isinstance(data, dict):
            if depth == 1:
                item_pixmap = self.__folder_pixmap
                item_type = keys.Type.folder
            elif depth == 2:
                item_pixmap = self.__file_pixmap
                item_type = keys.Type.file
            else:
                item_pixmap = self.__network_pixmap
                item_type = keys.Type.network
            for key, val in sorted(iter(data.items()), key=itemgetter(0)):
                if depth == 1:
                    dirpath: pathlib.Path | None = pathlib.Path(key)
                    filename = None
                    pnode_path = None
                elif depth == 2:
                    dirpath = parent.hip_dirpath
                    filename = key
                    pnode_path = None
                    assert isinstance(dirpath, pathlib.Path)
                else:
                    dirpath = parent.hip_dirpath
                    filename = parent.hip_filename
                    pnode_path = key
                    assert isinstance(dirpath, pathlib.Path)
                node = NodeData(
                    node_name=key,
                    node_type=item_type,
                    icon=item_pixmap,
                    hip_dirpath=dirpath,
                    hip_filename=filename,
                    node_depth=depth,
                    pnode_path=pnode_path,
                    parent=parent,
                )
                self.set_treemodel_data(
                    data=val, root_type=root_type, depth=depth + 1, parent=node
                )
        elif isinstance(data, list):
            if not len(data):
                return
            for rdata in sorted(data, key=lambda record: record.node_name):
                record_id = rdata.record_id
                hda_id = rdata.hda_id
                node_name = f"{rdata.node_name} (v{rdata.node_ver})"
                node_cate = rdata.node_cate
                node_ver = rdata.node_ver
                ctime = rdata.ctime
                mtime = rdata.mtime
                hip_dpath = rdata.hip_dirpath
                hip_fname = rdata.hip_filename
                hda_dpath = rdata.hda_dirpath
                hda_fname = rdata.hda_filename
                pixmap_ihda = (
                    self.__pixmap_ihda_data.get(hda_id) if hda_id is not None else None
                )
                # hda_id 리스트
                node = NodeData(
                    node_name=node_name,
                    node_type=keys.Type.ihda,
                    category=node_cate,
                    ctime=ctime,
                    mtime=mtime,
                    icon=pixmap_ihda,
                    record_id=record_id,
                    hda_id=hda_id,
                    hip_dirpath=hip_dpath,
                    hip_filename=hip_fname,
                    hda_dirpath=hda_dpath,
                    hda_filename=hda_fname,
                    node_depth=depth,
                    node_ver=node_ver,
                    record_data=rdata,
                    pnode_path=parent.pnode_path,
                    parent=parent,
                )
        else:
            pass

    @property
    def record_data(self) -> tuple[SceneRecord, ...]:
        return tuple(self._records.values())

    def replace_record_data(self, data: Sequence[SceneRecord]) -> None:
        self._records = {record.record_id: record for record in data}
        self.reload()

    def insert_record_data(self, data: SceneRecord) -> None:
        self._records[data.record_id] = data

    def remove_record_ids(self, identities: Sequence[int]) -> None:
        for identity in identities:
            self._records.pop(identity, None)
        self.reload()

    def remove_record_item_by_hda_id(self, hda_id: int | None = None) -> None:
        self.remove_record_ids(
            tuple(
                record.record_id
                for record in self._records.values()
                if record.hda_id == hda_id
            )
        )

    def rename_record_item(
        self,
        *,
        hda_id: int,
        new_name: str,
        hda_dirpath: pathlib.Path,
        hda_version: str,
        hda_filename: str,
    ) -> None:
        for identity, record in tuple(self._records.items()):
            if record.hda_id == hda_id:
                self._records[identity] = replace(
                    record,
                    node_name=new_name,
                    hda_dirpath=hda_dirpath,
                    hda_filename=hda_filename
                    if record.node_ver == hda_version
                    else record.hda_filename,
                )

    def clear_item(self) -> None:
        self.replace_record_data(())

    def reload(self) -> None:
        self.beginResetModel()
        try:
            self.__init_set_data()
        finally:
            self.endResetModel()

    # build context 에서 선택한 아이템을 삭제할 때 호출하는 함수.
    # bhild context에서 제공하는 index로 삭제하려는 무한루프에 빠지면서 오류난다.
    # 그래서 선택한 노드를 재귀적으로 돌려 찾은 index로 삭제하는 방식으로 돌아간다.
    def selected_record_ids(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> tuple[int, ...]:
        if not index.isValid():
            return ()
        source = index.model()
        while isinstance(source, QtCore.QAbstractProxyModel):
            index = source.mapToSource(index)
            source = index.model()
        if index.model() is not self:
            return ()
        identities: set[int] = set()

        def collect(parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> None:
            identity = parent.data(self.record_id_role)
            if identity is not None:
                identities.add(int(identity))
            for row in range(self.rowCount(parent)):
                collect(self.index(row, 0, parent))

        collect(index)
        return tuple(sorted(identities))

    # 유효한 데이터가 남아 있지 않은 껍데기 뿐인 record 데이터/모델 삭제하는 함수

    # 인자로 들어 온 key_data로 record data가져오는 함수

    # 선택한 부모에 존재하는 모든 record data의 id를 찾아 반환하는 함수
    # 이렇게 찾은 id를 DB에서 제거하기 위함.

    # key_date를 기준으로 아이템을 찾아들어가서 find_item을 찾고 리스트 반환

    # 유효하지 않는 데이터를 반환하는 함수. 껍데기만 존재하는 데이터
    # 이 함수로 반환된 데이터를 삭제한다. 선택하여 삭제하는 함수를 쓰면, 유효한 데이터가 하나도 존재 하지 않을 때
    # 그 껍데기를 삭제하는 용도이다.

    # 유효하지 않는 데이터가 존재하는지 확인하는 함수. 존재하지 않는다면 껍데기만 있는 데이터라 그 껍데기를 지우도록 확인한다.
    # 즉, 유효한 데이터가 존재하지 않는 최상위 부모를 찾는다.

    # 인자로 들어온 index의 부모들 이름을 구하는 함수. record data를 현재는 이름을 가져오지만 차후에는 record_id로
    # 변환해 이것으로 지워야 정확함. 현재 노드 이름과 버전이 공존하여 이것을 기반으로 삭제한다. 이름과 버전은 unique하기 때문.
    # ex) ['root', 'c:/users/scii', aaa.hip', '/obj/cam', 'bakeoedtest']

    # 모델 데이터와 record 데이터를 제거하는 함수

    # 유효하지 않는 레코드 데이터, 모델 데이터 취합하는 함수의 랩퍼 함수

    # 유효하지 않는 레코드 데이터를 재귀적으로 찾는 함수

    # 해당 부모를 지워도 되는지 확인하는 함수. 자식 중 하나라도 유효한 데이터가 있다면 부모를 지울 수 없다.

    # hda_id와 같은 record data 삭제 함수
    # iHDA 삭제 시, record 데이터 삭제되도록 DB에서 Constraint 걸어 놓아서 여기서만 삭제하면 된다.
    # 해당 hda_id를 가진 자식의 부모가 자식이 하나라면 가장 끝 부모를 삭제해야하기 때문에 is_find_parent를 True로 주었다.

    # record data 이름 변경 함수 (iHDA 파일 경로도 변경해야 함)
    # iHDA 이름 변경 시, record 데이터도 함께 변경되어야 한다. DB는 트리거로 자동화 시켜 놓았다.
    # 정확하게 해당 데이터를 찾아가야해서 is_find_parent를 False로 주었다.

    # 여러 개의 record data (중첩 된 딕셔너리&리스트 데이터)를 하나의 데이터로 만드는 함수

    # 인자로 들어온 hda_id를 가진 자식들이 존재하는지

    def set_icon_size(self, val: Any) -> None:
        self.beginResetModel()
        self.__icon_size = val
        self.endResetModel()

    def flags(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsDropEnabled
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        # if index.isValid():
        #     flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
        #     flags |= QtCore.Qt.ItemFlag.ItemIsEnabled
        #     flags |= QtCore.Qt.ItemFlag.ItemIsDragEnabled
        #     flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
        # else:
        #     flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled
        # return flags

    @property
    def headers_count(self) -> int:
        return len(RecordColumn)

    def columnCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return len(RecordColumn)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        value = header_data(RecordColumn, section, orientation, role)
        return None if value is UNHANDLED else value

    def node_from_index(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> NodeData:
        return index.internalPointer() if index.isValid() else self.__root

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
        # Tree rows require domain data; add_item/reload performs real insertion.
        return False

    def delete_node(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> None:
        if index.isValid() and index.model() is self:
            self.removeRows(index.row(), 1, index.parent())

    def removeRow(
        self,
        row: int,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> bool:
        return self.removeRows(row, 1, parent)

    def removeRows(
        self,
        row: int,
        count: int,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> bool:
        if parent.isValid() and (parent.model() is not self or parent.column() != 0):
            return False
        if count <= 0 or row < 0 or row + count > self.rowCount(parent):
            return False
        node = self.node_from_index(parent)
        self.beginRemoveRows(parent, row, row + count - 1)
        for _ in range(count):
            node.remove_child(row)
        self.endRemoveRows()
        return True

    def index(
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None
        node = self.node_from_index(index)
        column = index.column()
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if column > RecordColumn.CATEGORY:
                return int(
                    QtCore.Qt.AlignmentFlag.AlignHCenter
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.DisplayRole:
            descriptor = RecordColumn(column)
            if descriptor is RecordColumn.NAME:
                return node.name()
            if descriptor in (
                RecordColumn.TYPE,
                RecordColumn.CATEGORY,
                RecordColumn.VERSION,
                RecordColumn.CREATED,
                RecordColumn.MODIFIED,
            ):
                return getattr(node, descriptor.field)
            return (
                getattr(node.record_data, descriptor.field)
                if node.record_data is not None
                else None
            )
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            if column == RecordColumn.NAME:
                return node.name()
            return None
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            if node.icon is None:
                return None
            elif column == RecordColumn.NAME:
                if node.node_type == keys.Type.ihda:
                    return node.icon.scaled(
                        QtCore.QSize(int(self.__icon_size), int(self.__icon_size)),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
                return node.icon.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == RecordColumn.CATEGORY:
                pixmap = self.__pixmap_cate_data.get(node.category or "")
                if pixmap is None:
                    return None
                return pixmap.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column in [RecordColumn.CREATED, RecordColumn.MODIFIED]:
                if (node.ctime is None) or (node.mtime is None):
                    return None
                else:
                    pixmap = QtGui.QPixmap(Icon.IC_QUERY_BUILDER_WHITE)
                return pixmap.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.7), int(self.__icon_size * 0.7)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            return None
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self._font_style)
            font.setPointSize(self._font_size)
            if node.hip_dirpath is not None:
                if not node.hip_dirpath.exists():
                    font.setItalic(True)
                    font.setStrikeOut(True)
                else:
                    if node.hip_filepath is not None:
                        if not node.hip_filepath.exists():
                            font.setItalic(True)
                            font.setStrikeOut(True)
                        else:
                            if node.hda_filepath is not None:
                                if not node.hda_filepath.exists():
                                    font.setItalic(True)
                                    font.setStrikeOut(True)
            return font
        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(
                int(self.__icon_size), int(self.__icon_size + self._padding)
            )
        elif role == QtCore.Qt.ItemDataRole.BackgroundRole:
            if node.hip_dirpath is None:
                return None
            depth_val = ((node.depth() - 1) * 2) + 1
            color = QtGui.QColor(
                int(240.0 / depth_val), int(81.0 / depth_val), int(49.0 / depth_val)
            )
            if not node.hip_dirpath.exists():
                return color
            else:
                if node.hip_filepath is None:
                    return None
                if not node.hip_filepath.exists():
                    return color
                else:
                    if node.hda_filepath is None:
                        return None
                    if not node.hda_filepath.exists():
                        return color
        elif role == RecordModel.record_id_role:
            return node.record_id
        elif role == RecordModel.hda_id_role:
            return node.hda_id
        elif role == RecordModel.name_role:
            return node.name()
        elif role == RecordModel.depth_role:
            return node.depth()
        elif role == RecordModel.hip_dirpath_role:
            return node.hip_dirpath
        elif role == RecordModel.hip_filepath_role:
            return node.hip_filepath
        elif role == RecordModel.hda_filepath_role:
            return node.hda_filepath
        elif role == RecordModel.record_type_role:
            return node.node_type
        elif role == RecordModel.is_record_type_role:
            return node.node_type == keys.Type.ihda
        elif role == RecordModel.record_data_role:
            return node.record_data
        elif role == RecordModel.pnode_path_role:
            return node.pnode_path

    def rowCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        if parent.isValid() and parent.column() != 0:
            return 0
        node = self.node_from_index(parent)
        if node is None:
            return 0
        return len(node)

    @overload
    def parent(self) -> QtCore.QObject | None: ...

    @overload
    def parent(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> QtCore.QModelIndex: ...

    def parent(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex | None = None,
    ) -> QtCore.QModelIndex | QtCore.QObject | None:
        if index is None:
            return super().parent()
        if not index.isValid():
            return QtCore.QModelIndex()
        node = self.node_from_index(index)
        if node is None:
            return QtCore.QModelIndex()
        parent = node.parent()
        if parent is None:
            return QtCore.QModelIndex()
        grand_parent = parent.parent()
        if grand_parent is None:
            return QtCore.QModelIndex()
        row = grand_parent.row_of_child(parent)
        assert row != -1
        return self.createIndex(row, 0, parent)

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
            indexes = [indexes[keys.Value.drag_column_record_view]]
        for index in indexes:
            if index.isValid():
                data = encode_payload(
                    self.data(index, role=RecordModel.record_data_role)
                )
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
        return True
