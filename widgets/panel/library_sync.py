"""Keep the panel in step with a library other panels or users are changing.

A small poller compares the repository revision every few seconds and reloads
the in-memory rows when it moves; the toolbar Reload action runs the same path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets

from libs import log_handler
from libs.asset_contracts import LibrarySnapshot, SyncContext
from libs.history_activity import merge_history_rows
from libs.library_backups import auto_backup
from model.asset_notifications import QtAssetNotifications
from widgets.panel.sync_presenter import LibrarySyncPresenter
from widgets.team_library.executor import WorkspaceTaskExecutor

if TYPE_CHECKING:
    from libs.ihda_icons import IHDAIcons
    from libs.task_controller import TaskController
    from widgets.asset_details.integration import AssetDetailsIntegration
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.model_binding import PanelModelBinding
    from widgets.panel.notes import PanelNotes
    from widgets.panel.selection import PanelSelection
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState, PanelStatus, PanelViews


@dataclass(frozen=True, slots=True)
class PanelLibrarySyncBindings:
    details: AssetDetailsIntegration
    icons: IHDAIcons
    models: PanelModelBinding
    notes: PanelNotes
    parent: QtWidgets.QWidget
    selection: PanelSelection
    services: PanelServices
    session: PanelSessionState
    status: PanelStatus
    tasks: TaskController
    ui: MainWindowLayout
    views: PanelViews


class PanelLibrarySync:
    bindings: PanelLibrarySyncBindings

    def _init_library_sync(self) -> None:
        # Own controller: polling must never share the archive/encoder busy gate.
        self.tasks = self.bindings.services.tasks(self.bindings.parent)
        self.presenter = LibrarySyncPresenter(
            self,
            WorkspaceTaskExecutor(self.tasks),
            self.bindings.session.require_repository().revision()
            if self.bindings.session.repository is not None
            else 0,
        )
        self.timer = QtCore.QTimer(self.bindings.parent)
        self.timer.setInterval(self.bindings.services.policy.sync_interval_ms)
        self.timer.timeout.connect(self._poll_library_revision)
        self.timer.start()
        # Completion callbacks run while the controller is still busy, so a reload
        # requested by a poll waits for idle instead of being dropped.
        self.tasks.idle.connect(self._sync_idle)
        self.tasks.result.connect(self._sync_result)
        self.bindings.ui.actionReload.triggered.connect(self.reload_library)
        library = self.bindings.session.context
        if library is not None and library.db_filepath.is_file():
            database = library.db_filepath
            self.tasks.start(lambda: auto_backup(database), self._auto_backup_done)

    def _auto_backup_done(self, path: Any) -> None:
        if path is not None:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg=f"daily database backup written: {path}"
            )

    def _stop_library_sync(self) -> None:
        presenter = getattr(self, "presenter", None)
        if presenter is not None:
            presenter.close()
        timer = getattr(self, "timer", None)
        if timer is not None:
            timer.stop()
        tasks = getattr(self, "tasks", None)
        if tasks is not None:
            tasks.drain()

    @QtCore.Slot()
    def _poll_library_revision(self) -> None:
        repository = self.bindings.session.repository
        if (
            repository is None
            or self.bindings.status.closing
            or self.bindings.tasks.busy
            or self.bindings.details.busy
            or self.tasks.busy
        ):
            return
        if self._reload_pending:
            self.presenter.refresh()
        else:
            self.tasks.start(repository.revision, self._revision_polled)

    def _revision_polled(self, revision: Any) -> None:
        self.presenter.revision_polled(revision)

    @QtCore.Slot()
    def _sync_idle(self) -> None:
        self.presenter.idle()

    @QtCore.Slot(object, object)
    def _sync_result(self, value: Any, error: Any) -> None:
        if error is not None:
            self._reload_pending = False
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg=f"library sync failed: {error}"
            )

    @property
    def _known_revision(self) -> int:
        return self.presenter.known_revision

    @_known_revision.setter
    def _known_revision(self, value: int) -> None:
        self.presenter.known_revision = value

    @property
    def _reload_pending(self) -> bool:
        return self.presenter.pending

    @_reload_pending.setter
    def _reload_pending(self, value: bool) -> None:
        self.presenter.pending = value

    @QtCore.Slot()
    def reload_library(self) -> None:
        self.bindings.session.actions.refresh()

    def sync_allowed(self) -> bool:
        return (
            not self.bindings.status.closing
            and not self.bindings.tasks.busy
            and not self.bindings.details.busy
        )

    def sync_context(self) -> SyncContext:
        return SyncContext(
            repository=self.bindings.session.repository,
            write_generation=self.bindings.details.presenter.write_generation,
        )

    def read_snapshot(self) -> Any:
        repository, owner = self.bindings.session.repository, self.bindings.session.user
        if repository is None:
            return None

        def snapshot() -> LibrarySnapshot:
            return LibrarySnapshot(
                revision=repository.revision(),
                assets=tuple(repository.list_assets(owner=owner)),
                categories=tuple(repository.categories(owner=owner)),
                histories=tuple(
                    merge_history_rows(
                        repository.histories(None, owner=owner),
                        repository.activity(owner=owner),
                    )
                ),
                icons=tuple(repository.asset_icons(owner=owner)),
                history_thumbnails=tuple(repository.history_thumbnails(owner=owner)),
            )

        return snapshot

    def show_snapshot(self, snapshot: LibrarySnapshot) -> None:
        self._apply_library_snapshot(snapshot)

    def show_sync_error(self, message: str) -> None:
        log_handler.LogHandler.log_msg(
            method=logging.warning, msg=f"library sync failed: {message}"
        )

    def _apply_library_snapshot(self, snapshot: LibrarySnapshot) -> None:
        rows = list(snapshot.assets)
        categories = list(snapshot.categories)
        histories = list(snapshot.histories)
        icons = snapshot.icons
        hist_thumbs = snapshot.history_thumbnails
        self.presenter.accept(snapshot)
        self.bindings.selection.presenter.restore(rows, histories)
        history_filter = self.bindings.ui.comboBox__hist_ihda_node.currentData()
        # Model resets emit selection signals synchronously. Restore view selection
        # only after every model has installed the new rows.
        selection_blockers = [
            QtCore.QSignalBlocker(view.selectionModel())
            for view in (
                self.bindings.views.assets_list,
                self.bindings.views.assets_table,
                self.bindings.views.history,
                self.bindings.views.category,
            )
        ]
        history_blocker = QtCore.QSignalBlocker(
            self.bindings.ui.comboBox__hist_ihda_node
        )
        icons_cache = self.bindings.icons
        icons_cache.make_pixmap_ihda_data(icon_info=icons)
        icons_cache.make_pixmap_cate_data(cate_lst=categories)
        icons_cache.make_pixmap_thumbnail_data(all_data=rows)
        icons_cache.make_pixmap_hist_thumbnail_data(all_data=hist_thumbs)
        self.bindings.models.assets.observe(
            QtAssetNotifications(
                self.bindings.models.list_model, self.bindings.models.table_model
            )
        )
        self.bindings.models.assets.reset(rows)
        self.bindings.models.category_model.clear_item()
        self.bindings.models.category_model.add_item(dict.fromkeys(categories))
        self.bindings.models.category_model.reload()
        self.bindings.views.category.expandAll()
        self.bindings.models.history_model.reload(histories)
        self.bindings.selection._default_set_hist_ihda_combobox()
        for row in rows:
            self.bindings.selection._set_hist_ihda_to_combobox(
                hkey_id=row.hda_id, hda_name=row.hda_name
            )
        filter_index = self.bindings.ui.comboBox__hist_ihda_node.findData(
            history_filter
        )
        self.bindings.ui.comboBox__hist_ihda_node.setCurrentIndex(
            filter_index if filter_index >= 0 else 0
        )
        del history_blocker
        self.bindings.models.history_proxy_model.set_hda_id(
            self.bindings.ui.comboBox__hist_ihda_node.currentData()
        )
        self.bindings.selection._restore_panel_selection()
        del selection_blockers
        self.bindings.notes._set_hda_info_to_parms()
        self.bindings.notes._set_hda_hist_info_to_parms()
        self.bindings.models._refresh_asset_search()
        self.bindings.ui.label__hda_count.setText(
            str(self.bindings.models.list_proxy_model.rowCount())
        )
        self.bindings.ui.label__cate_count.setText(
            str(self.bindings.models._get_category_count())
        )
        self.bindings.ui.label__hist_cnt.setText(
            str(self.bindings.models.history_proxy_model.rowCount())
        )
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg=f"library reloaded ({len(rows)} assets)"
        )
