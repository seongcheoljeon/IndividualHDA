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
    id_role: int | None = None
    name_column = 0
    _FIELD_INDEX = {"Tags": 1, "Type": 2}

    def __init__(
        self, search_target_idx: int | None = None, parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._search_target_idx = search_target_idx or 0
        self._id_filter: frozenset[int] | None = None
        self._favorite_only = False
        self._node_category: str | None = None
        self.setFilterKeyColumn(self.name_column)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
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
        if self._id_filter is not None and self.id_role is not None:
            return index.data(self.id_role) in self._id_filter
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

    def set_search_field(self, name: str) -> None:
        """Field for the local regex path; repository searches pass the name themselves."""
        self.set_search_target_idx(self._FIELD_INDEX.get(name, 0))

    def set_id_filter(self, ids: frozenset[int] | None) -> None:
        """Show only these asset ids (repository search result); None restores regex."""
        self._id_filter = ids
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

    def search_texts(self, index: QtCore.QModelIndex) -> list[str]:
        """Texts the filter expression is matched against for one row."""
        return [search_text(index.data(self.filterRole()))]

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> bool:
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)
        if not index.isValid() or not self.row_matches(index):
            return False
        expression = self.filterRegularExpression()
        while index.isValid():
            if any(
                expression.match(text).hasMatch() for text in self.search_texts(index)
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
