"""Typed library payloads. Paths are decoded at the database boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

from libs.asset_contracts import AssetData, HistoryData
from libs.paths import SQLite, hda_base_dirpath

Payload = TypeVar("Payload", AssetData, HistoryData)


@dataclass(slots=True)
class ItemSelection(Generic[Payload]):
    data: Payload | None = None
    id: int | None = None
    row: int | None = None
    name: str | None = None
    filepath: Path | None = None
    field: str | None = None
    cate: str | None = None
    version: str | None = None
    hist_id: int | None = None

    def require_data(self) -> Payload:
        if self.data is None:
            raise ValueError("Select an asset or version first")
        return self.data


@dataclass(slots=True)
class SelectionState:
    asset: ItemSelection[AssetData] = field(default_factory=ItemSelection)
    history: ItemSelection[HistoryData] = field(default_factory=ItemSelection)

    # Category tree selection (owned here; formerly scattered panel attributes).
    parents: list[str] = field(default_factory=list)
    column_idx: int | None = None
    item_text: str | None = None

    def select_asset(
        self, data: AssetData | None, row: int | None = None, field: str | None = None
    ) -> None:
        directory = data.hda_dirpath if data else None
        filename = data.hda_filename if data else None
        self.asset = ItemSelection(
            data=data,
            row=row,
            field=field,
            id=data.hda_id if data else None,
            name=data.hda_name if data else None,
            cate=data.hda_cate if data else None,
            version=data.hda_version if data else None,
            filepath=directory / filename if directory and filename else None,
        )

    def select_history(
        self, data: HistoryData | None, row: int | None = None, field: str | None = None
    ) -> None:
        directory = data.ihda_dirpath if data else None
        filename = data.ihda_filename if data else None
        self.history = ItemSelection(
            data=data,
            row=row,
            field=field,
            id=data.hda_id if data else None,
            name=data.org_hda_name if data else None,
            cate=data.node_category if data else None,
            version=data.version if data else None,
            hist_id=data.hist_id if data else None,
            filepath=directory / filename if directory and filename else None,
        )

    def select_category(self, column: int, text: str, parents: list[str]) -> None:
        self.column_idx, self.item_text, self.parents = column, text, list(parents)

    def set_category_parents(self, parents: list[str]) -> None:
        self.parents = list(parents)

    def set_field(self, value: str | None, *, history: bool = False) -> None:
        (self.history if history else self.asset).field = value

    def restore_asset_id(self, asset_id: int | None) -> None:
        """Remember identity while rows are being loaded; no stale item data."""
        self.clear_asset()
        self.asset.id = asset_id

    def clear(self) -> None:
        self.clear_asset()
        self.clear_history()
        self.select_category(0, "", [])

    def clear_asset(self) -> None:
        self.asset = ItemSelection()

    def clear_history(self) -> None:
        self.history = ItemSelection()


@dataclass(frozen=True, slots=True)
class LibraryContext:
    """Where this session's library lives and who is working in it.

    Immutable for the session: changing the data directory already requires a
    panel restart, so mixins read one snapshot instead of the Preference dialog.
    """

    user: str
    data_dirpath: Path
    db_filepath: Path  # data_dirpath / ihda.db
    asset_root: Path  # data_dirpath / houdini / IndividualHDA
    hda_base_dirpath: Path  # asset_root / user

    @classmethod
    def from_preference(cls, preference: Any, user: str) -> LibraryContext | None:
        if not preference.is_data_valid:
            return None

        data_dirpath = Path(preference.data_dirpath)
        asset_root = hda_base_dirpath(base_dirpath=data_dirpath)
        return cls(
            user=user,
            data_dirpath=data_dirpath,
            db_filepath=data_dirpath / SQLite.db_filename,
            asset_root=asset_root,
            hda_base_dirpath=asset_root / user,
        )
