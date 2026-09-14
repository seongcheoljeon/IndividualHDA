"""Shared Qt 6 filters: one predicate per row, with native tree propagation."""

from __future__ import annotations
from typing import Any
from PySide6 import QtCore


def search_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item) for item in value if item is not None)
    return str(value)


class AssetProxyModel(QtCore.QSortFilterProxyModel):
    tag_role: int
    type_role: int
    cate_role: int | None = None
    favorite_role: int | None = None
    name_column = 0

    def __init__(
        self, search_target_idx: int | None = None, parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._search_target_idx = search_target_idx or 0
        self._favorite_only = False
        self._node_category: str | None = None
        self.setFilterKeyColumn(self.name_column)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, self.name_column, source_parent)
        if not index.isValid():
            return False
        if self.cate_role is not None and self._node_category is not None:
            if index.data(self.cate_role) != self._node_category:
                return False
        if self.favorite_role is not None and self._favorite_only:
            if not index.data(self.favorite_role):
                return False
        role = {1: self.tag_role, 2: self.type_role}.get(
            self._search_target_idx, self.filterRole()
        )
        return (
            self.filterRegularExpression()
            .match(search_text(index.data(role)))
            .hasMatch()
        )

    def reload(self) -> None:
        self.invalidate()

    def set_search_target_idx(self, idx: int) -> None:
        self._search_target_idx = idx
        self.invalidate()

    @property
    def is_favorite_nodes(self) -> bool:
        return self._favorite_only

    @is_favorite_nodes.setter
    def is_favorite_nodes(self, val: bool | None) -> None:
        self._favorite_only = bool(val)
        self.invalidate()

    @property
    def node_category(self) -> str | None:
        return self._node_category

    @node_category.setter
    def node_category(self, val: str | None) -> None:
        self._node_category = val
        self.invalidate()


class TreeProxyModel(QtCore.QSortFilterProxyModel):
    """Qt propagates accepted descendants; constraints never accept siblings.

    A matching ancestor supplies text context only. Each concrete row still has
    to satisfy the asset/file predicate, so separate children cannot satisfy
    different halves of an AND filter.
    """

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.setFilterKeyColumn(0)
        self.setDynamicSortFilter(True)
        self.setRecursiveFilteringEnabled(True)
        self.setAutoAcceptChildRows(False)

    def row_matches(self, index: QtCore.QModelIndex) -> bool:
        return True

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)
        if not index.isValid() or not self.row_matches(index):
            return False
        while index.isValid():
            if (
                self.filterRegularExpression()
                .match(search_text(index.data(self.filterRole())))
                .hasMatch()
            ):
                return True
            index = index.parent()
        return False

    def reload(self) -> None:
        self.invalidate()

    def count_role(self, role: int, *, boolean: bool = False) -> int:
        count = 0
        pending = [QtCore.QModelIndex()]
        while pending:
            parent = pending.pop()
            for row in range(self.rowCount(parent)):
                index = self.index(row, 0, parent)
                value = index.data(role)
                count += bool(value) if boolean else value is not None
                pending.append(index)
        return count
