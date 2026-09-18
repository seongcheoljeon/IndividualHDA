"""Main-panel asset menus and file dialogs; commands belong to the presenter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs.asset_contracts import HistoryData
from libs.drag_payload import decode_drag_record
from libs.scene_contracts import SceneRecord
from libs.team.contracts import FileKind
from libs.ui_icons import Icon

if TYPE_CHECKING:
    from widgets.team_library.integration import MainLibraryIntegration


class MainAssetActions:
    def __init__(self, library: MainLibraryIntegration) -> None:
        self.library = library
        self.bindings = library.bindings
        self._nodes: list[Any] = []
        self._imports: list[dict[str, Any]] = []
        self._drop_target: tuple[Any, Any] | None = None

    def context_menu(self, point: QtCore.QPoint) -> None:
        view = (
            self.bindings.views.assets_list
            if self.bindings.presentation.is_icon_mode
            else self.bindings.views.assets_table
        )
        index = view.indexAt(point)
        menu = QtWidgets.QMenu(self.bindings.parent)
        if index.isValid():
            view.setCurrentIndex(index)
            self.bindings.selection.selected_ihda_item(index)
            menu.addAction(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/download.png")),
                "Import",
                lambda: self.library.download(),
            )
            menu.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_MOVIE_WHITE)),
                "Play video",
                lambda: self.library.download("video"),
            )
            assert self.library.presenter is not None
            menu.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_QUERY_BUILDER_WHITE)),
                "History",
                self.library.presenter.history,
            )
            menu.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_FORMAT_QUOTE_WHITE)),
                "Details",
                lambda: self.bindings.notes.detail_view_ihda_data(
                    self.bindings.selection.state.asset.data
                ),
            )
            menu.addSeparator()
            edits = menu.addMenu("Edit")
            edits.setIcon(QtGui.QIcon(QtGui.QPixmap(Icon.IC_BORDER_COLOR_WHITE)))
            edits.setEnabled(self.library.writable and not self.library.busy)
            edits.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_BORDER_COLOR_WHITE)),
                "Rename…",
                self.rename,
            )
            favorite = menu.addAction(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_favorite_border_white.png")),
                "Favorite",
                self.favorite,
            )
            favorite.setEnabled(not self.library.busy)
            edits.addAction(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/asterisk.png")),
                "Add version…",
                lambda: self.register_file(True),
            )
            edits.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_CAMERA_ALT_WHITE)),
                "Attach thumbnail…",
                lambda: self.attach("thumbnail"),
            )
            edits.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_VIDEOCAM_WHITE)),
                "Attach video…",
                lambda: self.attach("video"),
            )
            edits.addSeparator()
            edits.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_DELETE_FOREVER_WHITE)),
                "Delete…",
                self.remove,
            )
        else:
            action = menu.addAction(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_SAVE_WHITE)),
                "Register file…",
                self.register_file,
            )
            action.setEnabled(self.library.writable and not self.library.busy)
        menu.exec(view.mapToGlobal(point))

    def rename(self) -> None:
        if self.library.presenter is None or not self.library.writable:
            return
        name, accepted = QtWidgets.QInputDialog.getText(
            self.bindings.parent,
            "Rename asset",
            "Name",
            text=self.bindings.selection.state.asset.name or "",
        )
        if accepted:
            self.library.presenter.mutate("rename", {"name": name})

    def favorite(self) -> None:
        selected_id = self.bindings.selection.state.asset.id
        asset = self.library.document(selected_id) if selected_id is not None else None
        if asset and self.library.presenter:
            self.library.presenter.mutate(
                "preference", {"favorite": not asset.get("favorite", False)}
            )

    def remove(self) -> None:
        asset_id = self.bindings.selection.state.asset.id
        if asset_id is not None and self.library.presenter and self.library.writable:
            self._confirm_removal(
                {"asset_id": asset_id},
                lambda: self.library.presenter.mutate("delete", {}),
            )

    def _confirm_removal(self, item: dict[str, Any], operation: Any) -> None:
        from libs.library_management import RemoteManagement
        from widgets.library_metadata.dependency_warning import dependency_message

        if self.library.busy:
            return
        gateway = RemoteManagement(self.library.require_catalog())

        def ready(rows: list[dict[str, Any]]) -> None:
            def confirm() -> None:
                if self.bindings.status.closing:
                    return
                if self.library.busy:
                    QtCore.QTimer.singleShot(
                        self.library.callbacks.retry_delay_ms, confirm
                    )
                    return
                if (
                    QtWidgets.QMessageBox.question(
                        self.bindings.parent,
                        "Move to Trash",
                        "Move this item to Trash? Files and history will be retained."
                        + dependency_message(rows),
                    )
                    == QtWidgets.QMessageBox.StandardButton.Yes
                ):
                    operation()

            QtCore.QTimer.singleShot(0, confirm)

        self.library.start_task(lambda: gateway.dependents(item), ready)

    def register_file(self, new_version: bool = False) -> None:
        if (
            self.library.presenter is None
            or not self.library.writable
            or self.library.busy
        ):
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.bindings.parent,
            "Select HDA",
            filter="Houdini assets (*.hda *.hdalc *.hdanc *.ihda)",
        )
        if not path:
            return
        name = self.bindings.selection.state.asset.name or Path(path).stem
        category = self.bindings.selection.state.asset.cate or "sop"
        if not new_version:
            name, accepted = QtWidgets.QInputDialog.getText(
                self.bindings.parent, "Register asset", "Name", text=Path(path).stem
            )
            if not accepted:
                return
            category, accepted = QtWidgets.QInputDialog.getText(
                self.bindings.parent, "Register asset", "Category", text="sop"
            )
            if not accepted:
                return
        version, accepted = QtWidgets.QInputDialog.getText(
            self.bindings.parent, "Asset version", "Version", text="1.0"
        )
        if accepted:
            description, accepted = QtWidgets.QInputDialog.getMultiLineText(
                self.bindings.parent, "Asset version", "Change description (optional)"
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

    def attach(self, kind: FileKind) -> None:
        if self.library.presenter is None or not self.library.writable:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.bindings.parent, "Attach " + kind
        )
        if path:
            self.library.presenter.attach_media(Path(path), kind)

    def play_video(self) -> None:
        if self.bindings.presentation.is_ihda_history_view:
            from model.ihda_history_model import HistoryModel

            index = self.bindings.views.history.currentIndex()
            item = self.library.history(index.data(HistoryModel.hist_id_role))
            if item is not None:
                self.library.download("video", item["document"])
        else:
            self.library.download("video")

    def history_menu(self, point: QtCore.QPoint) -> None:
        from model.ihda_history_model import HistoryModel

        view = self.bindings.views.history
        index = view.indexAt(point)
        item = self.library.history(index.data(HistoryModel.hist_id_role))
        if item is None:
            return
        menu = QtWidgets.QMenu(self.bindings.parent)
        menu.addAction(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/download.png")),
            "Import",
            lambda: self.library.download(historical=item["document"]),
        )
        menu.addAction(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_MOVIE_WHITE)),
            "Play video",
            lambda: self.library.download("video", item["document"]),
        )
        remove = menu.addAction(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_DELETE_FOREVER_WHITE)),
            "Delete version…",
            lambda: self._remove_history(item),
        )
        remove.setEnabled(self.library.writable and not self.library.busy)
        menu.exec(view.mapToGlobal(point))

    def _remove_history(self, item: dict[str, Any]) -> None:
        if self.library.presenter:
            asset_id, history_id = item["document"]["id"], item["id"]
            self._confirm_removal(
                {"asset_id": asset_id, "history_id": history_id},
                lambda: self.library.presenter.delete_history(asset_id, history_id),
            )

    def _allow_batch(self, count: int, action: str) -> bool:
        policy = self.bindings.policy
        if not 1 <= count <= policy.maximum_node_batch:
            self.library.show_error(
                f"{action} between 1 and {policy.maximum_node_batch} nodes at a time."
            )
            return False
        if count > policy.warn_node_batch:
            return (
                QtWidgets.QMessageBox.question(
                    self.bindings.parent,
                    action + " nodes",
                    f"{action} {count} nodes? Houdini may take some time to complete this batch.",
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No,
                )
                == QtWidgets.QMessageBox.StandardButton.Yes
            )
        return True

    def register_nodes(self, nodes: Any) -> None:
        if (
            self.library.presenter is None
            or not self.library.writable
            or self.library.busy
        ):
            return
        if not self._allow_batch(len(nodes) if nodes else 0, "Register"):
            return
        self._nodes = list(nodes)
        self.next()

    def clear(self) -> None:
        self._nodes.clear()
        self._imports.clear()

    def next(self) -> None:
        if not self.library.active or self.library.closing:
            self.clear()
            return
        if self.library.busy:
            return
        if self._imports:
            self.library.download(
                historical=self._imports.pop(0), target=self._drop_target
            )
        elif self._nodes:
            try:
                path, metadata, thumbnail = self.bindings.tools.capture_team_node(
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

        if self.library.busy:
            self.bindings.presentation.dragdrop_overlay_close()
            return
        action, items = drop_data
        self.bindings.presentation.dragdrop_overlay_close()
        if action != QtCore.Qt.DropAction.IgnoreAction or not items:
            return
        if not self._allow_batch(len(items), "Import"):
            return
        documents = []
        for item in items:
            data = decode_drag_record(item)
            if isinstance(
                data, SceneRecord
            ) or data.library_id != self.library.project.get("id"):
                self.library.show_error(
                    "This drag belongs to a different library. Select the asset again."
                )
                return
            history_id = data.hist_id if isinstance(data, HistoryData) else None
            historical = (
                self.library.history(history_id)
                if isinstance(history_id, int)
                else None
            )
            asset_id = data.hda_id
            document = (
                historical["document"]
                if historical
                else self.library.document(asset_id)
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
