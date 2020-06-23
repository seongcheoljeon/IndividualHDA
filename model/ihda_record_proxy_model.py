# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.05.15 01:36
# modify date       :
# description       :

from imp import reload

from PySide2 import QtCore

from model import ihda_record_model

reload(ihda_record_model)


class RecordProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(RecordProxyModel, self).__init__(parent)
        self.__hip_filepath = None
        self.__hda_id = None
        self.setFilterKeyColumn(0)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)

        is_filtering = True

        if self.__hip_filepath is not None:
            hip_fpath = index.data(ihda_record_model.RecordModel.hip_filepath_role)
            if hip_fpath is not None:
                is_filtering &= (hip_fpath.as_posix() == self.__hip_filepath.as_posix())
            else:
                hip_dpath = index.data(ihda_record_model.RecordModel.hip_dirpath_role)
                if hip_dpath is not None:
                    is_filtering &= (hip_dpath.as_posix() == self.__hip_filepath.parent.as_posix())

        if self.__hda_id is not None:
            is_filtering &= self.__is_exist_hda_id(parent=index)

        if self.__filter_accept_row_itself(source_row, source_parent):
            return True and is_filtering

        if self.__filter_accept_any_parent(source_parent):
            return True and is_filtering

        return self.__has_accepted_children(source_row, source_parent) and is_filtering

    def __filter_accept_row_itself(self, source_row, source_parent):
        return super(RecordProxyModel, self).filterAcceptsRow(source_row, source_parent)

    def __filter_accept_any_parent(self, source_parent):
        while source_parent.isValid():
            if self.__filter_accept_row_itself(source_parent.row(), source_parent.parent()):
                return True
            source_parent = source_parent.parent()
        return False

    def __has_accepted_children(self, source_row, source_parent):
        model = self.sourceModel()
        source_index = model.index(source_row, 0, source_parent)
        children_count = model.rowCount(source_index)
        for i in range(children_count):
            if self.filterAcceptsRow(i, source_index):
                return True
        return False

    def reload(self):
        self.invalidate()
        self.invalidateFilter()

    # 재귀적으로 iHDA Record 데이터 개수만 구하는 함수
    def get_row_count(self):
        root_index = self.index(0, 0, QtCore.QModelIndex())
        return self.__calc_row_count(root_index)

    def __calc_row_count(self, index):
        num_record_data = 0
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            if child_index.data(ihda_record_model.RecordModel.is_record_type_role):
                num_record_data += 1
            num_record_data += self.__calc_row_count(child_index)
        return num_record_data

    def __is_exist_hda_id(self, parent=None):
        is_hda_id = False
        model = parent.model()
        if model.rowCount(parent) == 0:
            return parent.data(ihda_record_model.RecordModel.hda_id_role) == self.__hda_id
        else:
            for row in range(0, model.rowCount(parent)):
                child_index = model.index(row, 0, parent)
                if child_index.data(ihda_record_model.RecordModel.hda_id_role) == self.__hda_id:
                    is_hda_id |= True
                is_hda_id |= self.__is_exist_hda_id(child_index)
        return is_hda_id

    def set_filter_attribute(self, hda_id=None, hip_filepath=None):
        self.__hda_id = hda_id
        self.__hip_filepath = hip_filepath
        self.invalidateFilter()
