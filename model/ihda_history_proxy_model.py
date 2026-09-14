"""History search with inclusive calendar-day bounds."""

from __future__ import annotations
from collections.abc import Sequence
from PySide6 import QtCore
from model.ihda_history_model import HistoryModel
from model.proxy_filters import AssetProxyModel


class HistoryProxyModel(AssetProxyModel):
    name_column = 1
    tag_role = HistoryModel.tag_role
    type_role = HistoryModel.type_role

    def __init__(
        self, search_target_idx: int | None = None, parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(search_target_idx, parent)
        self._hda_id: int | None = None
        self._dates: tuple[str, str] | None = None

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        index = self.sourceModel().index(source_row, self.name_column, source_parent)
        if (
            self._hda_id is not None
            and index.data(HistoryModel.id_role) != self._hda_id
        ):
            return False
        if self._dates is not None:
            value = index.data(HistoryModel.datetime_role)
            day = str(value)[:10] if value is not None else ""
            if not QtCore.QDate.fromString(day, "yyyy-MM-dd").isValid():
                return False
            return self._dates[0] <= day <= self._dates[1]
        return True

    def set_hda_id(self, hda_id: int | None = None) -> None:
        self._hda_id = hda_id if hda_id != -1 else None
        self.invalidate()

    def set_datetime(self, datetime_lst: Sequence[str] | None = None) -> None:
        dates = None
        if datetime_lst:
            if (
                len(datetime_lst) != 2
                or any(
                    not QtCore.QDate.fromString(value, "yyyy-MM-dd").isValid()
                    for value in datetime_lst
                )
                or datetime_lst[0] > datetime_lst[1]
            ):
                raise ValueError(
                    "History filter requires two ordered ISO calendar dates"
                )
            dates = (datetime_lst[0], datetime_lst[1])
        self._dates = dates
        self.invalidate()
