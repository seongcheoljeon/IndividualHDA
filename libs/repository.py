"""Library storage boundary: one protocol for local SQLite now and a server later.

No Qt or HOM imports. Panel code depends on these types only; concrete adapters
live in libs/database/sqlite_repository.py (and libs/http_repository.py later).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any, Protocol

from libs.asset_rename import RenamePlan
from libs.domain import AssetData, HistoryData


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


@dataclass(frozen=True, slots=True)
class RegistrationPayload:
    """Everything a registration needs, gathered on the GUI thread from HOM.

    Files (HDA, thumbnail) already exist on disk when this is built; the adapter
    only writes metadata. Paths are absolute in local mode.
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
    type_path_lst: list[Any]
    cate_path_lst: list[Any]
    icon_path_lst: list[Any]
    input_conn: Any
    output_conn: Any
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


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    asset: AssetData
    history: list[
        Any
    ]  # positional row for the history model (hda_history_key_lst order)
    history_id: int
    thumb_filepath: Path


class LibraryRepository(Protocol):
    """Use-case level operations. Every call may block; run writes off the GUI thread
    once a network adapter exists (local SQLite finishes in milliseconds)."""

    def ensure_user(self, user: str) -> None: ...
    def revision(self) -> int: ...
    def list_assets(
        self, owner: str | None = None, category: str | None = None
    ) -> list[AssetData]: ...
    def categories(self, owner: str | None = None) -> list[str]: ...
    def histories(
        self, asset_id: int | None, owner: str | None = None, search_date: Any = None
    ) -> list[HistoryData]: ...
    def history_videos(self, asset_id: int) -> list[Path]: ...
    def asset_icons(self, owner: str | None = None) -> list[Any]: ...
    def history_thumbnails(self, owner: str | None = None) -> list[Any]: ...
    def video_matches_version(self, asset_id: int, version: str) -> bool: ...
    def is_latest_history(self, asset_id: int, history_id: int) -> bool: ...
    def is_latest_version(self, asset_id: int, version: str) -> bool: ...
    def search_asset_ids(
        self,
        query: str,
        *,
        field: str = "All",
        case_sensitive: bool = False,
        limit: int = 5000,
        cancel: threading.Event | None = None,
    ) -> list[int]: ...
    def distinct_tags(self, owner: str | None = None) -> list[str]: ...
    def register_asset(self, payload: RegistrationPayload) -> RegistrationResult: ...
    def add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult: ...
    def set_note(self, asset_id: int, note: str) -> None: ...
    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None: ...
    def toggle_favorite(self, asset_id: int) -> bool: ...
    def rename_asset(self, plan: RenamePlan) -> tuple[int, int]: ...
    def delete_asset(self, asset_id: int, directory: Path) -> None: ...
    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None: ...
