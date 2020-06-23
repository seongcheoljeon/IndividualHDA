#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 01:36
# modify date       :
# description       :


from PySide2 import QtCore


class CategoryProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(CategoryProxyModel, self).__init__(parent)
        self.setFilterKeyColumn(0)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row, source_parent):
        if self.filter_accept_row_itself(source_row, source_parent):
            return True

        if self.filter_accept_any_parent(source_parent):
            return True

        return self.has_accepted_children(source_row, source_parent)

    def filter_accept_row_itself(self, source_row, source_parent):
        return super(CategoryProxyModel, self).filterAcceptsRow(source_row, source_parent)

    def filter_accept_any_parent(self, source_parent):
        while source_parent.isValid():
            if self.filter_accept_row_itself(source_parent.row(), source_parent.parent()):
                return True
            source_parent = source_parent.parent()
        return False

    def has_accepted_children(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False
        source_index = model.index(source_row, 0, source_parent)
        children_count = model.rowCount(source_index)
        for i in range(children_count):
            if self.filterAcceptsRow(i, source_index):
                return True
        return False

    def reload(self):
        self.invalidate()
        self.invalidateFilter()


if __name__ == '__main__':
    pass
