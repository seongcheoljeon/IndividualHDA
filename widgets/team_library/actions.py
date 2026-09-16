"""Main-panel asset menus and file dialogs; commands belong to the presenter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets

if TYPE_CHECKING:
    from widgets.team_library.integration import MainLibraryIntegration


class MainAssetActions:
    def __init__(self, library: MainLibraryIntegration) -> None:
        self.library = library
        self.window = library.window
        self._nodes: list[Any] = []
        self._imports: list[dict[str, Any]] = []
        self._drop_target: tuple[Any, Any] | None = None

    def context_menu(self, point: QtCore.QPoint) -> None:
        view = (
            self.window._ihda_list_view
            if self.window._is_icon_mode
            else self.window._ihda_table_view
        )
        index = view.indexAt(point)
        menu = QtWidgets.QMenu(self.window)
        if index.isValid():
            view.setCurrentIndex(index)
            self.window._selected_ihda_item(index)
            menu.addAction("Import", lambda: self.library.download())
            menu.addAction("Play video", lambda: self.library.download("video"))
            assert self.library.presenter is not None
            menu.addAction("History", self.library.presenter.history)
            menu.addAction(
                "Details",
                lambda: self.window._detail_view_ihda_data(
                    self.window._selection.asset.data
                ),
            )
            menu.addSeparator()
            edits = menu.addMenu("Edit")
            edits.setEnabled(self.library.writable and not self.library._tasks.busy)
            edits.addAction("Rename…", self.rename)
            favorite = menu.addAction("Favorite", self.favorite)
            favorite.setEnabled(not self.library._tasks.busy)
            edits.addAction("Add version…", lambda: self.register_file(True))
            edits.addAction("Attach thumbnail…", lambda: self.attach("thumbnail"))
            edits.addAction("Attach video…", lambda: self.attach("video"))
            edits.addSeparator()
            edits.addAction("Delete…", self.remove)
        else:
            action = menu.addAction("Register file…", self.register_file)
            action.setEnabled(self.library.writable and not self.library._tasks.busy)
        menu.exec(view.mapToGlobal(point))

    def rename(self) -> None:
        if self.library.presenter is None or not self.library.writable:
            return
        name, accepted = QtWidgets.QInputDialog.getText(
            self.window,
            "Rename asset",
            "Name",
            text=self.window._selection.asset.name or "",
        )
        if accepted:
            self.library.presenter.mutate("rename", {"name": name})

    def favorite(self) -> None:
        selected_id = self.window._selection.asset.id
        asset = (
            self.library._documents.get(selected_id)
            if selected_id is not None
            else None
        )
        if asset and self.library.presenter:
            self.library.presenter.mutate(
                "preference", {"favorite": not asset.get("favorite", False)}
            )

    def remove(self) -> None:
        if (
            self.library.presenter
            and self.library.writable
            and QtWidgets.QMessageBox.question(
                self.window,
                "Delete asset",
                "Move the selected asset to Trash? Files and history will be retained.",
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self.library.presenter.mutate("delete", {})

    def register_file(self, new_version: bool = False) -> None:
        if (
            self.library.presenter is None
            or not self.library.writable
            or self.library._tasks.busy
        ):
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Select HDA",
            filter="Houdini assets (*.hda *.hdalc *.hdanc *.ihda)",
        )
        if not path:
            return
        name = self.window._selection.asset.name or Path(path).stem
        category = self.window._selection.asset.cate or "sop"
        if not new_version:
            name, accepted = QtWidgets.QInputDialog.getText(
                self.window, "Register asset", "Name", text=Path(path).stem
            )
            if not accepted:
                return
            category, accepted = QtWidgets.QInputDialog.getText(
                self.window, "Register asset", "Category", text="sop"
            )
            if not accepted:
                return
        version, accepted = QtWidgets.QInputDialog.getText(
            self.window, "Asset version", "Version", text="1.0"
        )
        if accepted:
            description, accepted = QtWidgets.QInputDialog.getMultiLineText(
                self.window, "Asset version", "Change description (optional)"
            )
            if accepted:
                self.library.presenter.register(
                    Path(path),
                    name,
                    category,
                    version,
                    {},
                    new_version=new_version,
                    description=description,
                )

    def attach(self, kind: str) -> None:
        if self.library.presenter is None or not self.library.writable:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self.window, "Attach " + kind)
        if path:
            self.library.presenter.attach_media(Path(path), kind)

    def play_video(self) -> None:
        if self.window._is_ihda_history_view:
            from model.ihda_history_model import HistoryModel

            index = self.window._ihda_history_view.currentIndex()
            item = self.library._histories.get(index.data(HistoryModel.hist_id_role))
            if item is not None:
                self.library.download("video", item["document"])
        else:
            self.library.download("video")

    def history_menu(self, point: QtCore.QPoint) -> None:
        from model.ihda_history_model import HistoryModel

        view = self.window._ihda_history_view
        index = view.indexAt(point)
        item = self.library._histories.get(index.data(HistoryModel.hist_id_role))
        if item is None:
            return
        menu = QtWidgets.QMenu(self.window)
        menu.addAction(
            "Import", lambda: self.library.download(historical=item["document"])
        )
        menu.addAction(
            "Play video", lambda: self.library.download("video", item["document"])
        )
        remove = menu.addAction("Delete version…", lambda: self._remove_history(item))
        remove.setEnabled(self.library.writable and not self.library._tasks.busy)
        menu.exec(view.mapToGlobal(point))

    def _remove_history(self, item: dict[str, Any]) -> None:
        if (
            self.library.presenter
            and QtWidgets.QMessageBox.question(
                self.window, "Delete version", "Delete this historical version?"
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self.library.presenter.delete_history(item["document"]["id"], item["id"])

    def register_nodes(self, nodes: Any) -> None:
        if (
            self.library.presenter is None
            or not self.library.writable
            or self.library._tasks.busy
        ):
            return
        if not nodes or len(nodes) > 30:
            self.library.show_error("Register between 1 and 30 nodes at a time.")
            return
        self._nodes = list(nodes)
        self.next()

    def clear(self) -> None:
        self._nodes.clear()
        self._imports.clear()

    def next(self) -> None:
        if not self.library.active or self.library._closing:
            self.clear()
            return
        if self.library._tasks.busy:
            return
        if self._imports:
            self.library.download(
                historical=self._imports.pop(0), target=self._drop_target
            )
        elif self._nodes:
            try:
                path, metadata, thumbnail = self.window._capture_team_node(
                    self._nodes.pop(0)
                )
                assert self.library.presenter is not None
                self.library.presenter.register(
                    path,
                    metadata["hda_name"],
                    metadata["hda_cate"],
                    metadata["hda_version"],
                    metadata,
                    thumbnail,
                )
            except Exception as error:
                self.clear()
                self.library.show_error(str(error))

    def import_drop(self, drop_data: Any) -> None:
        from libs.drag_payload import decode_payload

        if self.library._tasks.busy:
            self.window._dragdrop_overlay_close()
            return
        action, items = drop_data
        self.window._dragdrop_overlay_close()
        if action != QtCore.Qt.DropAction.IgnoreAction or not items:
            return
        documents = []
        for item in items:
            data = decode_payload(item)
            if data.get("library_id") != self.library.project.get("id"):
                self.library.show_error(
                    "This drag belongs to a different library. Select the asset again."
                )
                return
            history_id = data.get("hist_id")
            historical = (
                self.library._histories.get(history_id)
                if isinstance(history_id, int)
                else None
            )
            asset_id = data.get("hda_id")
            document = (
                historical["document"]
                if historical
                else self.library._documents.get(asset_id)
                if isinstance(asset_id, int)
                else None
            )
            if document is not None:
                documents.append(document)
        from libs.host import IS_HOUDINI
        from libs.houdini_api import HoudiniAPI

        if IS_HOUDINI:
            editor = HoudiniAPI.find_network_editor_by_cursor()
            if editor is None:
                self.library.show_error("Drop the assets in a Network Editor.")
                return
            self._drop_target = (editor.pwd(), editor.cursorPosition())
        self._imports = documents
        self.next()
