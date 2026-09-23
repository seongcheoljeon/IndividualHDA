"""Asset management for the Houdini panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore

from libs.scene_record_cleanup import RecordCleanupResult, SceneRecordCleanup

if TYPE_CHECKING:
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
    from widgets.panel.library_port import LibraryPort
    from widgets.panel.ports import (
        AssetModelPort,
        LibraryQueryPort,
        LibraryToolsPort,
        NotesPort,
        NotificationsPort,
        PresentationPort,
        SelectionPort,
    )
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6 import QtGui, QtWidgets

from libs import houdini_api, keys, log_handler
from libs.asset_contracts import AssetData, HistoryData
from libs.asset_lifecycle import RenameResult
from model import ihda_history_model, ihda_list_model, ihda_table_model
from widgets.asset_lifecycle.presenter import AssetCommandPresenter

if TYPE_CHECKING:
    from libs.ihda_icons import IHDAIcons
    from widgets.asset_details.integration import AssetDetailsIntegration
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState, PanelViews
    from widgets.rename_ihda.rename_ihda import RenameIHDA


@dataclass(frozen=True, slots=True)
class PanelAssetManagementBindings:
    details: AssetDetailsIntegration
    icons: IHDAIcons
    models: AssetModelPort
    notes: NotesPort
    parent: QtWidgets.QWidget
    presentation: PresentationPort
    notifications: NotificationsPort
    queries: LibraryQueryPort
    reload_library: Callable[[], None]
    rename_dialog: RenameIHDA
    selection: SelectionPort
    services: PanelServices
    session: PanelSessionState
    library: Callable[[], LibraryPort]
    tools: LibraryToolsPort
    ui: MainWindowLayout
    video_player: VideoPlayer | UnavailableVideoPlayer
    views: PanelViews


class PanelAssetManagement:
    bindings: PanelAssetManagementBindings

    def asset_commands(self) -> AssetCommandPresenter:
        return AssetCommandPresenter(
            self,
            self.bindings.services.lifecycle(
                self.bindings.session.require_repository(), self.bindings.services.names
            ),
            self._committed_asset_display_failed,
        )

    def _committed_asset_display_failed(self, error: Exception) -> None:
        logging.exception("Display update failed after a committed library change")
        self.show_command_error(
            f"Library change saved, but display update failed: {error}. Reload the library."
        )
        try:
            self.bindings.reload_library()
        except Exception as reload_error:
            self.show_command_error(f"Automatic reload failed: {reload_error}")

    def show_command_error(self, message: str) -> None:
        log_handler.LogHandler.log_msg(method=logging.error, msg=message)

    def _slot_cleanup_hda_record(self) -> None:
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.bindings.presentation.get_default_font())
        msgbox.setWindowTitle("Cleanup iHDA Record")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setText(
            "Are you sure you want to remove all unnecessary iHDA record data that does not exist?"
        )
        msgbox.setDetailedText(
            "Only scene-record metadata is removed. HIP and HDA files are kept."
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_unused_hda_record_info()

    def _delete_unused_hda_record_info(
        self, db_api: SQLite3DatabaseAPI | None = None
    ) -> None:
        if (
            self.bindings.session.repository is None
            or not self.bindings.library().supports_scene_records
        ):
            return
        try:
            result = SceneRecordCleanup(self.bindings.session.repository).cleanup(
                self.bindings.session.user
            )
        except Exception as error:
            self.show_command_error(str(error))
            return
        self._apply_scene_record_cleanup(result)

    def _apply_scene_record_cleanup(self, result: RecordCleanupResult) -> None:
        model, view = self.bindings.models.record_model, self.bindings.views.record
        selected: set[int] = set()
        for index in view.selectionModel().selectedRows(0):
            selected.update(model.selected_record_ids(index))
        try:
            if result.deleted:
                model.remove_record_ids(result.deleted)
        except Exception as error:
            self.show_command_error(
                f"Records were deleted, but the view could not be updated: {error}"
            )
            try:
                data = self.bindings.queries.get_hda_loc_record_data(
                    self.bindings.queries.db_filepath
                )
                if data is None:
                    raise RuntimeError("Scene records could not be reloaded")
                model.replace_record_data(data)
            except Exception as reload_error:
                self.show_command_error(
                    f"Scene record reload failed: {reload_error}. Reopen the panel."
                )
                return
        view.expandAll()
        proxy = self.bindings.models.record_proxy_model

        def restore(parent: QtCore.QModelIndex) -> None:
            for row in range(proxy.rowCount(parent)):
                index = proxy.index(row, 0, parent)
                if index.data(model.record_id_role) in selected:
                    view.selectionModel().select(
                        index,
                        QtCore.QItemSelectionModel.SelectionFlag.Select
                        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
                    )
                restore(index)

        restore(QtCore.QModelIndex())
        self.bindings.ui.label__loc_record_count.setText(str(proxy.get_row_count()))
        removed = len(result.deleted)
        self.bindings.notifications.notify(
            f"Removed {removed} stale scene record{'s' if removed != 1 else ''}."
            if removed
            else "No stale scene records; every HIP and asset file still exists."
        )
        if result.failed:
            details = "; ".join(
                f"{identity}: {message}" for identity, message in result.failed
            )
            self.show_command_error("Some records were kept: " + details)
            self.bindings.notifications.notify(
                f"{len(result.failed)} record(s) could not be checked; see the log.",
                level="warning",
            )

    def _slot_favorite_node(self) -> None:
        is_favorite_nodes = self.bindings.ui.pushButton__favorite_node.isChecked()
        self.bindings.models.list_proxy_model.is_favorite_nodes = is_favorite_nodes
        self.bindings.models.table_proxy_model.is_favorite_nodes = is_favorite_nodes
        self.bindings.ui.label__hda_count.setText(
            str(self.bindings.models.list_proxy_model.rowCount())
        )
        self.bindings.ui.label__cate_count.setText(
            str(self.bindings.models.get_category_count())
        )
        if is_favorite_nodes:
            favorite_icon = "ic_favorite_white.png"
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="turn on favorite filtering"
            )
        else:
            favorite_icon = "ic_favorite_border_white.png"
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="turn off favorite filtering"
            )
        self.bindings.ui.pushButton__favorite_node.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/main/icons/{favorite_icon}"))
        )

    @staticmethod
    def ihda_license_check(hda_license: str | None = None) -> bool:
        # 만약 현재 Houdini는 상업용 라이센스이면
        if houdini_api.HoudiniAPI.is_houdini_commercial_license():
            # iHDA는 상업용 라이센스가 아니라면
            if hda_license != houdini_api.HoudiniAPI.commercial_license():
                return False
        return True

    def _slot_hda_name_changed(self) -> None:
        if not self.bindings.rename_dialog.is_valid_ihda_name:
            return
        new_name = self.bindings.rename_dialog.final_ihda_name
        self.bindings.presentation.dragdrop_overlay_show(text="Change iHDA Node Name")
        try:
            if self._change_ihda_name(new_hda_name=new_name):
                self.bindings.rename_dialog.close()
        finally:
            self.bindings.presentation.dragdrop_overlay_close()

    def _change_ihda_name(self, new_hda_name: str | None = None) -> bool:
        data = (
            self.bindings.selection.state.asset.data
            if self.bindings.selection.state.asset.data
            else None
        )
        if (
            data is None
            or new_hda_name is None
            or self.bindings.session.repository is None
        ):
            return False
        hda_id = data.hda_id
        row = self.bindings.models.assets.id_rows.get(hda_id)
        if row is None:
            return False
        self.bindings.video_player.player_stop()
        from widgets.library_metadata.dependency_warning import (
            confirm_local_dependencies,
        )

        try:
            if not confirm_local_dependencies(
                self.bindings.parent,
                {"asset_id": hda_id},
                database=self.bindings.session.context.db_filepath
                if self.bindings.session.context
                else None,
            ):
                return False
            video_paths = self.bindings.session.require_repository().history_videos(
                hda_id
            )
        except Exception as error:
            self.show_command_error(str(error))
            return False

        def committed(result: RenameResult) -> None:
            self._delete_video_playlist(video_filepath_list=video_paths)
            self._apply_renamed_asset(data, result)

        return self.asset_commands().rename(
            data,
            new_hda_name,
            committed,
        )

    def _apply_renamed_asset(self, data: AssetData, result: RenameResult) -> None:
        plan = result.plan
        hda_id, hda_version = data.hda_id, data.hda_version
        row = self.bindings.models.assets.id_rows.get(hda_id)
        if row is None:
            return
        new_hda_name = plan.name
        is_update_hda_name, is_update_hda_name_hist = (
            result.asset_rows,
            result.history_rows,
        )
        new_hda_dirpath, new_hda_filename = plan.directory, plan.filename
        new_node_old_path = plan.node_path
        new_thumbnail_dirpath, new_thumbnail_filename = (
            plan.thumbnail_directory,
            plan.thumbnail_filename,
        )
        new_video_dirpath, new_video_filename = (
            plan.video_directory,
            plan.video_filename,
        )
        if bool(is_update_hda_name):
            val_datetime = datetime.today().strftime(keys.Value.datetime_fmt_str)
            self.bindings.queries.change_hda_data(
                row=row, key=keys.Key.hda_name, val=new_hda_name
            )
            self.bindings.queries.change_hda_data(
                row=row, key=keys.Key.hda_filename, val=new_hda_filename
            )
            self.bindings.queries.change_hda_data(
                row=row, key=keys.Key.hda_dirpath, val=new_hda_dirpath
            )
            self.bindings.queries.change_hda_data(
                row=row, key=keys.Key.node_old_path, val=new_node_old_path
            )
            self.bindings.queries.change_hda_data(
                row=row, key=keys.Key.hda_mtime, val=val_datetime
            )
            if new_thumbnail_dirpath is not None:
                self.bindings.queries.change_hda_data(
                    row=row, key=keys.Key.thumbnail_dirpath, val=new_thumbnail_dirpath
                )
                self.bindings.queries.change_hda_data(
                    row=row,
                    key=keys.Key.thumbnail_filename,
                    val=new_thumbnail_filename,
                )
            if new_video_dirpath is not None:
                self.bindings.queries.change_hda_data(
                    row=row, key=keys.Key.video_dirpath, val=new_video_dirpath
                )
                self.bindings.queries.change_hda_data(
                    row=row, key=keys.Key.video_filename, val=new_video_filename
                )
            if new_thumbnail_dirpath is not None and new_thumbnail_filename:
                self.bindings.icons.update_pixmap_thumbnail_data(
                    hda_id, new_thumbnail_dirpath / new_thumbnail_filename
                )
            self.bindings.selection.state.select_asset(
                self.bindings.models.assets.rows[row],
                row,
                self.bindings.selection.state.asset.field,
            )
            self.bindings.models.refresh_asset_search()
            # record 데이터 갱신 함수 호출. 이 함수만 하면 data는 바뀌지만 뷰에서는 바뀌지 않늗 문제가 있다.
            self.bindings.models.record_model.rename_record_item(
                hda_id=hda_id,
                new_name=new_hda_name,
                hda_dirpath=new_hda_dirpath,
                hda_version=hda_version,
                hda_filename=plan.filename,
            )
            # 그래서 임시 방편으로 reload 함수를 강제 호출했다.
            self.bindings.models.record_model.reload()
            if bool(is_update_hda_name_hist):
                # history ihda combobox text 변경
                find_cmbox_idx = self.bindings.selection.find_hist_ihda_combobox_index(
                    hkey_id=hda_id
                )
                if find_cmbox_idx is not None:
                    self.bindings.ui.comboBox__hist_ihda_node.setItemText(
                        find_cmbox_idx, new_hda_name
                    )
                changed_history = (
                    self.bindings.models.history_model.relocate_asset_paths(
                        hda_id, plan.moves
                    )
                )
                self.bindings.icons.make_pixmap_hist_thumbnail_data(changed_history)
                self._restore_history_selection_data()
                # history trigger 주석처리로 인해 DB 삽입을 직접해줘야 한다.
                # The transactional audit records renames; no synthetic HDA version.

    def _restore_history_selection_data(self) -> None:
        history_id = self.bindings.selection.state.history.hist_id
        if history_id is None:
            return
        row = self.bindings.models.history_model.get_hist_id_row_map_from_model().get(
            history_id
        )
        if row is not None:
            data = self.bindings.models.history_model.index(row, 0).data(
                ihda_history_model.HistoryModel.data_role
            )
            self.bindings.selection.state.select_history(
                data, row, self.bindings.selection.state.history.field
            )

    def get_hda_id_row_map(self) -> Mapping[int, int]:
        return self.bindings.models.assets.id_rows

    def _slot_db_cleanup(self) -> None:
        # Missing files are diagnostics, not evidence that their metadata is disposable.
        self.bindings.tools.open_library_tools(0)

    def _slot_delete_all_history(self) -> None:
        counts = self.bindings.session.require_repository().history_counts()
        cnt_hda_hist, cnt_hda_note_hist = counts.versions, counts.notes
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.bindings.presentation.get_default_font())
        msgbox.setWindowTitle("Delete all iHDA history")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setText(
            "Move historical versions to Trash? Current versions and note history are retained."
        )
        # chkbox = QtWidgets.QCheckBox(msgbox)
        # chkbox.setText('Delete All History Files')
        # chkbox.setChecked(True)
        # chkbox.setIcon(QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        # chkbox.setToolTip('Delete all iHDA history files')
        # msgbox.setCheckBox(chkbox)
        msgbox.setDetailedText(
            f"""
Historical versions move to Trash. Files and note history are retained.
iHDA node history: {cnt_hda_hist}
iHDA note history: {cnt_hda_note_hist}
        """
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        msgbox.setStyleSheet("QLabel {min-width: 500px;}")
        msgbox.resize(msgbox.sizeHint())
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # 만약 파일들까지 삭제한다면
            # if chkbox.isChecked():
            all_hkey_id = self.bindings.session.require_repository().asset_ids(
                self.bindings.session.user
            )
            # player가 재생중이거나 일시정지 상태면 정지
            self.bindings.video_player.player_stop()
            del_hist_data_lst = []
            for hkey_id in sorted(all_hkey_id, reverse=True):
                hist_data_lst = self.bindings.models.history_model.get_hist_data_by_hkey_id_from_model(
                    hkey_id=hkey_id
                )
                del_hist_data_lst.extend(hist_data_lst)
            self.trash_history_rows(del_hist_data_lst)

    def trash_history_rows(self, histories: list[HistoryData]) -> None:
        snapshots = {
            history.hist_id: history for history in histories if history.is_version
        }
        for history in snapshots.values():
            if not self.bindings.session.require_repository().is_latest_history(
                history.hda_id, history.hist_id
            ):
                self._delete_each_hist_ihda_item(history)

    def hda_favorite(self) -> None:
        if self.bindings.selection.state.asset.data is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="no node selected "
            )
            return
        self._toggle_favorite(self.bindings.selection.state.asset.require_data().hda_id)

    def toggle_favorite_at(self, index: QtCore.QModelIndex) -> None:
        """The star on a card or table row; the team library has its own command."""
        if not index.isValid():
            return
        id_role = getattr(index.model(), "id_role", None)  # source and proxies
        hda_id = index.data(id_role) if id_role is not None else None
        if hda_id is None or self.bindings.library().toggle_favorite(hda_id):
            return
        self._toggle_favorite(hda_id)

    def _toggle_favorite(self, hda_id: int) -> None:
        row = self.bindings.models.assets.id_rows.get(hda_id)
        if row is None:
            return
        current = self.bindings.models.assets.rows[row]
        is_update = self.bindings.session.require_repository().toggle_favorite(hda_id)
        if bool(is_update):
            key = keys.Key.is_favorite_hda
            val = not current.is_favorite_hda
            hda_name = current.hda_name
            self.bindings.queries.change_hda_data(row=row, key=key, val=val)
            if val:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg=f'the "{hda_name}" node has been set as a favorite node',
                )
            else:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg=f'the "{hda_name}" node has been released from the favorites node',
                )

    def remove_selected_record_item(
        self, index: QtCore.QModelIndex | None = None
    ) -> None:
        if index is None or not index.isValid():
            return
        repository = self.bindings.session.repository
        if repository is None or not self.bindings.library().supports_scene_records:
            return
        identities = self.bindings.models.record_model.selected_record_ids(index)
        record_data_name = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.bindings.presentation.get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setWindowTitle("Remove iHDA Record Information")
        msgbox.setText(
            f'Are you sure you want to delete the selected "{record_data_name}" record information?'
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        if (
            repository is not self.bindings.session.repository
            or not self.bindings.library().supports_scene_records
        ):
            self.show_command_error("The library changed; select the records again.")
            return
        result = SceneRecordCleanup(repository).delete(identities)
        self._apply_scene_record_cleanup(result)

    def remove_hist_item(self) -> None:
        indexes = self.bindings.views.history.selectionModel().selectedRows(0)
        if not len(indexes):
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="iHDA history is not selected"
            )
            return
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.bindings.presentation.get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msgbox.setWindowTitle("Remove iHDA History Node")
        msgbox.setText(
            f"Delete the <b>{len(indexes)}</b> selected iHDA nodes?<br>"
            "Move to Trash? Files are retained; the current version is protected."
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # player가 재생중이거나 일시 정지상태면 정지
            self.bindings.video_player.player_stop()
            selected = [
                index.data(ihda_history_model.HistoryModel.data_role)
                for index in indexes
                if index.isValid()
            ]
            for hist_data in sorted(
                selected,
                key=lambda item: item.item_row,
                reverse=True,
            ):
                self._delete_each_hist_ihda_item(hist_data=hist_data, verbose=True)

    def remove_hda_item(self, indexes: Any = None) -> None:
        # player가 재생중이거나 일시 정지상태면 정지
        if self.bindings.library().remove_selected():
            return
        self.bindings.video_player.player_stop()
        role = (
            ihda_list_model.ListModel.data_role
            if self.bindings.presentation.is_icon_mode
            else ihda_table_model.TableModel.data_role
        )
        selected = {
            index.data(role).hda_id: index.data(role)
            for index in (indexes or ())
            if index.isValid()
        }
        for hda_id, item in selected.items():
            if hda_id not in self.bindings.models.assets.id_rows:
                continue
            self._delete_ihda_item(
                hda_id=hda_id,
                hda_cate=item.hda_cate,
                hda_name=item.hda_name,
                hda_dirpath=item.hda_dirpath,
            )

    def _delete_video_playlist(self, video_filepath_list: Any = None) -> None:
        for video_filepath in video_filepath_list:
            # iHDA video playlist 아이템 삭제 (이것을 삭제하지 않은 시, 파일이 삭제되지 않는다)
            self.bindings.video_player.delete_playlist_item_by_filepath(
                filepath=video_filepath
            )

    def _delete_ihda_item(
        self,
        hda_id: int | None = None,
        hda_cate: Any = None,
        hda_name: str | None = None,
        hda_dirpath: pathlib.Path | None = None,
        item_row: int | None = None,
    ) -> bool:
        if hda_id is None or hda_dirpath is None or hda_name is None:
            return False
        from widgets.library_metadata.dependency_warning import (
            confirm_local_dependencies,
        )

        try:
            if not confirm_local_dependencies(
                self.bindings.parent,
                {"asset_id": hda_id},
                database=self.bindings.session.context.db_filepath
                if self.bindings.session.context
                else None,
            ):
                return False
            video_paths = self.bindings.session.require_repository().history_videos(
                hda_id
            )
        except Exception as error:
            self.show_command_error(str(error))
            return False
        return self.asset_commands().delete(
            hda_id,
            hda_dirpath,
            lambda _: self._apply_deleted_asset(
                hda_id, hda_cate, hda_name, video_paths
            ),
        )

    def _apply_deleted_asset(
        self, hda_id: int, category: str, name: str, video_paths: list[pathlib.Path]
    ) -> None:
        self.bindings.details.presenter.forget(hda_id)
        self._delete_video_playlist(video_filepath_list=video_paths)
        self.bindings.models.remove_hda_data(
            item_row=self.bindings.models.assets.id_rows.get(hda_id)
        )
        histories = (
            self.bindings.models.history_model.get_hist_data_by_hkey_id_from_model(
                hkey_id=hda_id
            )
        )
        for history in sorted(histories, key=lambda item: item.item_row, reverse=True):
            self.bindings.models.history_model.remove_item(row=history.item_row)
            self.bindings.models.remove_pixmap_hist_thumbnail(hist_id=history.hist_id)
        self._delete_hist_combobox_ihda_item(hkey_id=hda_id)
        self.bindings.models.record_model.remove_record_item_by_hda_id(hda_id=hda_id)
        self.bindings.models.remove_pixmap_ihda(hkey_id=hda_id)
        self.bindings.models.remove_pixmap_thumbnail(hkey_id=hda_id)
        self.bindings.models.remove_category_item(
            category=category,
            category_list=self.bindings.session.require_repository().categories(
                owner=self.bindings.session.user
            ),
        )
        if self.bindings.selection.state.asset.id == hda_id:
            self.bindings.selection.initialize_current_attribs()
            self.bindings.notes.clear_parms()
        if self.bindings.selection.state.history.id == hda_id:
            self.bindings.selection.initialize_hist_current_attribs()
            self.bindings.notes.set_hda_hist_info_to_parms()
        selected_id = self.bindings.selection.state.asset.id
        selected_row = (
            self.bindings.models.assets.id_rows.get(selected_id)
            if selected_id is not None
            else None
        )
        if selected_row is not None:
            self.bindings.selection.state.select_asset(
                self.bindings.models.assets.rows[selected_row],
                selected_row,
                self.bindings.selection.state.asset.field,
            )
        self._restore_history_selection_data()
        self.bindings.notes.clear_hist_parms()
        self.bindings.models.refresh_asset_search()
        self.bindings.ui.label__hda_count.setText(
            str(self.bindings.models.list_proxy_model.rowCount())
        )
        self.bindings.ui.label__cate_count.setText(
            str(self.bindings.models.get_category_count())
        )
        self.bindings.ui.label__loc_record_count.setText(
            str(self.bindings.models.record_proxy_model.get_row_count())
        )
        self.bindings.notifications.notify(
            f'"{name}" moved to Trash',
            action="Undo",
            on_action=lambda: self._restore_trashed(name, {"asset_id": hda_id}),
        )

    def _restore_trashed(self, name: str, item: dict[str, Any]) -> None:
        """Undo from the toast: clear deleted_at and reload the library snapshot."""
        from libs.library_management import LocalManagement

        context = self.bindings.session.context
        if context is None:
            return
        try:
            LocalManagement(pathlib.Path(context.db_filepath)).change(item, "restore")
        except Exception as error:
            self.show_command_error(f"Could not restore {name}: {error}")
            return
        self.bindings.reload_library()

    def _delete_each_hist_ihda_item(
        self,
        hist_data: HistoryData,
        verbose: bool = True,
    ) -> bool:
        history = hist_data
        from widgets.library_metadata.dependency_warning import (
            confirm_local_dependencies,
        )

        try:
            if not confirm_local_dependencies(
                self.bindings.parent,
                {
                    "asset_id": history.hda_id,
                    "history_id": history.hist_id,
                },
                database=self.bindings.session.context.db_filepath
                if self.bindings.session.context
                else None,
            ):
                return False
        except Exception as error:
            self.show_command_error(str(error))
            return False
        return self.asset_commands().delete_history(
            history.hda_id,
            history.hist_id,
            [],
            lambda _: self._apply_deleted_history(history, verbose),
        )

    def _apply_deleted_history(self, history: HistoryData, verbose: bool) -> None:
        hda_id, hist_id = (
            history.hda_id,
            history.hist_id,
        )
        # Resolve the row after commit: earlier batch items may have shifted it.
        for row in range(self.bindings.models.history_model.rowCount()):
            index = self.bindings.models.history_model.index(row, 0)
            if index.data(ihda_history_model.HistoryModel.hist_id_role) == hist_id:
                self.bindings.models.history_model.remove_item(row=row)
                break
        self._delete_hist_combobox_ihda_item(hkey_id=hda_id)
        self.bindings.models.remove_pixmap_hist_thumbnail(hist_id=hist_id)
        if self.bindings.selection.state.history.hist_id == hist_id:
            self.bindings.selection.initialize_hist_current_attribs()
            self.bindings.notes.set_hda_hist_info_to_parms()
        self._restore_history_selection_data()
        self.bindings.notes.clear_hist_parms()
        if verbose:
            self.bindings.notifications.notify(
                f"Version {history.version} moved to Trash",
                action="Undo",
                on_action=lambda: self._restore_trashed(
                    f"version {history.version}",
                    {"asset_id": hda_id, "history_id": hist_id},
                ),
            )

    def _delete_hist_combobox_ihda_item(self, hkey_id: int | None = None) -> None:
        # history가 존재하지 않는다면
        if not self.bindings.models.history_model.is_exist_ihda_item_from_model(
            hkey_id=hkey_id
        ):
            for idx in range(self.bindings.ui.comboBox__hist_ihda_node.count()):
                hid = self.bindings.ui.comboBox__hist_ihda_node.itemData(idx)
                if hkey_id == hid:
                    self.bindings.ui.comboBox__hist_ihda_node.removeItem(idx)
