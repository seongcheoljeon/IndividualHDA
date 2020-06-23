#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:36
# modify date       :
# description       :

from imp import reload

from PySide2 import QtCore

from model import ihda_history_model

reload(ihda_history_model)


class HistoryProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, search_target_idx=None, parent=None):
        super(HistoryProxyModel, self).__init__(parent)
        self.__search_target_idx = search_target_idx
        self.__name_column = 1
        self.__hda_id = None
        self.__datetime_lst = None
        self.setFilterKeyColumn(self.__name_column)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, self.__name_column, source_parent)
        # data = self.sourceModel().data(index)
        #
        is_filtering = True

        if self.__hda_id is not None:
            is_hda_id = index.data(ihda_history_model.HistoryModel.id_role) == self.__hda_id
            is_filtering &= is_hda_id

        if self.__datetime_lst is not None:
            datetime_reg = index.data(ihda_history_model.HistoryModel.datetime_role)
            is_valid_datetime = (datetime_reg >= self.__datetime_lst[0]) and (datetime_reg <= self.__datetime_lst[1])
            is_filtering &= is_valid_datetime

        if self.__search_target_idx == 1:
            return self.__is_regex(
                ' '.join(index.data(ihda_history_model.HistoryModel.tag_role))) and is_filtering
        elif self.__search_target_idx == 2:
            return self.__is_regex(index.data(ihda_history_model.HistoryModel.type_role)) and is_filtering
        else:
            return super(HistoryProxyModel, self).filterAcceptsRow(
                source_row, source_parent) and self.__is_regex(index.data()) and is_filtering

    def reload(self):
        self.invalidate()
        self.invalidateFilter()

    def __is_regex(self, data):
        return self.filterRegExp().indexIn(data) >= 0

    def set_search_target_idx(self, idx):
        self.__search_target_idx = idx
        self.invalidateFilter()

    def set_hda_id(self, hda_id=None):
        self.__hda_id = hda_id if hda_id != -1 else None
        self.invalidateFilter()

    def set_datetime(self, datetime_lst=None):
        self.__datetime_lst = datetime_lst if len(datetime_lst) else None
        self.invalidateFilter()

