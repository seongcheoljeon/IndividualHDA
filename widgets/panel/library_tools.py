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
            import hou

            from libs.houdini_api import HoudiniAPI

            editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if editor is None:
                raise RuntimeError("Open a Network Editor first")
            parent = editor.pwd()
            if (
                parent.childTypeCategory().name().casefold()
                != snapshot["node_category"].casefold()
            ):
                raise ValueError("Open a network matching the asset category first")
            path = Path(snapshot["hda_dirpath"]) / snapshot["hda_filename"]
            with hou.undos.group("Import iHDA history version"):
                node = HoudiniAPI.import_individual_hda_into_houdini(
                    path,
                    parent,
                    editor.cursorPosition(),
                    snapshot["org_hda_name"],
                    snapshot["node_type_name"],
                )
            if node is None:
                raise RuntimeError("Could not import this history file")
            if self._library_manager is not None:
                self._library_manager.status.setText(
                    f"Imported {snapshot['version']}: {node.path()}"
                )
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "Import version", str(error))
