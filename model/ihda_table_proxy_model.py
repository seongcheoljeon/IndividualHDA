#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:36
# modify date       :
# description       :

from imp import reload

from PySide2 import QtCore

from model import ihda_table_model

reload(ihda_table_model)


class TableProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, search_target_idx=None, parent=None):
        super(TableProxyModel, self).__init__(parent)
        self.__search_target_idx = search_target_idx
        self.__is_favorite_nodes = None
        self.__node_category = None
        self.setFilterKeyColumn(0)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)
        # data = self.sourceModel().data(index)
        #
        is_filtering = True
        # root를 제외한 나머지 category를 선택했다면
        if self.__node_category is not None:
            is_node_cate = index.data(ihda_table_model.TableModel.cate_role) == self.__node_category
            is_filtering &= is_node_cate
        #
        if self.__is_favorite_nodes is not None:
            is_filtering &= index.data(ihda_table_model.TableModel.favorite_role)

        if self.__search_target_idx == 1:
            return self.__is_regex(' '.join(index.data(ihda_table_model.TableModel.tag_role))) and is_filtering
        elif self.__search_target_idx == 2:
            return self.__is_regex(index.data(ihda_table_model.TableModel.type_role)) and is_filtering
        else:
            return super(TableProxyModel, self).filterAcceptsRow(
                source_row, source_parent) and self.__is_regex(index.data()) and is_filtering

    def reload(self):
        self.invalidate()
        self.invalidateFilter()

    def __is_regex(self, data):
        return self.filterRegExp().indexIn(data) >= 0

    def set_search_target_idx(self, idx):
        self.__search_target_idx = idx
        self.invalidateFilter()

    @property
    def is_favorite_nodes(self):
        return self.__is_favorite_nodes

    @is_favorite_nodes.setter
    def is_favorite_nodes(self, val):
        self.__is_favorite_nodes = val if val else None
        self.invalidateFilter()

    @property
    def node_category(self):
        return self.__node_category

    @node_category.setter
    def node_category(self, val):
        self.__node_category = val
        self.invalidateFilter()
