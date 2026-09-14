"""Compatibility facade for callers that still request archive file dialogs.

Panel code uses ArchiveTransfer directly; Qt is imported only for legacy dialogs.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from libs.archive_transfer import ArchiveTransfer

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class DataStream:
    def __init__(
        self,
        userid: str | None = None,
        hda_base_dirpath: Path | None = None,
        data_dirpath: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        if hda_base_dirpath is None or data_dirpath is None:
            raise ValueError("Library and data directories are required")
        self.user = userid
        self.parent = parent
        self._transfer = ArchiveTransfer(hda_base_dirpath, data_dirpath)

    @property
    def assets(self) -> Path:
        return self._transfer.assets

    @property
    def directory(self) -> Path:
        return self._transfer.directory

    @property
    def stage(self) -> Path | None:
        return self._transfer.stage

    @stage.setter
    def stage(self, value: Path | None) -> None:
        self._transfer.stage = value

    def create_backup_file(self) -> Path | None:
        return self._transfer.create_backup_file()

    def import_ihda_data(self, source: str | Path | None = None) -> Path | None:
        if source is None:
            from PySide6.QtWidgets import QFileDialog

            source, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Select Import iHDA Data File",
                str(Path.home()),
                "iHDA file (*.zip *.ZIP)",
            )
        return self._transfer.import_ihda_data(source) if source else None

    def export_ihda_data(self, destination: str | Path | None = None) -> Path | None:
        if destination is None:
            from PySide6.QtWidgets import QFileDialog

            destination = QFileDialog.getExistingDirectory(
                self.parent, "Select Export Directory", str(Path.home())
            )
        return self._transfer.export_ihda_data(destination) if destination else None

    def discard_import(self) -> None:
        self._transfer.discard_import()

    def commit_import(self) -> None:
        self._transfer.commit_import()
