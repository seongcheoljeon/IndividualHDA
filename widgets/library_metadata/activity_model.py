"""Activity rows (time · actor · action · detail) for the Version details dialog."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from PySide6 import QtCore

HEADERS = ("Time", "Actor", "Action", "Detail")
ActivityRow = tuple[str, str, str, str]
Index = QtCore.QModelIndex | QtCore.QPersistentModelIndex


class ActivityModel(QtCore.QAbstractTableModel):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[ActivityRow] = []

    def set_rows(self, rows: Sequence[ActivityRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rows(self) -> list[ActivityRow]:
        return list(self._rows)

    def rowCount(self, parent: Index = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: Index = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(HEADERS)

    def data(self, index: Index, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role not in (
            QtCore.Qt.ItemDataRole.DisplayRole,
            QtCore.Qt.ItemDataRole.ToolTipRole,
        ):
            return None
        return self._rows[index.row()][index.column()]

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            role == QtCore.Qt.ItemDataRole.DisplayRole
            and orientation == QtCore.Qt.Orientation.Horizontal
        ):
            return HEADERS[section]
        return None
