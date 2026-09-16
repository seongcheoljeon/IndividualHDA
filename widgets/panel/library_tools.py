"""Optional library tools attached to the existing panel menu."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtWidgets

from widgets.library_manager.dialog import LibraryManager


class LibraryToolsMixin:
    def _setup_library_tools(self) -> None:
        self._library_manager = None
        self._tools_require_restart = False
        menu = self.menubar.addMenu("Library Tools")
        action = menu.addAction("Team connection…")
        action.triggered.connect(lambda: self._team_library.open_connection())
        self.actionProject_Members = menu.addAction("Project members…")
        self.actionProject_Members.setVisible(False)
        self.actionProject_Members.triggered.connect(
            lambda: self._team_library.open_members()
        )
        menu.addSeparator()
        menu.addAction("Copy to team…", self._open_copy_to_team)
        menu.addAction("Trash…", lambda: self._open_metadata_tools())
        menu.addAction(
            "Version details…",
            self._open_selected_version_details,
        )
        for index, label in enumerate(
            (
                "Library health…",
                "Backups and restore…",
                "Repair moved paths…",
                "Compare versions…",
                "Library explorer…",
                "Recovery files…",
            )
        ):
            action = menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, tab=index: self._open_library_tools(tab)
            )

    def _open_copy_to_team(self) -> None:
        from libs.paths import Paths
        from libs.team.copy_source import PersonalCopySource
        from widgets.asset_copy.dialog import CopyAssetDialog

        if self._tasks.busy or self._team_library._tasks.busy:
            return
        asset_id = self._selection.asset.id
        if self._team_library.active or asset_id is None or self._db_filepath is None:
            QtWidgets.QMessageBox.information(
                self, "Copy to team", "Select an asset in your personal library first."
            )
            return
        dialog = CopyAssetDialog(
            PersonalCopySource(self._db_filepath, asset_id),
            Paths.config_dirpath / "workspace",
            self,
        )
        self._copy_dialog = dialog
        try:
            dialog.exec()
        finally:
            dialog.shutdown()
            self._copy_dialog = None
            dialog.deleteLater()

    def _open_selected_version_details(self) -> None:
        asset_id = self._selection.asset.id
        if asset_id is None:
            QtWidgets.QMessageBox.information(
                self, "Version details", "Select an asset first."
            )
            return
        self._open_metadata_tools(asset_id)

    def _open_metadata_tools(self, asset_id: int | None = None) -> None:
        from libs.library_management import LocalManagement, RemoteManagement
        from widgets.library_metadata.dialog import LibraryMetadataDialog

        team = self._team_library
        if self._tasks.busy or team._tasks.busy:
            return
        if team.active:
            gateway = RemoteManagement(team.catalog, team._pending)
            writable, owner = team.writable, team.project.get("role") == "owner"
        else:
            if self._db_filepath is None or not self._db_filepath.is_file():
                return
            gateway = LocalManagement(self._db_filepath)
            writable = owner = True
        dialog = LibraryMetadataDialog(
            gateway, self, asset_id=asset_id, writable=writable, owner=owner
        )
        self._metadata_dialog = dialog
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
            self._metadata_dialog = None
            dialog.deleteLater()
        if team.active:
            team.show_status("")
        if not team.active:
            self._tools_require_restart = False
            self.reload_library()

    def _open_library_tools(self, tab: int = 0) -> None:
        if self._tasks.busy or self._is_imported_data:
            return
        database, assets = self._db_filepath, self._hda_base_dirpath
        if database is None or assets is None or not database.is_file():
            QtWidgets.QMessageBox.information(
                self, "Library Tools", "Configure a library in Preferences first."
            )
            return
        if self._library_manager is None:
            dialog = LibraryManager(
                database, assets, self._user, self._selection.asset.id, self
            )
            self._library_manager = dialog
            dialog.restoreReady.connect(self._tools_restore_ready)
            dialog.pathsChanged.connect(self._tools_paths_changed)
            dialog.importVersion.connect(self._tools_import_version)
            dialog.assetSelected.connect(self._tools_select_asset)
            dialog.finished.connect(self._tools_finished)
        self._library_manager.tabs.setCurrentIndex(tab)
        self._library_manager.show()
        self._library_manager.raise_()

    def _tools_restore_ready(self, stream: Any) -> None:
        self._stage_import(stream)
        self._tools_require_restart = True

    def _tools_paths_changed(self) -> None:
        self._tools_require_restart = True

    def _tools_finished(self, result: int) -> None:
        dialog, self._library_manager = self._library_manager, None
        if dialog is not None:
            dialog.deleteLater()
        if self._tools_require_restart:
            QtCore.QTimer.singleShot(0, self.close)

    def _tools_select_asset(self, asset_id: int) -> None:
        for model, view in (
            (self._ihda_list_proxy_model, self._ihda_list_view),
            (self._ihda_table_proxy_model, self._ihda_table_view),
        ):
            index = self._find_hda_id_by_model_item(model, asset_id)
            if index is not None and index.isValid():
                view.setCurrentIndex(index)
                view.scrollTo(index)
        if self._library_manager is not None:
            self._library_manager.status.setText(
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
            if not self._repository.asset_available(
                snapshot["hda_key_id"], snapshot["id"]
            ):
                raise ValueError(
                    "This version is no longer available. Refresh the library."
                )
            path = Path(snapshot["hda_dirpath"]) / snapshot["hda_filename"]
            with HoudiniAPI.undo_group("Import iHDA history version"):
                node = HoudiniAPI.import_individual_hda_into_houdini(
                    path,
                    parent,
                    editor.cursorPosition(),
                    snapshot["org_hda_name"],
                    snapshot["node_type_name"],
                )
            if node is None:
                raise RuntimeError("Could not import this history file")
            self._repository.record_use(snapshot["hda_key_id"])
            if self._library_manager is not None:
                self._library_manager.status.setText(
                    f"Imported {snapshot['version']}: {node.path()}"
                )
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "Import version", str(error))

    def _capture_team_node(
        self, selected_node: Any = None
    ) -> tuple[Path, dict[str, Any], Path | None]:
        import json
        import tempfile

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
        staging = Paths.config_dirpath / "workspace" / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="capture-", dir=staging))
        version = "1.0"
        data = HoudiniAPI(
            hda_version=version, node_path=node.path(), hda_dirpath=directory
        ).get_individual_hda_data()
        filename = data["hda_filename"]
        if not HoudiniAPI.create_hda_file(node, directory, filename, version):
            raise RuntimeError("Houdini asset capture failed")
        thumbnail = directory / "thumbnail.png"
        has_thumbnail = HoudiniAPI.create_thumbnail(thumbnail)
        metadata = {key: value for key, value in data.items() if key != "node"}
        metadata = json.loads(json.dumps(metadata, default=str))
        metadata.update(
            hda_name=node.name(),
            hda_cate=HoudiniAPI.node_category_type_name(node),
            hda_version=version,
        )
        return directory / filename, metadata, thumbnail if has_thumbnail else None

    def _import_team_asset(
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
            node = HoudiniAPI.import_individual_hda_into_houdini(
                path,
                parent,
                position,
                asset["name"],
                asset.get("metadata", {}).get("node_type_name"),
            )
        if node is None:
            raise RuntimeError("Could not instantiate the asset")
