"""Named application records, independent of storage and Qt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class NodeConnection:
    port: int
    node_name: str
    node_type: str
    peer_port: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetData:
    remote: bool = False
    library_id: str = ""
    hda_id: int
    hda_name: str
    hda_cate: str = ""
    hda_icon: tuple[str, ...] = ()
    hda_tags: tuple[str, ...] = ()
    hda_note: str | None = None
    is_favorite_hda: bool = False
    hip_filename: str | None = None
    hip_dirpath: Path | None = None
    hda_load_count: int = 0
    hda_ctime: str = ""
    hda_mtime: str = ""
    hou_version: str = ""
    node_old_path: str = ""
    hda_license: str = ""
    hda_version: str = ""
    hda_dirpath: Path | None = None
    hda_filename: str | None = None
    thumbnail_filename: str | None = None
    thumbnail_dirpath: Path | None = None
    video_filename: str | None = None
    video_dirpath: Path | None = None
    node_type_path_list: tuple[str, ...] = ()
    node_cate_path_list: tuple[str, ...] = ()
    node_icon_path_list: tuple[str, ...] = ()
    node_type_name: str = ""
    node_cate_name: str = ""
    node_def_desc: str = ""
    node_input_connections: tuple[NodeConnection, ...] = ()
    node_output_connections: tuple[NodeConnection, ...] = ()
    is_network: bool = False
    is_sub_network: bool = False
    item_row: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoryData:
    remote: bool = False
    library_id: str = ""
    # "version" is a real hda_history row; "rename"/"video" rows come from
    # audit events and own no files, so the panel neither opens nor deletes them.
    kind: str = "version"
    hist_id: int = 0
    hda_id: int
    comment: str | None = None
    org_hda_name: str
    version: str
    ihda_filename: str | None = None
    ihda_dirpath: Path | None = None
    reg_time: str = ""
    hou_version: str = ""
    hip_filename: str | None = None
    hip_dirpath: Path | None = None
    hda_license: str = ""
    os: str = ""
    node_old_path: str = ""
    node_def_desc: str = ""
    node_type_name: str = ""
    node_category: str = ""
    userid: str = ""
    icon: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    hda_note: str | None = None
    thumb_dirpath: Path | None = None
    thumb_filename: str | None = None
    video_dirpath: Path | None = None
    video_filename: str | None = None
    item_row: int = 0

    @property
    def is_version(self) -> bool:
        return self.kind == "version"


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoryThumbnail:
    hist_id: int
    thumb_dirpath: Path | None
    thumb_filename: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetIdentity:
    asset_id: int
    node_type: str | None
    version: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetName:
    asset_id: int
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetIcon:
    asset_id: int
    icon: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoryCounts:
    versions: int
    notes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class NodeConnections:
    inputs: tuple[NodeConnection, ...] = ()
    outputs: tuple[NodeConnection, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarySnapshot:
    revision: int
    assets: tuple[AssetData, ...] = ()
    categories: tuple[str, ...] = ()
    histories: tuple[HistoryData, ...] = ()
    icons: tuple[AssetIcon, ...] = ()
    history_thumbnails: tuple[HistoryThumbnail, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncContext:
    repository: object
    write_generation: int


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteHistory:
    registered_at: str
    version: str
    note: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetBeforeUpdate:
    is_favorite_hda: bool
    hda_load_count: int
    hda_ctime: str
    hda_tags: tuple[str, ...]
    hda_note: str | None
    video_dirpath: Path | None
    video_filename: str | None
