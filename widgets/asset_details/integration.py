"""Qt adapter for the existing named note/tag controls and shared item models."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs.tags import normalize_tags
from libs.task_controller import TaskController
from widgets.asset_details.presenter import (
    AssetDetailsPresenter,
    Field,
    MetadataGateway,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class DetailsBindings:
    note: QtWidgets.QTextEdit
    tags: QtWidgets.QTextEdit
    status: QtWidgets.QLabel
    show_tags: Callable[[list[str]], None]
    saved: Callable[[int, Field, str | list[str]], None]


class MetadataSaveExecutor:
    def __init__(self, tasks: TaskController) -> None:
        self._tasks = tasks
        self._finished: Callable[[Exception | None], None] | None = None
        tasks.result.connect(self._result)

    def submit(
        self,
        operation: Callable[[], None],
        finished: Callable[[Exception | None], None],
    ) -> bool:
        if self._tasks.busy:
            return False
        self._finished = finished
        try:
            return self._tasks.start(operation, lambda _: None)
        except Exception:
            self._finished = None
            raise

    def _result(self, value: Any, error: Exception | None) -> None:
        finished, self._finished = self._finished, None
        if finished is not None:
            finished(error)


class AssetDetailsIntegration:
    def __init__(self, bindings: DetailsBindings, tasks: TaskController) -> None:
        self.bindings = bindings
        self._tasks = tasks
        self.presenter = AssetDetailsPresenter(self, MetadataSaveExecutor(tasks))
        self.label__metadata_status = bindings.status
        self._save_error = ""
        self._library_identity: object = None
        bindings.note.textChanged.connect(self._edited)
        bindings.tags.textChanged.connect(self._edited)

    def change_repository(
        self, repository: MetadataGateway | None, identity: object
    ) -> None:
        self._tasks.drain()
        self.presenter.change_gateway(
            repository, preserve_drafts=identity == self._library_identity
        )
        self._library_identity = identity

    def _edited(self) -> None:
        self.presenter.edit(
            self.bindings.note.toPlainText(),
            self.bindings.tags.toPlainText(),
        )

    def show_draft(self, note: str, tags: str) -> None:
        bindings = self.bindings
        with (
            QtCore.QSignalBlocker(bindings.note),
            QtCore.QSignalBlocker(bindings.tags),
        ):
            bindings.note.setPlainText(note)
            bindings.tags.setPlainText(tags)
        bindings.show_tags(normalize_tags(tags))

    def show_state(self, dirty: bool, saving: bool) -> None:
        if saving:
            self._save_error = ""
        self.label__metadata_status.setText(
            "Saving…"
            if saving
            else "Save failed — edits retained"
            if self._save_error
            else "Unsaved changes"
            if dirty
            else ""
        )

    def show_error(self, message: str) -> None:
        self._save_error = message
        logging.error("Could not save asset details: %s", message)
        self.label__metadata_status.setToolTip(message)

    def saved(self, asset_id: int, field: Field, value: str | list[str]) -> None:
        self.bindings.saved(asset_id, field, value)
        logging.info("Asset %s %s saved", asset_id, field)

    @property
    def busy(self) -> bool:
        return self._tasks.busy

    def suspend(self) -> None:
        """Finish local saves and detach selection while keeping personal drafts."""
        self._tasks.drain()
        self.presenter.select(None)

    def close(self) -> None:
        self._tasks.drain()
