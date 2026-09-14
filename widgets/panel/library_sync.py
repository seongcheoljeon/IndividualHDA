"""Keep the panel in step with a library other panels or users are changing.

A small poller compares the repository revision every few seconds and reloads
the in-memory rows when it moves; the toolbar Reload action runs the same path.
"""

from __future__ import annotations

from typing import Any
import logging

from PySide6 import QtCore

from libs import log_handler
from model.asset_notifications import QtAssetNotifications

SYNC_INTERVAL_MS = 10_000


class LibrarySyncMixin:
    def _init_library_sync(self) -> None:
        # Own controller: polling must never share the archive/encoder busy gate.
        self._sync_tasks = self._services.tasks(self)
        self._reload_pending = False
        self._known_revision = (
            self._repository.revision() if self._repository is not None else 0
        )
        self._sync_timer = QtCore.QTimer(self)
        self._sync_timer.setInterval(SYNC_INTERVAL_MS)
        self._sync_timer.timeout.connect(self._poll_library_revision)
        self._sync_timer.start()
        # Completion callbacks run while the controller is still busy, so a reload
        # requested by a poll waits for idle instead of being dropped.
        self._sync_tasks.idle.connect(self._sync_idle)
        self._sync_tasks.result.connect(self._sync_result)
        self.actionReload.triggered.connect(self.reload_library)

    def _stop_library_sync(self) -> None:
        self._sync_timer.stop()
        self._sync_tasks.drain()

    @QtCore.Slot()
    def _poll_library_revision(self) -> None:
        repository = self._repository
        if (
            repository is None
            or self._closing
            or self._tasks.busy
            or self._sync_tasks.busy
        ):
            return
        self._sync_tasks.start(repository.revision, self._revision_polled)

    def _revision_polled(self, revision: Any) -> None:
        if revision != self._known_revision:
            self._reload_pending = True

    @QtCore.Slot()
    def _sync_idle(self) -> None:
        if self._reload_pending and not self._closing:
            self.reload_library()

    @QtCore.Slot(object, object)
    def _sync_result(self, value: Any, error: Any) -> None:
        if error is not None:
            self._reload_pending = False
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg=f"library sync failed: {error}"
            )

    @QtCore.Slot()
    def reload_library(self) -> None:
        """Re-read rows, categories, histories and icons; keep the selection if it survives."""
        repository = self._repository
        if repository is None or self._closing or self._tasks.busy:
            return
        owner = self._user

        def snapshot() -> tuple[Any, ...]:
            return (
                repository.revision(),
                repository.list_assets(owner=owner),
                repository.categories(owner=owner),
                repository.histories(None, owner=owner),
                repository.asset_icons(owner=owner),
                repository.history_thumbnails(owner=owner),
            )

        # A poll may be in flight; _sync_idle retries once it reports back.
        self._reload_pending = not self._sync_tasks.start(
            snapshot, self._apply_library_snapshot
        )

    def _apply_library_snapshot(self, snapshot: tuple[Any, ...]) -> None:
        revision, rows, categories, histories, icons, hist_thumbs = snapshot
        self._reload_pending = False
        self._known_revision = revision
        selected_id = self._selection.asset.id
        icons_cache = self._ihda_icons
        icons_cache.make_pixmap_ihda_data(icon_info=icons)
        icons_cache.make_pixmap_cate_data(cate_lst=categories)
        icons_cache.make_pixmap_thumbnail_data(all_data=rows)
        icons_cache.make_pixmap_hist_thumbnail_data(all_data=hist_thumbs)
        self._assets.observe(
            QtAssetNotifications(self._ihda_list_model, self._ihda_table_model)
        )
        self._assets.reset(rows)
        self._ihda_category_model.clear_item()
        self._ihda_category_model.add_item(dict.fromkeys(categories))
        self._ihda_category_model.reload()
        self._ihda_category_view.expandAll()
        self._ihda_history_model.reload(histories)
        self.comboBox__hist_ihda_node.clear()
        for row in rows:
            self._set_hist_ihda_to_combobox(
                hkey_id=row["hda_id"], hda_name=row["hda_name"]
            )
        row_index = (
            self._assets.id_rows.get(selected_id) if selected_id is not None else None
        )
        if row_index is None:
            self._initialize_current_attribs()
            self._initialize_hist_current_attribs()
            self._clear_parms()
            self._clear_hist_parms()
        else:
            self._selection.asset.row = row_index
            self._selection.asset.data = self._assets.rows[row_index]
        self._refresh_asset_search()
        self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self._get_category_count()))
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg=f"library reloaded ({len(rows)} assets)"
        )
