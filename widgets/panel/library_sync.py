"""Keep the panel in step with a library other panels or users are changing.

A small poller compares the repository revision every few seconds and reloads
the in-memory rows when it moves; the toolbar Reload action runs the same path.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtCore

from libs import log_handler
from libs.library_backups import auto_backup
from model.asset_notifications import QtAssetNotifications
from widgets.panel.sync_presenter import LibrarySyncPresenter
from widgets.team_library.executor import WorkspaceTaskExecutor

SYNC_INTERVAL_MS = 10_000


class PanelLibrarySync:
    def __init__(self, window: Any) -> None:
        self.window = window

    def _init_library_sync(self) -> None:
        window = self.window
        # Own controller: polling must never share the archive/encoder busy gate.
        window._sync_tasks = window._services.tasks(window)
        window._library_sync_presenter = LibrarySyncPresenter(
            self,
            WorkspaceTaskExecutor(window._sync_tasks),
            window._repository.revision() if window._repository is not None else 0,
        )
        window._sync_timer = QtCore.QTimer(window)
        window._sync_timer.setInterval(SYNC_INTERVAL_MS)
        window._sync_timer.timeout.connect(self._poll_library_revision)
        window._sync_timer.start()
        # Completion callbacks run while the controller is still busy, so a reload
        # requested by a poll waits for idle instead of being dropped.
        window._sync_tasks.idle.connect(self._sync_idle)
        window._sync_tasks.result.connect(self._sync_result)
        window.actionReload.triggered.connect(self.reload_library)
        library = window._library
        if library is not None and library.db_filepath.is_file():
            database = library.db_filepath
            window._sync_tasks.start(
                lambda: auto_backup(database), self._auto_backup_done
            )

    def _auto_backup_done(self, path: Any) -> None:
        if path is not None:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg=f"daily database backup written: {path}"
            )

    def _stop_library_sync(self) -> None:
        window = self.window
        presenter = getattr(window, "_library_sync_presenter", None)
        if presenter is not None:
            presenter.close()
        timer = getattr(window, "_sync_timer", None)
        if timer is not None:
            timer.stop()
        tasks = getattr(window, "_sync_tasks", None)
        if tasks is not None:
            tasks.drain()

    @QtCore.Slot()
    def _poll_library_revision(self) -> None:
        window = self.window
        repository = window._repository
        if (
            repository is None
            or window._closing
            or window._tasks.busy
            or window._details.busy
            or window._sync_tasks.busy
        ):
            return
        if self._reload_pending:
            window._library_sync_presenter.refresh()
        else:
            window._sync_tasks.start(repository.revision, self._revision_polled)

    def _revision_polled(self, revision: Any) -> None:
        window = self.window
        window._library_sync_presenter.revision_polled(revision)

    @QtCore.Slot()
    def _sync_idle(self) -> None:
        window = self.window
        window._library_sync_presenter.idle()

    @QtCore.Slot(object, object)
    def _sync_result(self, value: Any, error: Any) -> None:
        if error is not None:
            self._reload_pending = False
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg=f"library sync failed: {error}"
            )

    @property
    def _known_revision(self) -> int:
        window = self.window
        return window._library_sync_presenter.known_revision

    @_known_revision.setter
    def _known_revision(self, value: int) -> None:
        window = self.window
        window._library_sync_presenter.known_revision = value

    @property
    def _reload_pending(self) -> bool:
        window = self.window
        return window._library_sync_presenter.pending

    @_reload_pending.setter
    def _reload_pending(self, value: bool) -> None:
        window = self.window
        window._library_sync_presenter.pending = value

    @QtCore.Slot()
    def reload_library(self) -> None:
        window = self.window
        window._panel_library.refresh()

    def sync_allowed(self) -> bool:
        window = self.window
        return (
            not window._closing and not window._tasks.busy and not window._details.busy
        )

    def sync_context(self) -> tuple[object, int]:
        window = self.window
        return window._repository, window._details.presenter.write_generation

    def read_snapshot(self) -> Any:
        window = self.window
        repository, owner = window._repository, window._user
        if repository is None:
            return None

        def snapshot() -> tuple[Any, ...]:
            return (
                repository.revision(),
                repository.list_assets(owner=owner),
                repository.categories(owner=owner),
                repository.histories(None, owner=owner),
                repository.asset_icons(owner=owner),
                repository.history_thumbnails(owner=owner),
            )

        return snapshot

    def show_snapshot(self, snapshot: tuple[Any, ...]) -> None:
        self._apply_library_snapshot(snapshot)

    def show_sync_error(self, message: str) -> None:
        log_handler.LogHandler.log_msg(
            method=logging.warning, msg=f"library sync failed: {message}"
        )

    def _apply_library_snapshot(self, snapshot: tuple[Any, ...]) -> None:
        window = self.window
        revision, rows, categories, histories, icons, hist_thumbs = snapshot
        window._library_sync_presenter.accept(snapshot)
        window._panel_selection.restore(rows, histories)
        history_filter = window.comboBox__hist_ihda_node.currentData()
        # Model resets emit selection signals synchronously. Restore view selection
        # only after every model has installed the new rows.
        selection_blockers = [
            QtCore.QSignalBlocker(view.selectionModel())
            for view in (
                window._ihda_list_view,
                window._ihda_table_view,
                window._ihda_history_view,
                window._ihda_category_view,
            )
        ]
        history_blocker = QtCore.QSignalBlocker(window.comboBox__hist_ihda_node)
        icons_cache = window._ihda_icons
        icons_cache.make_pixmap_ihda_data(icon_info=icons)
        icons_cache.make_pixmap_cate_data(cate_lst=categories)
        icons_cache.make_pixmap_thumbnail_data(all_data=rows)
        icons_cache.make_pixmap_hist_thumbnail_data(all_data=hist_thumbs)
        window._assets.observe(
            QtAssetNotifications(window._ihda_list_model, window._ihda_table_model)
        )
        window._assets.reset(rows)
        window._ihda_category_model.clear_item()
        window._ihda_category_model.add_item(dict.fromkeys(categories))
        window._ihda_category_model.reload()
        window._ihda_category_view.expandAll()
        window._ihda_history_model.reload(histories)
        window._default_set_hist_ihda_combobox()
        for row in rows:
            window._set_hist_ihda_to_combobox(
                hkey_id=row["hda_id"], hda_name=row["hda_name"]
            )
        filter_index = window.comboBox__hist_ihda_node.findData(history_filter)
        window.comboBox__hist_ihda_node.setCurrentIndex(
            filter_index if filter_index >= 0 else 0
        )
        del history_blocker
        window._ihda_history_proxy_model.set_hda_id(
            window.comboBox__hist_ihda_node.currentData()
        )
        window._restore_panel_selection()
        del selection_blockers
        window._set_hda_info_to_parms()
        window._set_hda_hist_info_to_parms()
        window._refresh_asset_search()
        window.label__hda_count.setText(str(window._ihda_list_proxy_model.rowCount()))
        window.label__cate_count.setText(str(window._get_category_count()))
        window.label__hist_cnt.setText(str(window._ihda_history_proxy_model.rowCount()))
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg=f"library reloaded ({len(rows)} assets)"
        )
