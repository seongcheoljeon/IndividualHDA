"""Optional library tools attached to the existing panel menu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from widgets.library_manager.dialog import LibraryManager

if TYPE_CHECKING:
    from libs.task_controller import TaskController
    from widgets.asset_copy.dialog import CopyAssetDialog
    from widgets.library_manager.dialog import LibraryManager
    from widgets.library_metadata.dialog import LibraryMetadataDialog
    from widgets.library_metadata.recovery import RegistrationRecoveryDialog
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.ports import AssetModelPort, LibraryQueryPort, SelectionPort
    from widgets.panel.scene_usage import SceneUsageIntegration
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState, PanelStatus, PanelViews
    from widgets.team_library.integration import MainLibraryIntegration


@dataclass(frozen=True, slots=True)
class PanelLibraryToolsBindings:
    imported: Callable[[], bool]
    models: AssetModelPort
    parent: QtWidgets.QWidget
    queries: LibraryQueryPort
    reload_library: Callable[[], None]
    scene_usage: Callable[[], SceneUsageIntegration]
    selection: SelectionPort
    services: PanelServices
    session: PanelSessionState
    stage_import: Callable[[Any], None]
    status: PanelStatus
    tasks: TaskController
    team: Callable[[], MainLibraryIntegration]
    ui: MainWindowLayout
    views: PanelViews


class PanelLibraryTools:
    library_manager: LibraryManager | None = None
    recovery_dialog: RegistrationRecoveryDialog | None = None
    copy_dialog: CopyAssetDialog | None = None
    metadata_dialog: LibraryMetadataDialog | None = None
    bindings: PanelLibraryToolsBindings

    def _setup_library_tools(self) -> None:
        self.library_manager = None
        self.tools_require_restart = False
        # addMenu() appends after Help, which layout.py added last; insert before it.
        menu = QtWidgets.QMenu("Library Tools", self.bindings.ui.menubar)
        self.bindings.ui.menubar.insertMenu(
            self.bindings.ui.menuHelp.menuAction(), menu
        )
        action = menu.addAction(
            QtGui.QIcon(":/main/icons/graph1.png"), "Team connection…"
        )
        action.triggered.connect(lambda: self.bindings.team().open_connection())
        self.actionProject_Members = menu.addAction(
            QtGui.QIcon(":/main/icons/groups.png"), "Project members…"
        )
        self.actionProject_Members.setVisible(False)
        self.actionProject_Members.triggered.connect(
            lambda: self.bindings.team().open_members()
        )
        menu.addSeparator()
        menu.addAction(
            QtGui.QIcon(":/main/icons/upload.png"),
            "Copy to team…",
            self.open_copy_to_team,
        )
        self.actionRegistration_Recovery = menu.addAction(
            QtGui.QIcon(":/main/icons/ic_query_builder_white.png"),
            "Pending registrations…",
            self._open_registration_recovery,
        )
        self.registration_status_tasks = self.bindings.services.tasks(
            self.bindings.parent
        )
        menu.aboutToShow.connect(self._refresh_registration_status)
        QtCore.QTimer.singleShot(0, self._refresh_registration_status)
        menu.addAction(
            QtGui.QIcon(":/main/icons/ic_refresh_white.png"),
            "Retry scene reporting",
            lambda: self.bindings.scene_usage().flush(),
        )
        menu.addAction(
            QtGui.QIcon(":/main/icons/ic_delete_forever_white.png"),
            "Trash…",
            lambda: self._open_metadata_tools(),
        )
        menu.addAction(
            QtGui.QIcon(":/main/icons/ic_format_quote_white.png"),
            "Version details…",
            self._open_selected_version_details,
        )
        for index, (label, icon) in enumerate(
            (
                ("Library health…", ":/main/icons/monitor_heart.png"),
                ("Backups and restore…", ":/main/icons/ic_archive_white.png"),
                ("Repair moved paths…", ":/main/icons/ic_build_white.png"),
                ("Compare versions…", ":/main/icons/ic_swap_horiz_white.png"),
                ("Library explorer…", ":/main/icons/ic_find_in_page_white.png"),
                ("Recovery files…", ":/main/icons/ic_restore_page_white.png"),
            )
        ):
            action = menu.addAction(QtGui.QIcon(icon), label)
            action.triggered.connect(
                lambda checked=False, tab=index: self.open_library_tools(tab)
            )

    def _refresh_registration_status(self) -> None:
        if self.bindings.status.closing or self.registration_status_tasks.busy:
            return
        from libs.paths import Paths
        from libs.registration_recovery import RegistrationRecovery
        from libs.team.registration_recovery import TeamRegistrationRecovery

        recovery: RegistrationRecovery | TeamRegistrationRecovery
        team = self.bindings.team()
        if team.active:
            assert team.catalog is not None
            recovery = TeamRegistrationRecovery(
                Paths.config_dirpath / "workspace" / "registrations",
                team.catalog.namespace,
            )
        else:
            if (
                self.bindings.queries.db_filepath is None
                or not self.bindings.queries.db_filepath.is_file()
            ):
                return
            recovery = RegistrationRecovery(self.bindings.queries.db_filepath)

        def loaded(rows: list[dict[str, Any]]) -> None:
            count = sum(row["phase"] not in {"committed", "discarded"} for row in rows)
            self.actionRegistration_Recovery.setText(
                f"Pending registrations ({count})…"
                if count
                else "Pending registrations…"
            )

        self.registration_status_tasks.start(recovery.jobs, loaded)

    def _open_registration_recovery(self) -> None:
        from libs.paths import Paths
        from libs.registration_recovery import RegistrationRecovery
        from libs.team.registration_recovery import TeamRegistrationRecovery
        from widgets.library_metadata.recovery import RegistrationRecoveryDialog

        recovery: RegistrationRecovery | TeamRegistrationRecovery
        team = self.bindings.team()
        if self.bindings.tasks.busy or team.busy:
            return
        if team.active:
            assert team.catalog is not None
            if not team.writable:
                return
            team_recovery = TeamRegistrationRecovery(
                Paths.config_dirpath / "workspace" / "registrations",
                team.catalog.namespace,
            )

            def retry(identity: str) -> Any:
                return team_recovery.retry(identity, team.catalog, team.pending)

            recovery = team_recovery
        else:
            if self.bindings.queries.db_filepath is None:
                return
            local_recovery = RegistrationRecovery(self.bindings.queries.db_filepath)
            writer = self.bindings.services.lifecycle(
                self.bindings.session.require_repository(), self.bindings.services.names
            )

            def retry(identity: str) -> Any:
                return local_recovery.retry(identity, writer)

            recovery = local_recovery
        dialog = RegistrationRecoveryDialog(
            recovery.jobs, retry, recovery.discard, self.bindings.parent
        )
        self.recovery_dialog = dialog
        try:
            dialog.exec()
        finally:
            dialog.shutdown()
            self.recovery_dialog = None
            dialog.deleteLater()
        if team.active and team.presenter:
            team.presenter.refresh()
        elif not team.active:
            self.bindings.reload_library()

    def open_copy_to_team(self) -> None:
        from libs.paths import Paths
        from libs.team.copy_source import PersonalCopySource
        from widgets.asset_copy.dialog import CopyAssetDialog

        if self.bindings.tasks.busy or self.bindings.team().busy:
            return
        asset_id = self.bindings.selection.state.asset.id
        if (
            self.bindings.team().active
            or asset_id is None
            or self.bindings.queries.db_filepath is None
        ):
            QtWidgets.QMessageBox.information(
                self.bindings.parent,
                "Copy to team",
                "Select an asset in your personal library first.",
            )
            return
        dialog = CopyAssetDialog(
            PersonalCopySource(self.bindings.queries.db_filepath, asset_id),
            Paths.config_dirpath / "workspace",
            self.bindings.parent,
            runtime=self.bindings.services.runtime,
        )
        self.copy_dialog = dialog
        try:
            dialog.exec()
        finally:
            dialog.shutdown()
            self.copy_dialog = None
            dialog.deleteLater()

    def _open_selected_version_details(self) -> None:
        asset_id = self.bindings.selection.state.asset.id
        if asset_id is None:
            QtWidgets.QMessageBox.information(
                self.bindings.parent, "Version details", "Select an asset first."
            )
            return
        self._open_metadata_tools(asset_id)

    def _open_metadata_tools(self, asset_id: int | None = None) -> None:
        from libs.library_management import LocalManagement, RemoteManagement
        from widgets.library_metadata.dialog import LibraryMetadataDialog

        team = self.bindings.team()
        if self.bindings.tasks.busy or team.busy:
            return
        if team.active:
            assert team.catalog is not None
            gateway: RemoteManagement | LocalManagement = RemoteManagement(
                team.catalog, team.pending
            )
            writable, owner = team.writable, team.project.get("role") == "owner"
        else:
            if (
                self.bindings.queries.db_filepath is None
                or not self.bindings.queries.db_filepath.is_file()
            ):
                return
            gateway = LocalManagement(self.bindings.queries.db_filepath)
            writable = owner = True
        dialog = LibraryMetadataDialog(
            gateway,
            self.bindings.parent,
            asset_id=asset_id,
            writable=writable,
            owner=owner,
            callbacks=self.bindings.services.callbacks,
        )
        self.metadata_dialog = dialog
        dialog.changed.connect(
            lambda: (
                team.presenter.refresh()
                if team.active and team.presenter
                else self._tools_paths_changed()
            )
        )
        try:
            dialog.exec()
        finally:
            dialog.shutdown()
            self.metadata_dialog = None
            dialog.deleteLater()
        if team.active:
            assert team.catalog is not None
            team.show_status("")
        if not team.active:
            self.tools_require_restart = False
            self.bindings.reload_library()

    def open_library_tools(self, tab: int = 0) -> None:
        if self.bindings.tasks.busy or self.bindings.imported():
            return
        database, assets = (
            self.bindings.queries.db_filepath,
            self.bindings.queries.hda_base_dirpath,
        )
        if database is None or assets is None or not database.is_file():
            QtWidgets.QMessageBox.information(
                self.bindings.parent,
                "Library Tools",
                "Configure a library in Preferences first.",
            )
            return
        if self.library_manager is None:
            dialog = LibraryManager(
                database,
                assets,
                self.bindings.session.user,
                self.bindings.selection.state.asset.id,
                self.bindings.parent,
                runtime=self.bindings.services.runtime,
            )
            self.library_manager = dialog
            dialog.restoreReady.connect(self._tools_restore_ready)
            dialog.pathsChanged.connect(self._tools_paths_changed)
            dialog.importVersion.connect(self._tools_import_version)
            dialog.assetSelected.connect(self._tools_select_asset)
            dialog.finished.connect(self._tools_finished)
        self.library_manager.tabs.setCurrentIndex(tab)
        self.library_manager.show()
        self.library_manager.raise_()

    def _tools_restore_ready(self, stream: Any) -> None:
        self.bindings.stage_import(stream)
        self.tools_require_restart = True

    def _tools_paths_changed(self) -> None:
        self.tools_require_restart = True

    def _tools_finished(self, result: int) -> None:
        dialog, self.library_manager = self.library_manager, None
        if dialog is not None:
            dialog.deleteLater()
        if self.tools_require_restart:
            QtCore.QTimer.singleShot(0, self.bindings.parent.close)

    def _tools_select_asset(self, asset_id: int) -> None:
        for model, view in (
            (self.bindings.models.list_proxy_model, self.bindings.views.assets_list),
            (self.bindings.models.table_proxy_model, self.bindings.views.assets_table),
        ):
            index = self.bindings.queries.find_hda_id_by_model_item(model, asset_id)
            if index is not None and index.isValid():
                view.setCurrentIndex(index)
                view.scrollTo(index)
        if self.library_manager is not None:
            self.library_manager.status.setText(
                "Selected in the main panel where visible. Existing category/search filters still apply."
            )

    def _tools_import_version(self, snapshot: dict[str, Any]) -> None:
        try:
            from libs.houdini_api import HoudiniAPI

            editor = HoudiniAPI.network_editor()
            if editor is None:
                raise RuntimeError("Open a Network Editor first")
            parent = editor.pwd()
            if (
                parent.childTypeCategory().name().casefold()
                != snapshot["node_category"].casefold()
            ):
                raise ValueError("Open a network matching the asset category first")
            if not self.bindings.session.require_repository().asset_available(
                snapshot["hda_key_id"], snapshot["id"]
            ):
                raise ValueError(
                    "This version is no longer available. Refresh the library."
                )
            path = Path(snapshot["hda_dirpath"]) / snapshot["hda_filename"]
            with HoudiniAPI.undo_group("Import iHDA history version"):
                node = self.bindings.services.host_scene.import_individual_hda_into_houdini(
                    path,
                    parent,
                    editor.cursorPosition(),
                    snapshot["org_hda_name"],
                    snapshot["node_type_name"],
                )
            if node is None:
                raise RuntimeError("Could not import this history file")
            self.bindings.session.require_repository().record_use(
                snapshot["hda_key_id"]
            )
            uuid = self.bindings.session.require_repository().version_identity(
                snapshot["hda_key_id"], snapshot["id"]
            )
            if uuid:
                self.bindings.scene_usage().observe(
                    node,
                    uuid,
                    "local:"
                    + str(
                        self.bindings.session.require_context().db_filepath.resolve()
                    ),
                )
            if self.library_manager is not None:
                self.library_manager.status.setText(
                    f"Imported {snapshot['version']}: {node.path()}"
                )
        except Exception as error:
            QtWidgets.QMessageBox.warning(
                self.bindings.parent, "Import version", str(error)
            )

    def capture_team_node(
        self, selected_node: Any = None
    ) -> tuple[Path, dict[str, Any], Path | None]:
        import json

        from libs.houdini_api import HoudiniAPI
        from libs.paths import Paths

        if isinstance(selected_node, bytes):
            selected_node = selected_node.decode("utf-8")
        if isinstance(selected_node, str):
            selected_node = HoudiniAPI.find_node(selected_node)
        nodes = (
            [selected_node]
            if selected_node is not None
            else HoudiniAPI.get_selected_nodes()
        )
        if not nodes or len(nodes) != 1:
            raise RuntimeError("Select exactly one Houdini node")
        node = nodes[0]
        if not HoudiniAPI.is_valid_node(node):
            raise RuntimeError("Selected node cannot be registered")
        from libs.team.registration_recovery import TeamRegistrationRecovery

        recovery = TeamRegistrationRecovery(
            Paths.config_dirpath / "workspace" / "registrations",
            self.bindings.team().require_catalog().namespace,
        )
        job_id, directory = recovery.begin_capture(node.path())
        version = "1.0"
        data = HoudiniAPI(
            hda_version=version, node_path=node.path(), hda_dirpath=directory
        ).get_individual_hda_data()
        filename = data["hda_filename"]
        if not self.bindings.services.host_capture.create_hda_file(
            node, directory, filename, version
        ):
            raise RuntimeError("Houdini asset capture failed")
        thumbnail = directory / "thumbnail.png"
        has_thumbnail = self.bindings.services.host_capture.create_thumbnail(thumbnail)
        metadata = {key: value for key, value in data.items() if key != "node"}
        metadata = json.loads(json.dumps(metadata, default=str))
        metadata.update(
            hda_name=node.name(),
            hda_cate=HoudiniAPI.node_category_type_name(node),
            hda_version=version,
        )
        recovery.captured(
            job_id, directory / filename, metadata, thumbnail if has_thumbnail else None
        )
        metadata["_registration_job_id"] = job_id
        return directory / filename, metadata, thumbnail if has_thumbnail else None

    def import_team_asset(
        self, path: Path, asset: dict[str, Any], target: tuple[Any, Any] | None = None
    ) -> None:
        from libs.houdini_api import HoudiniAPI

        if target is None:
            editor = HoudiniAPI.network_editor()
            if editor is None:
                raise RuntimeError("Open a Network Editor first")
            target = (editor.pwd(), editor.cursorPosition())
        parent, position = target
        if parent.childTypeCategory().name().casefold() != asset["category"].casefold():
            raise RuntimeError("Open a Network Editor matching the asset category")
        with HoudiniAPI.undo_group("Import library asset"):
            node = self.bindings.services.host_scene.import_individual_hda_into_houdini(
                path,
                parent,
                position,
                asset["name"],
                asset.get("metadata", {}).get("node_type_name"),
            )
        if node is None:
            raise RuntimeError("Could not instantiate the asset")
        if asset.get("version_uuid") and self.bindings.team().catalog:
            self.bindings.scene_usage().observe(
                node,
                asset["version_uuid"],
                self.bindings.team().require_catalog().namespace,
            )
