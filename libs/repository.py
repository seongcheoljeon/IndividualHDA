"""Library storage boundary: one protocol for local SQLite now and a server later.

No Qt or HOM imports. Panel code depends on these types only; concrete adapters
live in libs/database/sqlite_repository.py (and libs/http_repository.py later).
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from libs.asset_contracts import (
    AssetData,
    AssetIcon,
    AssetIdentity,
    AssetName,
    HistoryCounts,
    HistoryData,
    HistoryThumbnail,
    NodeConnection,
    NodeConnections,
    NoteHistory,
)
from libs.asset_rename import RenameCounts, RenamePlan
from libs.scene_contracts import SceneRecord, SceneRecordInput
from libs.scene_record_cleanup import SceneRecordFiles
from libs.search_limits import SEARCH_RESULT_LIMIT


class LibraryError(Exception):
    """Base for storage failures; the message is safe to show in the log panel."""


class LibraryUnavailable(LibraryError):
    """Database file missing or server unreachable."""


class LibraryAuthError(LibraryError):
    """Server rejected the token (401/403)."""


class LibraryNotFound(LibraryError):
    """The asset, history or record no longer exists."""


class LibraryConflict(LibraryError):
    """Duplicate name or a stale revision; reload and retry."""


@dataclass(frozen=True, slots=True)
class LibrarySettings:
    mode: str = "local"  # "local" | "server"
    server_url: str = ""  # tokens are never stored here (see libs/identity, Phase 2)


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationPayload:
    """Everything a registration needs, gathered on the GUI thread from HOM.

    The capture service can build this before files exist. At the repository
    boundary the HDA has been published (thumbnail is optional); the adapter
    writes metadata. Paths are absolute in local mode.
    """

    user: str
    node_name: str
    node_path: str
    version: str
    hda_dirpath: Path
    hda_filename: str
    type_name: str
    cate_name: str
    def_desc: str
    is_network: bool
    is_sub_network: bool
    type_path_lst: tuple[str, ...]
    cate_path_lst: tuple[str, ...]
    icon_path_lst: tuple[str, ...]
    input_conn: tuple[NodeConnection, ...]
    output_conn: tuple[NodeConnection, ...]
    hou_version: str
    hou_license: str
    operating_system: str
    hip_filename: str
    hip_dirpath: Path
    sf: float
    ef: float
    fps: float
    thumb_dirpath: Path
    thumb_filename: str
    registered_at: str
    description: str = ""
    operation_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationResult:
    asset: AssetData
    history: HistoryData
    history_id: int
    thumb_filepath: Path


class LibraryReads(Protocol):
    """Everything a feature needs to show a library; no writes."""

    def revision(self) -> int: ...
    def list_assets(
        self, owner: str | None = None, category: str | None = None
    ) -> list[AssetData]: ...
    def categories(self, owner: str | None = None) -> list[str]: ...
    def histories(
        self, asset_id: int | None, owner: str | None = None, search_date: Any = None
    ) -> list[HistoryData]: ...
    def activity(self, owner: str | None = None) -> list[HistoryData]: ...
    def asset_icons(self, owner: str | None = None) -> list[AssetIcon]: ...
    def history_thumbnails(
        self, owner: str | None = None
    ) -> list[HistoryThumbnail]: ...
    def asset_available(self, asset_id: int, history_id: int | None = None) -> bool: ...
    def has_asset(self, owner: str, category: str, name: str) -> bool: ...
    def asset_identity(
        self, owner: str, category: str, name: str
    ) -> AssetIdentity | None: ...
    def asset_ids(self, owner: str | None = None) -> list[int]: ...
    def asset_names(self, owner: str | None = None) -> list[AssetName]: ...
    def asset_filepath(self, asset_id: int) -> Path | None: ...
    def has_history(self, asset_id: int) -> bool: ...
    def note_history(self, asset_id: int) -> list[NoteHistory]: ...
    def history_counts(self) -> HistoryCounts: ...
    def history_videos(self, asset_id: int) -> list[Path]: ...
    def latest_video(self, asset_id: int, version: str) -> Path | None: ...
    def video_matches_version(self, asset_id: int, version: str) -> bool: ...
    def is_latest_history(self, asset_id: int, history_id: int) -> bool: ...
    def node_connections(self, asset_id: int) -> NodeConnections: ...
    def import_note(self, asset_id: int, version: str | None = None) -> str | None: ...
    def import_license(self, asset_id: int, version: str, owner: str) -> str | None: ...
    def search_asset_ids(
        self,
        query: str,
        *,
        field: str = "All",
        case_sensitive: bool = False,
        limit: int = SEARCH_RESULT_LIMIT,
        cancel: threading.Event | None = None,
    ) -> list[int]: ...
    def distinct_tags(self, owner: str | None = None) -> list[str]: ...
    def version_identity(
        self,
        asset_id: int,
        history_id: int | None = None,
        version_uuid: str | None = None,
    ) -> str | None: ...


class AssetWrites(Protocol):
    """Mutations of assets, versions and metadata; run off the GUI thread."""

    def ensure_user(self, user: str) -> None: ...
    def register_asset(self, payload: RegistrationPayload) -> RegistrationResult: ...
    def add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult: ...
    def set_note(self, asset_id: int, note: str) -> None: ...
    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None: ...
    def toggle_favorite(self, asset_id: int) -> bool: ...
    def set_thumbnail(
        self, asset_id: int, directory: Path, filename: str, version: str
    ) -> bool: ...
    def set_video(
        self, asset_id: int, directory: Path, filename: str, version: str
    ) -> str: ...
    def rename_asset(self, plan: RenamePlan) -> RenameCounts: ...
    def delete_asset(self, asset_id: int, directory: Path) -> None: ...
    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None: ...
    def registration_recovery(self) -> Any: ...
    def record_use(self, asset_id: int) -> None: ...


class SceneRecordRepository(Protocol):
    """Where assets were used in scenes."""

    def scene_records(self) -> tuple[SceneRecord, ...]: ...
    def record_detail(self, record_id: int) -> SceneRecord | None: ...
    def record_scene_usage(self, record: SceneRecordInput) -> int: ...
    def scene_record_files(self, user: str) -> list[SceneRecordFiles]: ...
    def delete_scene_record(self, record_id: int) -> bool: ...


class LibraryRepository(LibraryReads, AssetWrites, SceneRecordRepository, Protocol):
    """The full local library. Features should ask for the role they use;
    this union exists for the session that owns the adapter."""
