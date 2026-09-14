"""Translate the rename use case into the existing SQLite domain operations."""

from __future__ import annotations
from contextlib import AbstractContextManager
from pathlib import Path
from libs.asset_rename import RenamePlan
from libs.sqlite3_db_api import SQLite3DatabaseAPI


class SQLiteRenameRepository:
    def __init__(self, database: SQLite3DatabaseAPI) -> None:
        self.database = database

    @property
    def db_filepath(self) -> Path:
        return self.database.db_filepath

    @property
    def in_transaction(self) -> bool:
        return self.database.in_transaction

    def transaction(self) -> AbstractContextManager[object]:
        return self.database.transaction()

    def record_operation_commit(self, operation_id: str) -> None:
        self.database.record_operation_commit(operation_id)

    def apply_rename(self, plan: RenamePlan) -> tuple[int, int]:
        asset_rows = self.database.update_hda_name(
            hda_key_id=plan.asset_id,
            name=plan.name,
            filename=plan.filename,
            dirpath=plan.directory,
            node_old_path=plan.node_path,
            thumbnail_dirpath=plan.thumbnail_directory,
            thumbnail_filename=plan.thumbnail_filename,
            video_dirpath=plan.video_directory,
            video_filename=plan.video_filename,
        )
        history_rows = self.database.update_hda_name_to_history(
            hda_key_id=plan.asset_id,
            hda_version=plan.version,
            hda_filename=plan.filename,
            hda_dirpath=plan.directory,
            thumb_dirpath=plan.thumbnail_directory,
            thumb_filename=plan.thumbnail_filename,
            video_dirpath=plan.video_directory,
            video_filename=plan.video_filename,
            path_moves=plan.moves,
        )
        if asset_rows is None or history_rows is None:
            raise RuntimeError("Database rejected the asset rename")
        return asset_rows, history_rows
