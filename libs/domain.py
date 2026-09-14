"""Typed library payloads. Paths are decoded at the database boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypedDict, TypeVar


class AssetData(TypedDict, total=False):
    hda_id: int
    hda_name: str
    hda_cate: str
    hda_icon: list[str]
    hda_tags: list[str]
    hda_note: str | None
    is_favorite_hda: bool
    hip_filename: str | None
    hip_dirpath: Path | None
    hda_load_count: int
    hda_ctime: str
    hda_mtime: str
    hou_version: str
    node_old_path: str
    hda_license: str
    hda_version: str
    hda_dirpath: Path | None
    hda_filename: str | None
    thumbnail_filename: str | None
    thumbnail_dirpath: Path | None
    video_filename: str | None
    video_dirpath: Path | None
    node_type_path_list: list[str]
    node_cate_path_list: list[str]
    node_icon_path_list: list[str]
    node_type_name: str
    node_cate_name: str
    node_def_desc: str
    node_input_connections: list[tuple[int, str, str, int]]
    node_output_connections: list[tuple[int, str, str, int]]
    is_network: bool
    is_sub_network: bool
    item_row: int


class HistoryData(TypedDict, total=False):
    hist_id: int
    hda_id: int
    comment: str | None
    org_hda_name: str
    version: str
    ihda_filename: str | None
    ihda_dirpath: Path | None
    reg_time: str
    hou_version: str
    hip_filename: str | None
    hip_dirpath: Path | None
    hda_license: str
    os: str
    node_old_path: str
    node_def_desc: str
    node_type_name: str
    node_category: str
    userid: str
    icon: list[str]
    tags: list[str]
    hda_note: str | None
    thumb_dirpath: Path | None
    thumb_filename: str | None
    video_dirpath: Path | None
    video_filename: str | None
    item_row: int


class SceneRecord(TypedDict, total=False):
    record_id: int
    hda_id: int
    hip_filename: str | None
    hip_dirpath: Path | None
    hda_filename: str | None
    hda_dirpath: Path | None
    parent_node_path: str
    node_type: str
    node_cate: str
    node_name: str
    org_node_name: str
    node_ver: str
    houdini_version: str
    houdini_license: str
    operating_system: str
    sf: float
    ef: float
    fps: float
    ctime: str
    mtime: str
    thumb_dirpath: Path | None
    thumb_filename: str | None
    video_dirpath: Path | None
    video_filename: str | None


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


@dataclass(slots=True)
class SelectionState:
    asset: ItemSelection[AssetData] = field(default_factory=ItemSelection)
    history: ItemSelection[HistoryData] = field(default_factory=ItemSelection)

    # Category tree selection (owned here; formerly scattered panel attributes).
    parents: list[str] = field(default_factory=list)
    column_idx: int | None = None
    item_text: str | None = None

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
        import public

        data_dirpath = Path(preference.data_dirpath)
        asset_root = public.hda_base_dirpath(base_dirpath=data_dirpath)
        return cls(
            user=user,
            data_dirpath=data_dirpath,
            db_filepath=data_dirpath / public.SQLite.db_filename,
            asset_root=asset_root,
            hda_base_dirpath=asset_root / user,
        )
