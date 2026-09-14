"""Composition root: select concrete adapters here, inject them into the panel."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QObject
from libs.ai_provider import AIProvider, AISettings, make_provider
from libs.archive_transfer import ArchiveTransfer
from libs.asset_rename import AssetNames, RenameRepository
from libs.database.rename_repository import SQLiteRenameRepository
from libs.houdini_api import HoudiniAPI
from libs.library_reader import LibraryReader
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.task_controller import TaskController


@dataclass(frozen=True, slots=True)
class PanelServices:
    open_database: Callable[[Path], SQLite3DatabaseAPI] = SQLite3DatabaseAPI
    archives: Callable[[Path, Path], ArchiveTransfer] = ArchiveTransfer
    tasks: Callable[[QObject], TaskController] = TaskController
    names: AssetNames = HoudiniAPI
    rename_repository: Callable[[SQLite3DatabaseAPI], RenameRepository] = (
        SQLiteRenameRepository
    )
    ai: Callable[[AISettings], AIProvider] = make_provider

    def reader(self) -> LibraryReader:
        return LibraryReader(self.open_database)
