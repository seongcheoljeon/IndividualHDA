"""Scene record filters applied together to each concrete record."""

from __future__ import annotations
from pathlib import Path
from PySide6 import QtCore
from model.ihda_record_model import RecordModel
from model.proxy_filters import TreeProxyModel


class RecordProxyModel(TreeProxyModel):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._hip_filepath: Path | None = None
        self._hda_id: int | None = None

    def row_matches(self, index: QtCore.QModelIndex) -> bool:
        if (
            self._hda_id is not None
            and index.data(RecordModel.hda_id_role) != self._hda_id
        ):
            return False
        if self._hip_filepath is not None:
            filepath = index.data(RecordModel.hip_filepath_role)
            if filepath is None or Path(filepath) != self._hip_filepath:
                return False
        return True

    def get_row_count(self) -> int:
        return self.count_role(RecordModel.is_record_type_role, boolean=True)

    def set_filter_attribute(
        self, hda_id: int | None = None, hip_filepath: Path | None = None
    ) -> None:
        self._hda_id = hda_id if hda_id != -1 else None
        self._hip_filepath = Path(hip_filepath) if hip_filepath is not None else None
        self.invalidate()
