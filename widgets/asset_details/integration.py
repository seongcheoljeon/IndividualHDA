"""Qt adapter for the existing named note/tag controls and shared item models."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs.debounce import DebouncedText
from libs.task_controller import TaskController
from widgets.asset_details.presenter import (
    AssetDetailsPresenter,
    Field,
    MetadataGateway,
)
from widgets.tag_editor import TagEditor


@dataclass(frozen=True, slots=True, kw_only=True)
class DetailsBindings:
    note: QtWidgets.QTextEdit
    tags: TagEditor
    status: QtWidgets.QLabel
    tag_status: QtWidgets.QLabel
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
    def __init__(
        self,
        bindings: DetailsBindings,
        tasks: TaskController,
        *,
        autosave_delay_ms: int = 1500,
    ) -> None:
        self.bindings = bindings
        self._tasks = tasks
        self.presenter = AssetDetailsPresenter(self, MetadataSaveExecutor(tasks))
        self.presenter.autosave = True
        self._autosave = DebouncedText(
            lambda _: self.flush(), tasks, delay=autosave_delay_ms
        )
        self.label__metadata_status = bindings.status
        self._save_error = ""
        self._saved_recently = False
        self._library_identity: object = None
        self._vocabulary: Callable[[], Sequence[str]] | None = None
        bindings.note.textChanged.connect(self._edited)
        bindings.tags.changed.connect(self._edited)

    def change_repository(
        self,
        repository: MetadataGateway | None,
        identity: object,
        *,
        vocabulary: Callable[[], Sequence[str]] | None = None,
    ) -> None:
        self.flush()
        self._tasks.drain()
        self.presenter.change_gateway(
            repository, preserve_drafts=identity == self._library_identity
        )
        self._library_identity = identity
        self._vocabulary = vocabulary if repository is not None else None
        self._refresh_vocabulary()

    def _refresh_vocabulary(self) -> None:
        """Completer words come from the library; failures only cost suggestions."""
        words: Sequence[str] = ()
        if self._vocabulary is not None:
            try:
                words = self._vocabulary()
            except Exception as error:
                logging.warning("Tag vocabulary unavailable: %s", error)
        self.bindings.tags.setVocabulary(words)

    def _edited(self) -> None:
        self._saved_recently = False
        self.presenter.edit(self.bindings.note.toPlainText(), self.bindings.tags.tags())
        self._autosave.submit("")

    def flush(self) -> None:
        """Write pending edits now (Ctrl+S, selection change, library switch, close)."""
        self._autosave.timer.stop()
        self.presenter.save_pending()

    def show_draft(self, note: str, tags: Sequence[str]) -> None:
        bindings = self.bindings
        with (
            QtCore.QSignalBlocker(bindings.note),
            QtCore.QSignalBlocker(bindings.tags),
        ):
            bindings.note.setPlainText(note)
            bindings.tags.setTags(tags)
        bindings.show_tags(list(tags))
        self._saved_recently = False

    def show_state(self, note_dirty: bool, tag_dirty: bool, saving: bool) -> None:
        if saving:
            self._save_error = ""
        self.label__metadata_status.setText(
            "Saving…"
            if saving
            else "Save failed — edits retained"
            if self._save_error
            else "Unsaved"
            if note_dirty
            else "Saved · just now"
            if self._saved_recently and not tag_dirty
            else ""
        )
        # Tag label carries dirtiness only. "Saving…" and save errors stay on the
        # shared line; repeating them here is the contention this split removes.
        self.bindings.tag_status.setText("Unsaved" if tag_dirty else "")

    def show_error(self, message: str) -> None:
        self._save_error = message
        logging.error("Could not save asset details: %s", message)
        self.label__metadata_status.setToolTip(message)

    def saved(self, asset_id: int, field: Field, value: str | list[str]) -> None:
        self.bindings.saved(asset_id, field, value)
        logging.info("Asset %s %s saved", asset_id, field)
        self._saved_recently = True
        if field == "tag":
            self._refresh_vocabulary()

    @property
    def busy(self) -> bool:
        return self._tasks.busy

    def suspend(self) -> None:
        """Finish local saves and detach selection while keeping personal drafts."""
        self.flush()
        self._tasks.drain()
        self.presenter.select(None)

    def close(self) -> None:
        self.flush()
        self._tasks.drain()
