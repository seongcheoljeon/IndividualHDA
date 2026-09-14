"""File/DB asset commands. Qt views update only after these transactions commit."""

from __future__ import annotations
from pathlib import Path
import uuid
from libs.operation_journal import durable_operation
from libs.contracts import (
    AssetDeletionRepository,
    HistoryDeletionRepository,
    OperationFactory,
)


def delete_asset(
    db: AssetDeletionRepository,
    asset_id: int,
    directory: Path,
    *,
    operations: OperationFactory = durable_operation,
) -> None:
    with operations(db.db_filepath.parent, db) as journal:
        if directory.exists():
            journal.move(
                directory,
                directory.with_name(
                    f".ihda-deleted-{uuid.uuid4().hex}-{directory.name}"
                ),
            )
        if db.delete_hda_key_with_id(hda_key_id=asset_id) != 1:
            raise RuntimeError("Asset was not deleted from database")


def delete_history(
    db: HistoryDeletionRepository,
    asset_id: int,
    history_id: int,
    files: list[Path],
    *,
    operations: OperationFactory = durable_operation,
) -> None:
    with operations(db.db_filepath.parent, db) as journal:
        if db.is_most_recent_ihda_history(hda_key_id=asset_id, hist_id=history_id):
            raise ValueError("The most recent history cannot be deleted")
        for path in dict.fromkeys(files):
            if path.exists() and not db.is_library_file_referenced(path, history_id):
                journal.move(
                    path,
                    path.with_name(f".ihda-deleted-{uuid.uuid4().hex}-{path.name}"),
                )
        if db.delete_hda_history(hda_key_id=asset_id, hist_id=history_id) != 1:
            raise RuntimeError("History was not deleted from database")
