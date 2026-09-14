#!/usr/bin/env python
from __future__ import annotations

from typing import Any
from PySide6 import QtCore

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:55
# modify date       :
# description       :


from PySide6 import QtGui

try:
    import hou
except ImportError as err:
    pass

import public


class Node(QtCore.QObject):
    def __init__(
        self,
        node_name: str | None = None,
        node_depth: int | None = None,
        parent: Node | None = None,
    ) -> None:
        super(Node, self).__init__()
        self.__name = node_name
        self.__depth = node_depth
        self.__parent = parent
        self.__children = list()
        self.setParent(parent)

    @property
    def name(self) -> str | None:
        return self.__name

    @property
    def depth(self) -> int | None:
        return self.__depth

    @property
    def parent(self) -> Node | None:
        return self.__parent

    def setParent(self, parent: Node | None) -> None:
        if parent is not None:
            self.__parent = parent
            self.__parent.append_child(self)
        else:
            self.__parent = None

    def append_child(self, child: Node) -> None:
        self.__children.append(child)

    def child_at_row(self, row: int) -> Node:
        return self.__children[row]

    def row_of_child(self, child: Node) -> int:
        for idx, item in enumerate(self.__children):
            if child == item:
                return idx
        return -1

    def remove_child(self, row: int) -> bool:
        value = self.__children[row]
        self.__children.remove(value)
        return True

    def __len__(self) -> int:
        return len(self.__children)


class NodeData(Node):
    def __init__(
        self,
        node_name: str | None = None,
        node_type: str | None = None,
        icon: QtGui.QPixmap | None = None,
        node_depth: int | None = None,
        parent: Node | None = None,
    ) -> None:
        super(NodeData, self).__init__(
            node_name=node_name, node_depth=node_depth, parent=parent
        )
        self.__node_type = node_type
        self.__icon = icon

    @property
    def node_type(self) -> str | None:
        return self.__node_type

    @property
    def icon(self) -> QtGui.QPixmap | None:
        return self.__icon if self.__icon is not None else None


class CategoryModel(QtCore.QAbstractItemModel):
    category_role = QtCore.Qt.ItemDataRole.UserRole
    type_role = QtCore.Qt.ItemDataRole.UserRole + 1
    depth_role = QtCore.Qt.ItemDataRole.UserRole + 2

    def __init__(
        self,
        data: Any = None,
        pixmap_cate_data: dict[str, QtGui.QPixmap] | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        icon_size: int | None = None,
        padding: int | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super(CategoryModel, self).__init__(parent)
        self.__data = self.__default_data
        self.__pixmap_cate_data = (
            pixmap_cate_data if pixmap_cate_data is not None else {}
        )
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
        self.__padding = padding if padding is not None else 0
        self.__update_data(data=data)
        self.__headers = ("Network",)
        self.__root = None
        self.__init_set_data()

    def add_pixmap_cate_data(
        self, category: str | None = None, pixmap: QtGui.QPixmap | None = None
    ) -> None:
        if category not in self.__pixmap_cate_data:
            self.__pixmap_cate_data.update({category: pixmap})

    def remove_pixmap_cate_data(self, category: str | None = None) -> None:
        if category in self.__pixmap_cate_data:
            del self.__pixmap_cate_data[category]

    def __init_set_data(self) -> None:
        self.__root = NodeData(
            node_name=public.Type.root, node_type="", node_depth=0, parent=None
        )
        if self.__data is not None:
            self.__set_treemodel_data(data=self.__data, parent=self.__root)

    def __set_treemodel_data(
        self, data: Any = None, parent: QtCore.QModelIndex = None
    ) -> None:
        pixmap_cate_dat = self.__pixmap_cate_data

        def inner(
            _data: Any = None,
            _parent: Any = None,
            _root_type: Any = None,
            _depth: int = 1,
        ) -> None:
            if isinstance(_data, dict):
                for key, val in sorted(iter(_data.items()), key=lambda x: x[0]):
                    _pixmap = pixmap_cate_dat.get(key.lower())
                    node = NodeData(
                        node_name=key,
                        node_type=public.Type.network,
                        icon=_pixmap,
                        node_depth=_depth,
                        parent=_parent,
                    )
                    inner(
                        _data=val,
                        _parent=node,
                        _root_type=_root_type,
                        _depth=_depth + 1,
                    )
            elif isinstance(_data, list):
                for val in sorted(_data):
                    NodeData(
                        node_name=val[0],
                        node_type=val[1],
                        node_depth=_depth,
                        parent=_parent,
                    )
            else:
                pass

        for root_key, root_val in sorted(iter(data.items()), key=lambda x: x[0]):
            pixmap = pixmap_cate_dat.get(root_key)
            parent_node = NodeData(
                node_name=root_key,
                node_type=public.Type.root,
                node_depth=0,
                icon=pixmap,
                parent=parent,
            )
            inner(_data=root_val, _parent=parent_node, _root_type=root_key, _depth=1)

    def reload(self) -> None:
        self.beginResetModel()
        self.__init_set_data()
        self.endResetModel()

    @property
    def __default_data(self) -> dict[str, Any]:
        return {public.Type.root: {}}

    def __update_data(self, data: Any = None) -> None:
        if data is None:
            return
        assert isinstance(data, dict)
        if (data is None) or (not len(data)):
            return
        self.__data.get(public.Type.root).update(data)

    def add_item(self, data: Any = None) -> None:
        assert isinstance(data, dict)
        self.__update_data(data=data)

    def remove_item(self, category: str | None = None) -> None:
        del self.__data.get(public.Type.root)[category]

    def set_icon_size(self, val: Any) -> None:
        self.beginResetModel()
        self.__icon_size = val
        self.endResetModel()

    def set_font(self, style: str | None = None, size: int | None = None) -> None:
        self.beginResetModel()
        self.__font_style = style
        self.__font_size = size
        self.endResetModel()

    def set_padding(self, val: Any) -> None:
        self.beginResetModel()
        self.__padding = val
        self.endResetModel()

    def clear_item(self) -> None:
        self.beginResetModel()
        self.__data = self.__default_data
        self.__init_set_data()
        self.endResetModel()

    def flags(
        self, index: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.Qt.ItemFlag:
        flags = super(CategoryModel, self).flags(index)
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

    @property
    def headers_count(self) -> int:
        return len(self.__headers)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.__headers)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self.__headers[section]
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            return None
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setPointSize(public.UISetting.view_font_size)
            return font
        return None

    def node_from_index(self, index: QtCore.QModelIndex) -> Node:
        return index.internalPointer() if index.isValid() else self.__root

    def insertRow(
        self, row: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> bool:
        return self.insertRows(row, 1, parent)

    def insertRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> bool:
        # Tree rows require domain data; add_item/reload performs real insertion.
        return False

    def delete_node(self, index: QtCore.QModelIndex) -> None:
        if index.isValid() and index.model() is self:
            self.removeRows(index.row(), 1, index.parent())

    def removeRow(
        self, row: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> bool:
        return self.removeRows(row, 1, parent)

    def removeRows(
        self, row: int, count: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
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
        self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None
        node = self.node_from_index(index)
        column = index.column()
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return int(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            if column == 0:
                if node.icon is None:
                    return None
                return node.icon.scaled(
                    QtCore.QSize(self.__icon_size, self.__icon_size),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                )
        elif role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return node.name
            elif column == 1:
                return node.node_type
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            return font
        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(self.__icon_size, self.__icon_size + self.__padding)
        # UserRole
        elif role == CategoryModel.category_role:
            return node.name
        elif role == CategoryModel.type_role:
            return node.node_type
        elif role == CategoryModel.depth_role:
            return node.depth

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid() and parent.column() != 0:
            return 0
        node = self.node_from_index(parent)
        if node is None:
            return 0
        return len(node)

    def parent(
        self, index: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        node = self.node_from_index(index)
        if node is None:
            return QtCore.QModelIndex()
        parent = node.parent
        if parent is None:
            return QtCore.QModelIndex()
        grand_parent = parent.parent
        if grand_parent is None:
            return QtCore.QModelIndex()
        row = grand_parent.row_of_child(parent)
        assert row != -1
        return self.createIndex(row, 0, parent)
