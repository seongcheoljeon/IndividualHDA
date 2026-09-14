"""Archive application service: explicit paths in, results out; no dialogs."""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from libs.archive_service import create_archive, extract_archive, prepare_database
from libs.contracts import OperationFactory
from libs.operation_journal import durable_operation, sync_tree


class ArchiveTransfer:
    def __init__(
        self,
        assets: Path,
        directory: Path,
        *,
        operations: OperationFactory = durable_operation,
    ) -> None:
        self.assets = Path(assets)
        self.directory = Path(directory)
        self.stage: Path | None = None
        self._operations = operations

    def create_backup_file(self) -> Path | None:
        stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
        output = self.directory / "backup" / f"bak_data_{stamp}_iHDA.zip"
        try:
            return create_archive(self.directory / "ihda.db", self.assets, output)
        except (OSError, ValueError) as error:
            logging.error("Could not back up library: %s", error)
            return None

    def import_ihda_data(self, source: str | Path) -> Path:
        if self.stage is not None:
            raise RuntimeError("An import is already staged")
        self.stage = Path(tempfile.mkdtemp(prefix=".ihda-import-", dir=self.directory))
        try:
            extract_archive(source, self.stage)
            prepare_database(self.stage, self.assets)
            sync_tree(self.stage)
            backup = self.create_backup_file()
            if backup is None:
                raise OSError("Cannot import without backing up the existing library")
            return backup
        except BaseException:
            try:
                self.discard_import()
            except OSError:
                logging.exception(
                    "Could not remove failed import staging directory: %s", self.stage
                )
            raise

    def discard_import(self) -> None:
        if self.stage is not None:
            shutil.rmtree(self.stage)
            self.stage = None

    def commit_import(self) -> None:
        """Switch on panel close; retain old files and roll back any failed rename."""
        if self.stage is None:
            return
        database = self.directory / "ihda.db"
        token = uuid.uuid4().hex
        old_assets = self.assets.with_name(self.assets.name + ".previous-" + token)
        old_db = database.with_name(database.name + ".previous-" + token)
        staged_db = self.stage / "ihda.db"
        self.assets.parent.mkdir(parents=True, exist_ok=True)
        with self._operations(self.directory) as journal:
            if self.assets.exists():
                journal.move(self.assets, old_assets)
            journal.move(database, old_db)
            journal.move(staged_db, database)
            journal.move(self.stage, self.assets)
        self.stage = None
        # Recovery copies intentionally remain alongside the library.
        logging.info(
            "Imported library activated; previous files retained at %s and %s",
            old_assets,
            old_db,
        )

    def export_ihda_data(self, destination: str | Path) -> Path:
        destination = Path(destination)
        stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
        create_archive(
            self.directory / "ihda.db", self.assets, destination / f"{stamp}_iHDA.zip"
        )
        return destination
