"""Team commands projected into the existing main panel, without a second browser."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs.asset_contracts import AssetData, AssetIcon, HistoryData, LibrarySnapshot
from libs.domain import ItemSelection
from libs.history_activity import activity_rows, merge_history_rows
from libs.host import IS_HOUDINI
from libs.paths import Paths
from libs.task_controller import TaskController
from libs.team.client import HttpCatalog
from libs.team.contracts import Conflict, FileKind, Page, parse_blob
from libs.team.panel_catalog import PanelCatalog
from libs.team.pending import PendingCommand
from libs.team.presentation import asset_row, history_row
from libs.team.search import DocumentSearch
from widgets.library_connection.dialog import ConnectionDialog
from widgets.panel.library_session import PersonalPanelSession, TeamPanelSession
from widgets.tag_editor import TagEditor
from widgets.team_library.actions import MainAssetActions
from widgets.team_library.executor import WorkspaceTaskExecutor
from widgets.team_library.presenter import WorkspacePresenter

if TYPE_CHECKING:
    from libs.ihda_icons import IHDAIcons
    from libs.resource_policy import CallbackPolicy
    from libs.runtime_settings import RuntimeSettings
    from widgets.asset_browser.integration import AssetBrowserIntegration
    from widgets.asset_details.integration import AssetDetailsIntegration
    from widgets.panel.library_sync import PanelLibrarySync
    from widgets.panel.policy import PanelPolicy
    from widgets.panel.ports import (
        AssetModelPort,
        LibraryToolsPort,
        NotesPort,
        PresentationPort,
        SelectionPort,
    )
    from widgets.panel.state import PanelSessionState, PanelStatus, PanelViews
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer


@dataclass(frozen=True, slots=True, kw_only=True)
class TeamBindings:
    parent: QtWidgets.QWidget
    callbacks: CallbackPolicy
    runtime: RuntimeSettings
    policy: PanelPolicy
    tasks: TaskController
    ai_tasks: TaskController
    browser: AssetBrowserIntegration
    details: AssetDetailsIntegration
    icons: IHDAIcons
    sync: PanelLibrarySync
    video_player: VideoPlayer | UnavailableVideoPlayer
    models: AssetModelPort
    notes: NotesPort
    presentation: PresentationPort
    selection: SelectionPort
    session: PanelSessionState
    status: PanelStatus
    tools: LibraryToolsPort
    views: PanelViews
    apply_snapshot: Callable[[LibrarySnapshot], None]
    refresh: Callable[[], None]
    invalidate_ai: Callable[[], None]
    show_assets: Callable[[], None]
    show_video: Callable[[], None]
    personal_controls: tuple[QtWidgets.QWidget | QtGui.QAction, ...]
    label__hist_cnt: QtWidgets.QLabel
    label__hist_tags: QtWidgets.QLabel
    label__metadata_status: QtWidgets.QLabel
    label__tag_status: QtWidgets.QLabel
    lineEdit__search_hda: QtWidgets.QLineEdit
    pushButton__ai_suggest: QtWidgets.QPushButton
    pushButton__metadata_save: QtWidgets.QPushButton
    stackedWidget__hda_infos: QtWidgets.QStackedWidget
    textEdit__note: QtWidgets.QTextEdit
    textEdit__tag: TagEditor


class MainLibraryIntegration(QtCore.QObject):
    def require_catalog(self) -> PanelCatalog:
        if self.catalog is None:
            raise RuntimeError("No team library is active")
        return self.catalog

    def __init__(self, bindings: TeamBindings) -> None:
        super().__init__(bindings.parent)
        self.bindings = bindings
        self.callbacks = bindings.callbacks
        self.actions = MainAssetActions(self)
        self._root = Paths.config_dirpath / "workspace"
        self._tasks = TaskController(self)
        self._executor = WorkspaceTaskExecutor(self._tasks)
        self._tasks.idle.connect(self._idle)
        self._tasks.idle.connect(self.actions.next)
        self.presenter: WorkspacePresenter | None = None
        self.catalog: PanelCatalog | None = None
        self._candidate: PanelCatalog | None = None
        self.project: dict[str, Any] = {}
        self._documents: dict[int, dict[str, Any]] = {}
        self._histories: dict[int, dict[str, Any]] = {}
        self._history_owner: int | None = None
        self._history_pending = False
        self._personal_repository: Any = None
        self._personal_library: Any = None
        self._personal_selection: int | None = None
        self._disabled: list[tuple[Any, bool]] = []
        self._connection: ConnectionDialog | None = None
        self._members_dialog: Any = None
        self._refresh_pending = False
        self._closing = False
        self._loading = False
        self._file_kind: FileKind = "asset"
        self._import_target: tuple[Any, Any] | None = None
        self._conflict = False
        self._conflict_message = ""
        self._conflict_asset_id: int | None = None
        self._review_asset_id: int | None = None
        self._pending: PendingCommand | None = None
        self.source = bindings.browser.view.comboBox__library_source
        self.source.activated.connect(self._source_changed)
        bindings.textEdit__note.textChanged.connect(self._edited)
        bindings.textEdit__tag.changed.connect(self._edited)
        bindings.label__metadata_status.linkActivated.connect(self._recover)

    @property
    def active(self) -> bool:
        return self.presenter is not None

    @property
    def writable(self) -> bool:
        return self.project.get("role") in {"owner", "editor"}

    # Read-only surface for the action class; it must not depend on how the
    # integration stores its caches or runs its jobs.
    @property
    def busy(self) -> bool:
        return self._tasks.busy

    @property
    def closing(self) -> bool:
        return self._closing

    @property
    def pending(self) -> PendingCommand | None:
        return self._pending

    def document(self, asset_id: int) -> dict[str, Any] | None:
        return self._documents.get(asset_id)

    def history(self, history_id: int) -> dict[str, Any] | None:
        return self._histories.get(history_id)

    def start_task(
        self, operation: Callable[[], Any], finished: Callable[..., Any]
    ) -> None:
        self._tasks.start(operation, finished)

    def _source_changed(self, index: int) -> None:
        action = self.source.itemData(index)
        if action == "connect":
            self._reset_source()
            self.open_connection()
        elif action == "personal":
            self.use_personal()

    def _reset_source(self) -> None:
        with QtCore.QSignalBlocker(self.source):
            self.source.setCurrentIndex(1 if self.active else 0)

    def open_connection(self) -> None:
        if self._tasks.busy or self._closing:
            return
        if self._connection is not None:
            self._connection.show()
            self._connection.raise_()
            return
        dialog = ConnectionDialog(
            self._root, self.bindings.parent, runtime=self.bindings.runtime
        )
        self._connection = dialog
        dialog.connected.connect(self.open_backend)
        dialog.finished.connect(self._connection_finished)
        dialog.show()

    def _connection_finished(self, result: int) -> None:
        dialog, self._connection = self._connection, None
        if dialog is not None:
            dialog.deleteLater()

    def open_backend(self, backend: HttpCatalog, project: dict[str, Any]) -> None:
        if self._tasks.busy or self._closing or self.bindings.tasks.busy:
            self.show_error("Wait for the current library operation to finish.")
            return
        candidate = PanelCatalog(
            backend, page_size=self.bindings.runtime.team_page_size
        )
        self._candidate = candidate
        self._loading = True
        self.source.setEnabled(False)
        self.show_status("Loading team library…")

        def ready(page: Any, error: Exception | None) -> None:
            self._loading = False
            self._candidate = None
            if self._closing:
                return
            if error is not None:
                self.show_error(str(error))
                self.source.setEnabled(True)
                return
            if self.bindings.tasks.busy:
                self.show_error(
                    "Finish the current library operation, then connect again."
                )
                self.source.setEnabled(True)
                return
            if not self._can_leave():
                self.source.setEnabled(True)
                return
            self._activate(candidate, project, page)

        self._executor.submit(candidate.list_assets, ready)

    def _activate(
        self, catalog: PanelCatalog, project: dict[str, Any], page: Page
    ) -> None:
        bindings = self.bindings
        if not self.active:
            bindings.details.suspend()
            bindings.sync.tasks.drain()
            self._personal_repository = bindings.session.repository
            self._personal_library = bindings.session.context
            self._personal_selection = bindings.selection.state.asset.id
        else:
            assert self.presenter is not None
            self.presenter.close()
        bindings.invalidate_ai()
        bindings.details.presenter.select(None)
        bindings.session.replace(None, None)
        bindings.browser.change_repository(None)
        bindings.selection.state.clear()
        if self.catalog is not None:
            self.catalog.cancel.set()
        self.catalog, self.project = catalog, dict(project)
        self._pending = PendingCommand(
            self._root
            / "pending"
            / (hashlib.sha256(catalog.namespace.encode()).hexdigest() + ".json")
        )
        self.presenter = WorkspacePresenter(
            self,
            catalog,
            self._executor,
            self._pending,
            page_size=self.bindings.runtime.team_page_size,
        )
        bindings.session.actions = TeamPanelSession(self)
        self._documents.clear()
        self._histories.clear()
        self._history_owner = None
        self._history_pending = False
        self._conflict = False
        self._set_personal_controls(bindings.session.actions.capabilities.local_files)
        with QtCore.QSignalBlocker(self.source):
            self.source.clear()
            self.source.addItem("Personal", "personal")
            self.source.addItem(project["name"], "team")
            self.source.addItem("Connect team…", "connect")
            self.source.setCurrentIndex(1)
        bindings.show_assets()
        bindings.pushButton__metadata_save.setVisible(True)
        self.presenter.page_ready(page)
        bindings.selection.init_select_ihda_category_model()
        self.show_busy(False)
        self.bindings.tools.actionProject_Members.setVisible(
            bindings.session.actions.capabilities.manage_members
        )

    def _set_personal_controls(self, enabled: bool) -> None:
        if enabled:
            for control, previous in self._disabled:
                control.setEnabled(previous)
            self._disabled.clear()
            return
        if self._disabled:
            return
        for control in self.bindings.personal_controls:
            self._disabled.append((control, control.isEnabled()))
            control.setEnabled(False)
        self.bindings.stackedWidget__hda_infos.setCurrentIndex(0)

    def _can_leave(self) -> bool:
        if self.presenter is None or not self.presenter.has_unsaved_changes:
            return True
        return (
            QtWidgets.QMessageBox.question(
                self.bindings.parent,
                "Unsaved team edits",
                "Discard unsaved edits and switch libraries?",
                QtWidgets.QMessageBox.StandardButton.Discard
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            == QtWidgets.QMessageBox.StandardButton.Discard
        )

    def use_personal(self) -> None:
        if self._tasks.busy or self.bindings.tasks.busy:
            self._reset_source()
            return
        if not self.active:
            return
        if not self._can_leave():
            self._reset_source()
            return
        assert self.presenter is not None
        self.presenter.close()
        self.presenter = None
        if self.catalog is not None:
            self.catalog.cancel.set()
        self.catalog = None
        bindings = self.bindings
        bindings.invalidate_ai()
        bindings.session.replace(self._personal_library, self._personal_repository)
        bindings.selection.state.clear()
        bindings.selection.state.restore_asset_id(self._personal_selection)
        bindings.session.actions = PersonalPanelSession(
            bindings.session,
            bindings.details.presenter,
            lambda: bindings.sync.presenter.refresh(),
        )
        bindings.browser.change_repository(bindings.session.repository)
        self._set_personal_controls(bindings.session.actions.capabilities.local_files)
        bindings.tools.actionProject_Members.setVisible(False)
        bindings.pushButton__ai_suggest.setEnabled(not bindings.ai_tasks.busy)
        bindings.pushButton__metadata_save.setEnabled(True)
        bindings.pushButton__metadata_save.setVisible(False)
        bindings.textEdit__note.setReadOnly(False)
        bindings.textEdit__tag.setReadOnly(False)
        bindings.icons.pixmap_thumbnail_data.clear()
        bindings.icons.pixmap_hist_thumbnail_data.clear()
        bindings.show_assets()
        bindings.apply_snapshot(LibrarySnapshot(revision=0))
        bindings.selection.state.restore_asset_id(self._personal_selection)
        bindings.refresh()
        with QtCore.QSignalBlocker(self.source):
            self.source.clear()
            self.source.addItem("Personal", "personal")
            self.source.addItem("Connect team…", "connect")
        self.show_status("")

    def refresh(self) -> None:
        if self.presenter is not None:
            if self._tasks.busy:
                self._refresh_pending = True
            else:
                self.presenter.refresh()

    def _idle(self) -> None:
        if self._closing:
            return
        self.source.setEnabled(True)
        if self._refresh_pending:
            self._refresh_pending = False
            self.refresh()
        elif self._history_pending:
            self._history_pending = False
            if self.bindings.presentation.is_ihda_history_view:
                self.request_history()

    def show_page(self, page: Page) -> None:
        assert self.catalog is not None
        self.bindings.icons.pixmap_thumbnail_data.clear()
        self.bindings.icons.pixmap_hist_thumbnail_data.clear()
        self._documents = {item["id"]: item for item in page.items}
        self.bindings.textEdit__tag.setVocabulary(
            [tag for item in page.items for tag in item.get("tags", [])]
        )
        self._histories.clear()
        self._history_owner = None
        self._history_pending = self.bindings.presentation.is_ihda_history_view
        rows = [asset_row(item, self.catalog.cache_root) for item in page.items]
        categories = sorted({item.hda_cate for item in rows})
        icons = tuple(AssetIcon(asset_id=row.hda_id, icon=row.hda_icon) for row in rows)
        self.bindings.apply_snapshot(
            LibrarySnapshot(
                revision=page.revision,
                assets=tuple(rows),
                categories=tuple(categories),
                icons=icons,
            )
        )
        self._prepare_previews(
            [(item["id"], item) for item in page.items], history=False
        )
        self.bindings.browser.presenter.change_gateway(DocumentSearch(page.items))
        self.bindings.browser.refresh()

    def _prepare_previews(
        self, documents: list[tuple[int, dict[str, Any]]], *, history: bool
    ) -> None:
        catalog = self.catalog
        if catalog is None:
            return
        icons = self.bindings.icons
        cache = (
            icons.pixmap_hist_thumbnail_data if history else icons.pixmap_thumbnail_data
        )
        for identifier, document in documents:
            reference = document.get("files", {}).get("thumbnail")
            if reference is not None:
                blob = parse_blob(reference)
                path = catalog.cache_root / blob.digest / blob.filename
                cache.set_path(
                    identifier, path, resolve=partial(catalog.download, blob)
                )

    def select(self, asset_id: int | None) -> None:
        if self.presenter is not None:
            self.presenter.select(asset_id)
            if self._history_owner != asset_id:
                self._histories.clear()
                self._history_owner = None
                self.bindings.selection.state.clear_history()
                self.bindings.models.history_model.reload([])
                self.bindings.label__hist_cnt.setText("0")
                self.bindings.label__hist_tags.clear()
            if asset_id is None:
                self.show_asset({}, "", [])

    def show_asset(self, asset: dict[str, Any], note: str, tags: Sequence[str]) -> None:
        bindings = self.bindings
        with (
            QtCore.QSignalBlocker(bindings.textEdit__note),
            QtCore.QSignalBlocker(bindings.textEdit__tag),
        ):
            bindings.textEdit__note.setPlainText(note)
            bindings.textEdit__tag.setTags(tags)
        bindings.notes.set_label_tags(list(tags))
        self._show_tag_dirty()
        if self._review_asset_id is not None and self._review_asset_id == asset.get(
            "id"
        ):
            self._review_asset_id = None
            self._show_comparison(asset, note, tags)

    def _show_tag_dirty(self) -> tuple[bool, bool]:
        """Refresh the tag indicator; return (note, tags) dirtiness."""
        note_dirty, tag_dirty = (
            self.presenter.unsaved_fields
            if self.presenter is not None
            else (False, False)
        )
        self.bindings.label__tag_status.setText("Unsaved" if tag_dirty else "")
        return note_dirty, tag_dirty

    def _edited(self) -> None:
        if self.presenter is not None:
            self.presenter.edit(
                self.bindings.textEdit__note.toPlainText(),
                self.bindings.textEdit__tag.tags(),
            )
            note_dirty, _ = self._show_tag_dirty()
            if self._conflict:
                self.bindings.label__metadata_status.setText(self._conflict_message)
            elif not self._tasks.busy:
                self.show_status("Unsaved" if note_dirty else "")

    def save(self) -> None:
        if self.presenter is not None and self.writable:
            self.presenter.save_metadata()

    def show_busy(self, busy: bool) -> None:
        self.source.setEnabled(not busy)
        if self.active:
            self.bindings.pushButton__metadata_save.setEnabled(
                not busy and self.writable
            )
            self.bindings.pushButton__ai_suggest.setEnabled(
                self.writable and not self.bindings.ai_tasks.busy
            )
            self.bindings.textEdit__note.setReadOnly(not self.writable)
            self.bindings.textEdit__tag.setReadOnly(not self.writable)
        if busy:
            self.show_status("Working…")

    def show_status(self, message: str) -> None:
        if message.startswith("Saved."):
            message = "Saved · just now"
        elif "assets · loaded" in message:
            message = ""
        if (
            self._pending is not None
            and self.active
            and self._pending.legacy() is not None
        ):
            self.bindings.label__metadata_status.setText(
                'A pre-upgrade request is preserved. <a href="legacy">Review request</a>'
            )
            return
        if (
            self._pending is not None
            and self.active
            and self._pending.load() is not None
        ):
            message = 'A save needs confirmation. <a href="retry">Retry</a>'
        self.bindings.label__metadata_status.setText(message)

    def show_error(self, message: str) -> None:
        self.bindings.label__metadata_status.setTextFormat(
            QtCore.Qt.TextFormat.PlainText
        )
        self.bindings.label__metadata_status.setText(message)
        self.bindings.label__metadata_status.setTextFormat(
            QtCore.Qt.TextFormat.AutoText
        )

    def show_failure(self, error: Exception) -> None:
        self.actions.clear()
        self._review_asset_id = None
        self._history_pending = False
        command = self.presenter.failed_command if self.presenter else None
        if (
            isinstance(error, Conflict)
            and command is not None
            and command.asset_id is not None
        ):
            self._conflict = True
            self._conflict_asset_id = command.asset_id
            self._conflict_message = (
                escape(str(error)) + ' <a href="compare">Review changes</a>'
            )
            self.bindings.label__metadata_status.setText(self._conflict_message)
        elif self._pending is not None and (
            self._pending.legacy() is not None or self._pending.load() is not None
        ):
            self.show_status("")
        else:
            self.show_error(str(error))

    def _recover(self, action: str) -> None:
        if self.presenter is None:
            return
        if action == "legacy" and self._pending is not None:
            payload = self._pending.legacy()
            if payload is None:
                return
            values = payload.get("values", {})
            if not isinstance(values, dict):
                values = {}
            review = QtWidgets.QMessageBox(self.bindings.parent)
            review.setWindowTitle("Review pre-upgrade request")
            review.setText(
                "The request has not been resent. Archive it, review the latest asset, then apply any remaining changes through the normal editor."
            )
            review.setDetailedText(
                str(payload.get("operation", ""))
                + "\n"
                + "\n".join(
                    f"{key}: {values[key]}"
                    for key in ("name", "version", "note", "tags", "favorite")
                    if key in values
                )
            )
            review.setStandardButtons(
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel
            )
            review.button(QtWidgets.QMessageBox.StandardButton.Ok).setText(
                "Archive and review"
            )
            if review.exec() == QtWidgets.QMessageBox.StandardButton.Ok:
                self._pending.archive_legacy()
                asset_id = payload.get("asset_id")
                if isinstance(asset_id, int) and asset_id in self._documents:
                    self.presenter.select(asset_id)
                    self.presenter.reload_selected()
                self.show_status(
                    "Request archived. Review the asset before applying changes."
                )
        elif action == "retry":
            self.presenter.retry()
        elif action == "compare":
            if self._conflict_asset_id is not None:
                self.bindings.show_assets()
                self.bindings.lineEdit__search_hda.clear()
                self.bindings.selection.init_select_ihda_category_model()
                self.bindings.selection.select_model_item_by_hda_id(
                    self._conflict_asset_id
                )
            self._review_asset_id = self.bindings.selection.state.asset.id
            self.presenter.reload_selected()

    def _show_comparison(
        self, asset: dict[str, Any], note: str, tags: Sequence[str]
    ) -> None:
        dialog = QtWidgets.QDialog(self.bindings.parent)
        dialog.setWindowTitle("Review changes — " + asset["name"])
        dialog.resize(680, 360)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(
            QtWidgets.QLabel(
                "Your edits are kept. Compare them with the latest saved values before saving again."
            )
        )
        columns = QtWidgets.QHBoxLayout()
        for title, text in (
            ("Your edits", note + "\n\nTags: " + " ".join(tags)),
            (
                "Latest saved",
                asset.get("note", "") + "\n\nTags: " + " ".join(asset.get("tags", [])),
            ),
        ):
            group = QtWidgets.QGroupBox(title)
            group_layout = QtWidgets.QVBoxLayout(group)
            editor = QtWidgets.QPlainTextEdit(text)
            editor.setReadOnly(True)
            group_layout.addWidget(editor)
            columns.addWidget(group)
        layout.addLayout(columns)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()

    def asset_committed(self, result: dict[str, Any]) -> None:
        self._conflict = False
        self._conflict_asset_id = None
        self._refresh_pending = True

    def request_history(self) -> None:
        asset_id = self.bindings.selection.state.asset.id
        if (
            self.presenter is None
            or asset_id is None
            or self._history_owner == asset_id
        ):
            return
        if self._tasks.busy:
            self._history_pending = True
            return
        # Mark as loaded only when the current response has actually arrived.
        self.presenter.history()

    def show_history(
        self, items: list[dict[str, Any]], events: Sequence[dict[str, Any]] = ()
    ) -> None:
        assert self.catalog is not None
        self._history_owner = (
            items[0]["document"]["id"]
            if items
            else self.bindings.selection.state.asset.id
        )
        self._histories = {item["id"]: item for item in items}
        rows = [history_row(item, self.catalog.cache_root) for item in items]
        if self._history_owner is not None:
            asset = self.bindings.selection.state.asset
            rows = merge_history_rows(rows, self._activity_rows(events, asset, items))
        self.bindings.icons.make_pixmap_hist_thumbnail_data(rows)
        self._prepare_previews(
            [(item["id"], item["document"]) for item in items], history=True
        )
        self.bindings.models.history_model.reload(rows)
        self.bindings.label__hist_cnt.setText(str(len(rows)))

    def _activity_rows(
        self,
        events: Sequence[dict[str, Any]],
        asset: ItemSelection[AssetData],
        items: list[dict[str, Any]],
    ) -> list[HistoryData]:
        """Server events as rows of the selected asset.

        The server joins ``actor_name`` (None once a member left); the personal
        fallback backend only has ``actor``.
        """
        library_id = items[0]["document"].get("project_id", "") if items else ""
        return activity_rows(
            (
                {
                    **event,
                    "hda_id": self._history_owner,
                    "org_hda_name": asset.name or "",
                    "node_category": asset.cate or "",
                    "actor": (
                        event.get("actor_name")
                        if "actor_name" in event
                        else event.get("actor")
                    )
                    or "Former member",
                }
                for event in events
            ),
            remote=True,
            library_id=library_id,
        )

    def file_ready(self, path: Path, asset: dict[str, Any]) -> None:
        try:
            if self._file_kind == "video":
                self.bindings.show_video()
                self.bindings.video_player.play_after_add_playlist(filepath_lst=[path])
            elif IS_HOUDINI:
                self.bindings.tools.import_team_asset(path, asset, self._import_target)
                if self.catalog is not None:
                    from libs.team.contracts import Command

                    catalog = self.catalog
                    command = Command(
                        "usage", asset_id=asset["id"], expected_revision=0
                    )
                    QtCore.QTimer.singleShot(
                        0, lambda: self._record_usage(catalog, command)
                    )
            else:
                self.show_status(f"Downloaded: {path}")
        except Exception as error:
            self.actions.clear()
            self.show_error(str(error))

    def _record_usage(self, catalog: Any, command: Any) -> None:
        if catalog is None or self._closing or catalog is not self.catalog:
            return
        if self._tasks.busy:
            QtCore.QTimer.singleShot(
                self.callbacks.retry_delay_ms,
                lambda: self._record_usage(catalog, command),
            )
            return
        backend: Any = catalog
        self._executor.submit(
            lambda: backend.execute(command),
            lambda result, error: (
                self.show_status("Imported; usage could not be recorded.")
                if error
                else None
            ),
        )

    def download(
        self,
        kind: FileKind = "asset",
        historical: dict[str, Any] | None = None,
        target: tuple[Any, Any] | None = None,
    ) -> None:
        if self.presenter is None or self._tasks.busy:
            return
        if kind == "asset" and IS_HOUDINI and target is None:
            from libs.houdini_api import HoudiniAPI

            editor = HoudiniAPI.network_editor()
            if editor is None:
                self.show_error("Open a Network Editor first")
                return
            target = (editor.pwd(), editor.cursorPosition())
        self._file_kind = kind
        self._import_target = target
        self.presenter.download(kind, historical)

    def open_members(self) -> None:
        from widgets.library_connection.members import MembersDialog

        if self.catalog is None or self.project.get("role") != "owner":
            return
        if self._members_dialog is not None:
            self._members_dialog.show()
            self._members_dialog.raise_()
            return
        dialog = MembersDialog(
            self.catalog.transport, self.project, self.bindings.parent
        )
        self._members_dialog = dialog
        dialog.finished.connect(self._members_closed)
        dialog.show()

    def _members_closed(self, result: int) -> None:
        dialog, self._members_dialog = self._members_dialog, None
        if dialog is not None:
            dialog.deleteLater()

    def shutdown(self) -> None:
        self._closing = True
        if self.presenter:
            self.presenter.close()
        if self.catalog:
            self.catalog.cancel.set()
        if self._candidate:
            self._candidate.cancel.set()
        if self._connection:
            self._connection.shutdown()
        self._tasks.drain()
        if self._members_dialog is not None:
            self._members_dialog.shutdown()
