"""Composition root: select concrete adapters here, inject them into the panel."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject

from libs.ai_provider import AIProvider, AISettings, make_provider
from libs.archive_transfer import ArchiveTransfer
from libs.asset_rename import AssetNames
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.domain import LibraryContext
from libs.houdini_api import HoudiniAPI
from libs.repository import LibraryRepository, LibrarySettings
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.task_controller import TaskController


@dataclass(frozen=True, slots=True)
class PanelServices:
    settings: LibrarySettings = LibrarySettings()
    open_database: Callable[[Path], SQLite3DatabaseAPI] = SQLite3DatabaseAPI
    archives: Callable[[Path, Path], ArchiveTransfer] = ArchiveTransfer
    tasks: Callable[[QObject], TaskController] = TaskController
    names: AssetNames = HoudiniAPI
    ai: Callable[[AISettings], AIProvider] = make_provider

    def repository(self, context: LibraryContext | None) -> LibraryRepository | None:
        """Storage adapter for this session; None until a data directory is chosen."""
        if context is None:
            return None
        # ponytail: settings.mode == "server" dispatches to the HTTP adapter in Phase 2.
        return SqliteLibraryRepository(context.db_filepath, self.open_database)
