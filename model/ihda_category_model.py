#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:55
# modify date       :
# description       :

from imp import reload

from PySide2 import QtGui, QtCore

try:
    import hou
except ImportError as err:
    pass

import public

reload(public)


class Node(QtCore.QObject):
    def __init__(self, node_name=None, node_depth=None, parent=None):
        super(Node, self).__init__()
        self.__name = node_name
        self.__depth = node_depth
        self.__parent = parent
        self.__children = list()
        self.setParent(parent)

    @property
    def name(self):
        return self.__name

    @property
    def depth(self):
        return self.__depth

    @property
    def parent(self):
        return self.__parent

    def setParent(self, parent):
        if parent is not None:
            self.__parent = parent
            self.__parent.append_child(self)
        else:
            self.__parent = None

    def append_child(self, child):
        self.__children.append(child)

    def child_at_row(self, row):
        return self.__children[row]

    def row_of_child(self, child):
        for idx, item in enumerate(self.__children):
            if child == item:
                return idx
        return -1

    def remove_child(self, row):
        value = self.__children[row]
        self.__children.remove(value)
        return True

    def __len__(self):
        return len(self.__children)


class NodeData(Node):
    def __init__(self, node_name=None, node_type=None, icon=None, node_depth=None, parent=None):
        super(NodeData, self).__init__(node_name=node_name, node_depth=node_depth, parent=parent)
        self.__node_type = node_type
        self.__icon = icon

    @property
    def node_type(self):
        return self.__node_type

    @property
    def icon(self):
        return self.__icon if self.__icon is not None else None


class CategoryModel(QtCore.QAbstractItemModel):
    category_role = QtCore.Qt.UserRole
    type_role = QtCore.Qt.UserRole + 1
    depth_role = QtCore.Qt.UserRole + 2

    def __init__(self, data=None, pixmap_cate_data=None, font_size=None, font_style=None,
                 icon_size=None, padding=None, parent=None):
        super(CategoryModel, self).__init__(parent)
        self.__data = self.__default_data
        self.__pixmap_cate_data = pixmap_cate_data
        self.__font_size = font_size
        self.__font_style = font_style
        self.__icon_size = icon_size
        self.__padding = padding
        self.__update_data(data=data)
        self.__headers = ('Network',)
        self.__root = None
        self.__init_set_data()

    def add_pixmap_cate_data(self, category=None, pixmap=None):
        if category not in self.__pixmap_cate_data:
            self.__pixmap_cate_data.update({category: pixmap})

    def remove_pixmap_cate_data(self, category=None):
        if category in self.__pixmap_cate_data:
            del self.__pixmap_cate_data[category]

    def __init_set_data(self):
        self.__root = NodeData(node_name=public.Type.root, node_type='', node_depth=0, parent=None)
        if self.__data is not None:
            self.__set_treemodel_data(data=self.__data, parent=self.__root)

    def __set_treemodel_data(self, data=None, parent=None):
        pixmap_cate_dat = self.__pixmap_cate_data

        def inner(_data=None, _parent=None, _root_type=None, _depth=1):
            if isinstance(_data, dict):
                for key, val in sorted(_data.iteritems(), key=lambda x: x[0]):
                    _pixmap = pixmap_cate_dat.get(key.lower())
                    node = NodeData(node_name=key, node_type=public.Type.network, icon=_pixmap,
                                    node_depth=_depth, parent=_parent)
                    inner(_data=val, _parent=node, _root_type=_root_type, _depth=_depth+1)
            elif isinstance(_data, list):
                for val in sorted(_data):
                    NodeData(node_name=val[0], node_type=val[1], node_depth=_depth, parent=_parent)
            else:
                pass

        for root_key, root_val in sorted(data.iteritems(), key=lambda x: x[0]):
            pixmap = pixmap_cate_dat.get(root_key)
            parent_node = NodeData(
                node_name=root_key, node_type=public.Type.root, node_depth=0, icon=pixmap, parent=parent)
            inner(_data=root_val, _parent=parent_node, _root_type=root_key, _depth=1)

    def reload(self):
        self.beginResetModel()
        self.__init_set_data()
        self.endResetModel()

    @property
    def __default_data(self):
        return {public.Type.root: {}}

    def __update_data(self, data=None):
        if data is None:
            return
        assert isinstance(data, dict)
        if (data is None) or (not len(data)):
            return
        self.__data.get(public.Type.root).update(data)

    def add_item(self, data=None):
        assert isinstance(data, dict)
        self.__update_data(data=data)

    def remove_item(self, category=None):
        del self.__data.get(public.Type.root)[category]

    def set_icon_size(self, val):
        self.beginResetModel()
        self.__icon_size = val
        self.endResetModel()

    def set_font(self, style=None, size=None):
        self.beginResetModel()
        self.__font_style = style.decode('utf8')
        self.__font_size = size
        self.endResetModel()

    def set_padding(self, val):
        self.beginResetModel()
        self.__padding = val
        self.endResetModel()

    def clear_item(self):
        self.beginResetModel()
        self.__data = self.__default_data
        self.__init_set_data()
        self.endResetModel()

    def flags(self, index=QtCore.QModelIndex()):
        flags = super(CategoryModel, self).flags(index)
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    @property
    def headers_count(self):
        return len(self.__headers)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.__headers)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.__headers[section]
        elif role == QtCore.Qt.DecorationRole:
            return None
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setPointSize(public.UISetting.view_font_size)
            return font
        return None

    def node_from_index(self, index):
        return index.internalPointer() if index.isValid() else self.__root

    def insertRow(self, row, parent=QtCore.QModelIndex()):
        return self.insertRows(row, 1, parent)

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        node = self.nodeFromindex(parent)
        self.beginInsertRows(parent, row, (row + (count - 1)))
        self.endInsertRows()
        return True

    def delete_node(self, index):
        node = self.node_from_index(index)
        parent = self.parent(index)
        position = node.row_of_child(parent)
        self.removeRows(position, 1, parent)

    def removeRow(self, row, parent=QtCore.QModelIndex()):
        return self.removeRows(row, 1, parent)

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        node = self.node_from_index(parent)
        node.remove_child(row)
        self.endRemoveRows()
        return True

    def index(self, row, column, parent=QtCore.QModelIndex()):
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = self.node_from_index(index)
        column = index.column()
        if role == QtCore.Qt.TextAlignmentRole:
            return int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        elif role == QtCore.Qt.DecorationRole:
            if column == 0:
                if node.icon is None:
                    return None
                return node.icon.scaled(QtCore.QSize(self.__icon_size, self.__icon_size), QtCore.Qt.KeepAspectRatio)
        elif role == QtCore.Qt.DisplayRole:
            if column == 0:
                return node.name
            elif column == 1:
                return node.node_type
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            return font
        elif role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(self.__icon_size, self.__icon_size + self.__padding)
        # UserRole
        elif role == CategoryModel.category_role:
            return node.name
        elif role == CategoryModel.type_role:
            return node.node_type
        elif role == CategoryModel.depth_role:
            return node.depth

    # def setData(self, index, value, role=QtCore.Qt.DisplayRole):
    #     if not index.isValid():
    #         return False
    #     node = self.node_from_index(index)
    #     if role == QtCore.Qt.DisplayRole:
    #         node.name = value
    #         self.emit(QtCore.SIGNAL('dataChanged(QModelIndex, QModelIndex)', index, index))
    #         return True
    #     return False

    def rowCount(self, parent=QtCore.QModelIndex()):
        node = self.node_from_index(parent)
        if node is None:
            return 0
        return len(node)

    def parent(self, index=QtCore.QModelIndex()):
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
