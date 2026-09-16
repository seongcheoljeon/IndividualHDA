"""Qt adapter for the existing named note/tag controls and shared item models."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

from libs.keys import Key
from libs.task_controller import TaskController
from widgets.asset_details.presenter import (
    AssetDetailsPresenter,
    Field,
    MetadataGateway,
)


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
    def __init__(self, window: Any, tasks: TaskController) -> None:
        self._window = window
        self._tasks = tasks
        self.presenter = AssetDetailsPresenter(self, MetadataSaveExecutor(tasks))
        self.label__metadata_status = window.label__metadata_status
        self._save_error = ""
        self._library_identity: object = None
        window.textEdit__note.textChanged.connect(self._edited)
        window.textEdit__tag.textChanged.connect(self._edited)

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
            self._window.textEdit__note.toPlainText(),
            self._window.textEdit__tag.toPlainText(),
        )

    def show_draft(self, note: str, tags: str) -> None:
        window = self._window
        with (
            QtCore.QSignalBlocker(window.textEdit__note),
            QtCore.QSignalBlocker(window.textEdit__tag),
        ):
            window.textEdit__note.setPlainText(note)
            window.textEdit__tag.setPlainText(tags)
        window._set_label_tags(window._split_tag_string(tags))

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
        window = self._window
        row = window._assets.id_rows.get(asset_id)
        if row is None:
            return
        window._change_hda_data(
            row=row, key=Key.hda_note if field == "note" else Key.hda_tags, val=value
        )
        if field == "tag":
            window._ihda_history_model.update_item_data_by_hkey_id_from_model(
                hkey_id=asset_id, key=Key.History.tags, val=value
            )
            if window._selection.asset.id == asset_id:
                window._set_label_tags(value)
        window._refresh_asset_search()
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
