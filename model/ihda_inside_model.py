#!/usr/bin/env python
from __future__ import annotations

import contextlib

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.05.14 01:55
# modify date       :
# description       :
from operator import itemgetter
from typing import Any, overload

from PySide6 import QtCore, QtGui

from libs.model_columns import InsideColumn
from model.model_style import ModelStyleMixin
from model.tree_nodes import Node

with contextlib.suppress(ImportError):
    pass

import contextlib

from libs import houdini_api, keys


class NodeData(Node):
    def __init__(
        self,
        node_name: str | None = None,
        node_type: str | None = None,
        icon: QtGui.QPixmap | None = None,
        icon_cate: QtGui.QPixmap | None = None,
        category: str | None = None,
        node_depth: int | None = None,
        version: str | None = None,
        hda_id: int | None = None,
        node_descript: str | None = None,
        created_time: Any = None,
        modified_time: Any = None,
        hda_org_name: str | None = None,
        node_path: str | None = None,
        parent: Node | None = None,
    ) -> None:
        super().__init__(node_name=node_name, node_depth=node_depth, parent=parent)
        self.__node_type = node_type
        self.__node_descript = node_descript
        self.__node_path = node_path
        self.__icon = icon
        self.__icon_cate = icon_cate
        self.__category = category
        self.__version = version
        self.__hda_id = hda_id
        self.__created_time = created_time
        self.__modified_time = modified_time
        self.__hda_org_name = hda_org_name

    def node_type(self) -> str | None:
        return self.__node_type

    def node_descript(self) -> str | None:
        return self.__node_descript

    def node_path(self) -> str | None:
        return self.__node_path

    def icon(self) -> QtGui.QPixmap | None:
        return self.__icon if self.__icon is not None else None

    def icon_cate(self) -> QtGui.QPixmap | None:
        return self.__icon_cate if self.__icon_cate is not None else None

    def category(self) -> str | None:
        return self.__category

    def version(self) -> str | None:
        return self.__version

    def hda_id(self) -> int | None:
        return self.__hda_id

    def created_time(self) -> Any:
        return self.__created_time

    def modified_time(self) -> Any:
        return self.__modified_time

    def hda_org_name(self) -> Any:
        return self.__hda_org_name


class InsideModel(QtCore.QAbstractItemModel, ModelStyleMixin):
    hda_id_role = QtCore.Qt.ItemDataRole.UserRole
    hda_org_name_role = QtCore.Qt.ItemDataRole.UserRole + 1
    node_path_role = QtCore.Qt.ItemDataRole.UserRole + 2
    name_role = QtCore.Qt.ItemDataRole.UserRole + 3
    depth_role = QtCore.Qt.ItemDataRole.UserRole + 4
    node_type_role = QtCore.Qt.ItemDataRole.UserRole + 5
    version_role = QtCore.Qt.ItemDataRole.UserRole + 6

    def __init__(
        self,
        data: Any = None,
        pixmap_cate_data: dict[str, QtGui.QPixmap] | None = None,
        pixmap_ihda_data: dict[int, QtGui.QPixmap] | None = None,
        inst_ihda_icon: Any = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        padding: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.__data = self.__default_data
        self.__update_data(data=data)
        self.__pixmap_cate_data = (
            pixmap_cate_data if pixmap_cate_data is not None else {}
        )
        self.__pixmap_ihda_data = (
            pixmap_ihda_data if pixmap_ihda_data is not None else {}
        )
        self.__inst_ihda_icon = inst_ihda_icon
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
        self.__generic_pixmap = QtGui.QPixmap(":/main/icons/generic.png")
        self.__init_set_data()

    def __init_set_data(self) -> None:
        self.__root = NodeData(node_name=keys.Type.root, node_depth=0, parent=None)
        root_pixmap = self.__pixmap_cate_data.get(keys.Type.root)

        if self.__data is not None:
            for root_key, root_val in sorted(
                iter(self.__data.items()), key=itemgetter(0)
            ):
                parent_node = NodeData(
                    node_name=root_key,
                    node_type=keys.Type.root,
                    node_depth=0,
                    icon=root_pixmap,
                    parent=self.__root,
                )
                self.set_treemodel_data(
                    data=root_val, root_type=root_key, depth=1, parent=parent_node
                )

    #               0           1       2           3           4       5       6          7            8
    # LIST DATA: [inside_id, hda_id, node_name, node_type, node_cate, ctime, mtime, hip_dirpath, hip_filename,
    #          9            10
    #    hda_dirpath, hda_filename
    # ]
    def set_treemodel_data(
        self,
        data: Any = None,
        root_type: Any = None,
        depth: int = 1,
        parent: NodeData | None = None,
    ) -> None:
        if isinstance(data, dict):
            for key, val in data.items():
                node_name = key.name()
                node_path = key.path()
                node_cate = houdini_api.HoudiniAPI.node_category_type_name(key)
                hda_info = houdini_api.HoudiniAPI.get_hda_info_by_selection_node(
                    node=key
                )
                node_descript = houdini_api.HoudiniAPI.node_definition_description(key)
                created_time, modified_time = houdini_api.HoudiniAPI.get_node_datetime(
                    key
                )
                created_time = created_time.strftime(keys.Value.datetime_fmt_str)
                modified_time = modified_time.strftime(keys.Value.datetime_fmt_str)
                if hda_info is not None:
                    hda_id = hda_info.get(keys.Key.Comment.ihda_id)
                    hda_ver = hda_info.get(keys.Key.Comment.ihda_version)
                    hda_org_name = hda_info.get(keys.Key.Comment.ihda_name)
                    node_name = f"{node_name} (v{hda_ver})"
                    node_type = keys.Type.ihda
                    icon = (
                        self.__pixmap_ihda_data.get(hda_id)
                        if hda_id is not None
                        else None
                    )
                    if icon is None:
                        icon = self.__inst_ihda_icon.get_houdini_icon(
                            icon_lst=houdini_api.HoudiniAPI.node_icon_path_lst(key)
                        )
                    # pixmap 공유 데이터 변수에 존재하지 않는다면 직접 가공해서 넣어준다.
                    icon_cate = self.__pixmap_cate_data.get(node_cate or "")
                    if icon_cate is None:
                        icon_cate = self.__inst_ihda_icon.get_category_icon(
                            category=node_cate
                        )
                else:
                    hda_id = None
                    hda_ver = None
                    hda_org_name = None
                    if node_cate == keys.Type.manager:
                        node_type = "manager"
                        icon_cate = self.__generic_pixmap
                    else:
                        node_type = houdini_api.HoudiniAPI.node_type_name(key) or ""
                        # pixmap 공유 데이터 변수에 존재하지 않는다면 직접 가공해서 넣어준다.
                        icon_cate = self.__pixmap_cate_data.get(node_cate or "")
                        if icon_cate is None:
                            icon_cate = self.__inst_ihda_icon.get_category_icon(
                                category=node_cate
                            )
                    icon_lst = houdini_api.HoudiniAPI.node_icon_path_lst(key)
                    icon = (
                        self.__pixmap_cate_data.get(icon_lst[1]) if icon_lst else None
                    )
                    if icon is None:
                        icon = self.__inst_ihda_icon.get_houdini_icon(icon_lst=icon_lst)
                node = NodeData(
                    node_name=node_name,
                    node_type=node_type,
                    icon=icon,
                    icon_cate=icon_cate,
                    node_depth=depth,
                    category=node_cate,
                    node_descript=node_descript,
                    version=hda_ver,
                    hda_id=hda_id,
                    node_path=node_path,
                    created_time=created_time,
                    modified_time=modified_time,
                    hda_org_name=hda_org_name,
                    parent=parent,
                )
                self.set_treemodel_data(
                    data=val, root_type=root_type, depth=depth + 1, parent=node
                )
        elif isinstance(data, list):
            if not len(data):
                return
            for val in sorted(data, key=itemgetter(2)):
                node = NodeData(
                    node_name=val,
                    node_type=keys.Type.ihda,
                    category="",
                    parent=parent,
                )
        else:
            pass

    @property
    def inside_data(self) -> Any:
        return self.__data

    @inside_data.setter
    def inside_data(self, val: Any) -> None:
        self.__update_data(val)

    @property
    def __default_data(self) -> dict[str, Any]:
        return {keys.Type.root: {}}

    def __update_data(self, data: Any = None) -> None:
        if data is None:
            return
        assert isinstance(data, dict)
        if (data is None) or (not len(data)):
            return
        self.__data[keys.Type.root].update(data)

    def make_node_tree(self, node_data: Any = None) -> None:
        self.beginResetModel()
        self.__data = self.__default_data
        self.inside_data = node_data
        self.__init_set_data()
        self.endResetModel()

    # build context 에서 선택한 아이템을 삭제할 때 호출하는 함수.
    # bhild context에서 제공하는 index로 삭제하려는 무한루프에 빠지면서 오류난다.
    # 그래서 선택한 노드를 재귀적으로 돌려 찾은 index로 삭제하는 방식으로 돌아간다.
    # 유효한 데이터가 남아 있지 않은 껍데기 뿐인 inside 데이터/모델 삭제하는 함수
    # 인자로 들어 온 key_data로 inside data가져오는 함수

    # 선택한 부모에 존재하는 모든 inside data의 id를 찾아 반환하는 함수
    # 이렇게 찾은 id를 DB에서 제거하기 위함.

    # hda_id를 가진 노드의 [[이름/hda_id/노드경로],]를 반환하는 함수
    def get_ihda_node_list(self) -> Any:
        root_index = self.index(0, 0, QtCore.QModelIndex())
        tmp_id_lst: list[int] = []
        return self.__find_inside_ihda_node(index=root_index, tmp_id_lst=tmp_id_lst)

    # tmp_id_lst는 데이터가 중복 저장되는 것을 방지하는 위한 임시 변수이다.
    def __find_inside_ihda_node(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex | None = None,
        tmp_id_lst: Any = None,
    ) -> list[Any]:
        if index is None:
            index = QtCore.QModelIndex()
        find_lst = []
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            hda_id = child_index.data(InsideModel.hda_id_role)
            if hda_id is not None and hda_id not in tmp_id_lst:
                hda_org_name = child_index.data(InsideModel.hda_org_name_role)
                node_path = child_index.data(InsideModel.node_path_role)
                find_lst.append([hda_org_name, hda_id, node_path])
                tmp_id_lst.append(hda_id)
            find_lst += self.__find_inside_ihda_node(
                index=child_index, tmp_id_lst=tmp_id_lst
            )
        return find_lst

    # key_date를 기준으로 아이템을 찾아들어가서 find_item을 찾고 리스트 반환

    # 유효하지 않는 데이터를 반환하는 함수. 껍데기만 존재하는 데이터
    # 이 함수로 반환된 데이터를 삭제한다. 선택하여 삭제하는 함수를 쓰면, 유효한 데이터가 하나도 존재 하지 않을 때
    # 그 껍데기를 삭제하는 용도이다.

    # 유효하지 않는 데이터가 존재하는지 확인하는 함수. 존재하지 않는다면 껍데기만 있는 데이터라 그 껍데기를 지우도록 확인한다.
    # 즉, 유효한 데이터가 존재하지 않는 최상위 부모를 찾는다.

    # 인자로 들어온 index의 부모들 이름을 구하는 함수. inside data를 현재는 이름을 가져오지만 차후에는 inside_id로
    # 변환해 이것으로 지워야 정확함. 현재 노드 이름과 버전이 공존하여 이것을 기반으로 삭제한다. 이름과 버전은 unique하기 때문.
    # ex) ['root', 'c:/users/scii', aaa.hip', '/obj/cam', 'bakeoedtest']

    # 모델 데이터와 inside 데이터를 제거하는 함수
    # 유효하지 않는 레코드 데이터, 모델 데이터 취합하는 함수의 랩퍼 함수

    # 유효하지 않는 레코드 데이터를 재귀적으로 찾는 함수

    # 해당 부모를 지워도 되는지 확인하는 함수. 자식 중 하나라도 유효한 데이터가 있다면 부모를 지울 수 없다.

    # hda_id와 같은 inside data 삭제 함수
    # iHDA 삭제 시, inside 데이터 삭제되도록 DB에서 Constraint 걸어 놓아서 여기서만 삭제하면 된다.
    # 해당 hda_id를 가진 자식의 부모가 자식이 하나라면 가장 끝 부모를 삭제해야하기 때문에 is_find_parent를 True로 주었다.
    # inside data 이름 변경 함수 (iHDA 파일 경로도 변경해야 함)
    # iHDA 이름 변경 시, inside 데이터도 함께 변경되어야 한다. DB는 트리거로 자동화 시켜 놓았다.
    # 정확하게 해당 데이터를 찾아가야해서 is_find_parent를 False로 주었다.
    # 여러 개의 inside data (중첩 된 딕셔너리&리스트 데이터)를 하나의 데이터로 만드는 함수

    # 인자로 들어온 hda_id를 가진 자식들이 존재하는지

    def add_item(self, data: Any = None) -> None:
        assert isinstance(data, dict)
        self.__update_data(data=data)

    def remove_item(self, category: str | None = None) -> None:
        del self.__data[keys.Type.root][category]

    def set_icon_size(self, val: Any) -> None:
        self.beginResetModel()
        self.__icon_size = val
        self.endResetModel()

    def clear_item(self) -> None:
        self.beginResetModel()
        self.__data = self.__default_data
        self.__init_set_data()
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
        return len(InsideColumn)

    def columnCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return len(InsideColumn)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return InsideColumn(section).label
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            return None
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            # font.setFamily(self._font_style)
            font.setPointSize(keys.UISetting.view_font_size)
            return font
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )

        return None

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
            if column > InsideColumn.CATEGORY:
                return int(
                    QtCore.Qt.AlignmentFlag.AlignHCenter
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.DisplayRole:
            return getattr(node, InsideColumn(column).field)()
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            if column == InsideColumn.NAME:
                return node.name()
            return None
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            if column == InsideColumn.NAME:
                icon = node.icon()
                if icon is None:
                    return None
                if node.node_type() == keys.Type.ihda:
                    return icon.scaled(
                        QtCore.QSize(int(self.__icon_size), int(self.__icon_size)),
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    )
                return icon.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column == InsideColumn.CATEGORY:
                icon = node.icon_cate()
                if icon is None:
                    return None
                return icon.scaled(
                    QtCore.QSize(
                        int(self.__icon_size * 0.8), int(self.__icon_size * 0.8)
                    ),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
            elif column in [InsideColumn.CREATED, InsideColumn.MODIFIED]:
                if (node.created_time() is None) or (node.modified_time() is None):
                    return None
                else:
                    pixmap = QtGui.QPixmap(":/main/icons/ic_query_builder_white.png")
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
            return font
        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(
                int(self.__icon_size), int(self.__icon_size + self._padding)
            )
        elif role == QtCore.Qt.ItemDataRole.BackgroundRole:
            return None
        # UserRole
        elif role == InsideModel.hda_id_role:
            return node.hda_id()
        elif role == InsideModel.hda_org_name_role:
            return node.hda_org_name()
        elif role == InsideModel.node_path_role:
            return node.node_path()
        elif role == InsideModel.name_role:
            return node.name()
        elif role == InsideModel.depth_role:
            return node.depth()
        elif role == InsideModel.node_type_role:
            return node.node_type()
        elif role == InsideModel.version_role:
            return node.version()

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
