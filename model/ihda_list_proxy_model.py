# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : seongcheolzeon@gmail.com
# create date       : 2020.01.28 01:36
# modify date       :
# description       :

from imp import reload

from PySide2 import QtCore

from model import ihda_list_model

reload(ihda_list_model)


class ListProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, search_target_idx=None, parent=None):
        super(ListProxyModel, self).__init__(parent)
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
        if self.__node_category is not None:
            is_filtering &= index.data(ihda_list_model.ListModel.cate_role) == self.__node_category
        #
        if self.__is_favorite_nodes is not None:
            is_filtering &= index.data(ihda_list_model.ListModel.favorite_role)
        if self.__search_target_idx == 1:
            return self.__is_regex(' '.join(index.data(ihda_list_model.ListModel.tag_role))) and is_filtering
        elif self.__search_target_idx == 2:
            return self.__is_regex(index.data(ihda_list_model.ListModel.type_role)) and is_filtering
        else:
            return super(ListProxyModel, self).filterAcceptsRow(
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
