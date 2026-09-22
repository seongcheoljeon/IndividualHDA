#!/usr/bin/env python
from __future__ import annotations

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.05.14 01:55
# modify date       :
# description       :
from collections.abc import Sequence
from typing import Any, overload

from PySide6 import QtCore, QtGui

from libs import keys
from libs.model_columns import InsideColumn
from libs.scene_scan import ScannedNode
from libs.ui_icons import Icon
from model.model_style import UNHANDLED, ModelStyleMixin, header_data
from model.tree_nodes import Node


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
        nodes: Sequence[ScannedNode] = (),
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
        self.__nodes: tuple[ScannedNode, ...] = tuple(nodes)
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
        scene = NodeData(
            node_name=keys.Type.root,
            node_type=keys.Type.root,
            node_depth=0,
            icon=self.__pixmap_cate_data.get(keys.Type.root),
            parent=self.__root,
        )
        self.__add_scanned(self.__nodes, depth=1, parent=scene)

    def __add_scanned(
        self, nodes: Sequence[ScannedNode], depth: int, parent: NodeData
    ) -> None:
        """Mirror the scanned Houdini hierarchy; icons come from the shared caches."""
        for scanned in sorted(nodes, key=lambda item: item.name):
            mark = scanned.mark
            if mark is not None:
                node_type = keys.Type.ihda
                display = f"{scanned.name} (v{mark.version})"
                icon = self.__pixmap_ihda_data.get(mark.hda_id) or self.__houdini_icon(
                    scanned.icon_paths
                )
            else:
                display = scanned.name
                node_type = (
                    "manager"
                    if scanned.category == keys.Type.manager
                    else scanned.type_name
                )
                icon = (
                    self.__pixmap_cate_data.get(scanned.icon_paths[1])
                    if len(scanned.icon_paths) > 1
                    else None
                ) or self.__houdini_icon(scanned.icon_paths)
            icon_cate: QtGui.QPixmap | None
            if mark is None and scanned.category == keys.Type.manager:
                icon_cate = self.__generic_pixmap
            else:
                icon_cate = self.__pixmap_cate_data.get(
                    scanned.category
                ) or self.__category_icon(scanned.category)
            node = NodeData(
                node_name=display,
                node_type=node_type,
                icon=icon,
                icon_cate=icon_cate,
                node_depth=depth,
                category=scanned.category,
                node_descript=scanned.description,
                version=mark.version if mark else None,
                hda_id=mark.hda_id if mark else None,
                node_path=scanned.path,
                created_time=scanned.created,
                modified_time=scanned.modified,
                hda_org_name=mark.name if mark else None,
                parent=parent,
            )
            self.__add_scanned(scanned.children, depth=depth + 1, parent=node)

    def __houdini_icon(self, icon_paths: Sequence[str]) -> QtGui.QPixmap | None:
        if self.__inst_ihda_icon is None:
            return self.__generic_pixmap
        return self.__inst_ihda_icon.get_houdini_icon(icon_lst=list(icon_paths) or None)

    def __category_icon(self, category: str) -> QtGui.QPixmap | None:
        if self.__inst_ihda_icon is None:
            return self.__generic_pixmap
        return self.__inst_ihda_icon.get_category_icon(category=category)

    @property
    def scanned(self) -> tuple[ScannedNode, ...]:
        return self.__nodes

    def make_node_tree(self, nodes: Sequence[ScannedNode] = ()) -> None:
        """Replace the tree with a new scan result."""
        self.beginResetModel()
        self.__nodes = tuple(nodes)
        self.__init_set_data()
        self.endResetModel()

    # [[name, hda_id, node_path], ...] for the filter combobox, one per asset.
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

    def set_icon_size(self, val: Any) -> None:
        self.beginResetModel()
        self.__icon_size = val
        self.endResetModel()

    def clear_item(self) -> None:
        self.make_node_tree(())

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
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return int(
                QtCore.Qt.AlignmentFlag.AlignHCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        value = header_data(InsideColumn, section, orientation, role)
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
                return node.node_path() or node.name()
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
