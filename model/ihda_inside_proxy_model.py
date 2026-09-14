"""Inside-node filters retain ancestors of matching HDA nodes."""

from __future__ import annotations

from PySide6 import QtCore

from model.ihda_inside_model import InsideModel
from model.proxy_filters import TreeProxyModel


class InsideProxyModel(TreeProxyModel):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._hda_id: int | None = None

    def row_matches(self, index: QtCore.QModelIndex) -> bool:
        return (
            self._hda_id is None or index.data(InsideModel.hda_id_role) == self._hda_id
        )

    def get_row_count(self) -> int:
        return self.count_role(InsideModel.hda_id_role)

    def set_filter_attribute(self, hda_id: int | None = None) -> None:
        self._hda_id = hda_id if hda_id != -1 else None
        self.invalidate()
