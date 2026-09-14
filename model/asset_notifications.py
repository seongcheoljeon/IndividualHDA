"""Qt adapter for the asset store's row-change contract."""

from __future__ import annotations

from PySide6.QtCore import QAbstractItemModel, QModelIndex


class QtAssetNotifications:
    def __init__(self, *models: QAbstractItemModel) -> None:
        self.models = models

    def begin_reset(self) -> None:
        for model in self.models:
            model.beginResetModel()

    def end_reset(self) -> None:
        for model in self.models:
            model.endResetModel()

    def begin_insert(self, row: int) -> None:
        for model in self.models:
            model.beginInsertRows(QModelIndex(), row, row)

    def end_insert(self) -> None:
        for model in self.models:
            model.endInsertRows()

    def begin_remove(self, row: int) -> None:
        for model in self.models:
            model.beginRemoveRows(QModelIndex(), row, row)

    def end_remove(self) -> None:
        for model in self.models:
            model.endRemoveRows()

    def changed(self, row: int) -> None:
        for model in self.models:
            model.dataChanged.emit(
                model.index(row, 0), model.index(row, model.columnCount() - 1), []
            )
