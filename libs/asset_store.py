"""Own asset rows and indexes; send mutation notifications through an observer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from libs.asset_contracts import AssetData
from libs.contracts import RowNotifications, SilentRows


class AssetStore:
    def __init__(self, observer: RowNotifications | None = None) -> None:
        self.rows: list[AssetData] = []
        self._id_rows: dict[int, int] = {}
        self._observer: RowNotifications = (
            observer if observer is not None else SilentRows()
        )

    @property
    def id_rows(self) -> Mapping[int, int]:
        return MappingProxyType(self._id_rows)

    def observe(self, observer: RowNotifications) -> None:
        self._observer = observer

    def _reindex(self) -> None:
        self._id_rows.clear()
        self._id_rows.update((item.hda_id, row) for row, item in enumerate(self.rows))

    def reset(self, rows: Iterable[AssetData]) -> None:
        replacement = list(rows)
        ids = [item.hda_id for item in replacement]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate asset IDs")
        self._observer.begin_reset()
        self.rows[:] = replacement
        self._reindex()
        self._observer.end_reset()

    def insert(self, data: AssetData) -> int:
        if data.hda_id in self._id_rows:
            raise ValueError("Duplicate asset ID")
        row = next(
            (i for i, item in enumerate(self.rows) if item.hda_name > data.hda_name),
            len(self.rows),
        )
        self._observer.begin_insert(row)
        self.rows.insert(row, data)
        self._reindex()
        self._observer.end_insert()
        return row

    def update(self, row: int, data: AssetData) -> None:
        if not 0 <= row < len(self.rows):
            raise IndexError(row)
        item = self.rows[row]
        if data.hda_id != item.hda_id:
            raise ValueError("Asset IDs are immutable")
        self.rows[row] = data
        self._observer.changed(row)

    def remove(self, row: int) -> None:
        if not 0 <= row < len(self.rows):
            raise IndexError(row)
        self._observer.begin_remove(row)
        del self.rows[row]
        self._reindex()
        self._observer.end_remove()
