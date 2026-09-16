"""Asset management for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore

if TYPE_CHECKING:
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
import logging
from datetime import datetime

from PySide6 import QtGui, QtWidgets

import public
from libs import houdini_api, log_handler
from libs.asset_lifecycle import RenameResult
from libs.domain import AssetData
from model import ihda_history_model, ihda_list_model, ihda_table_model
from widgets.asset_lifecycle.presenter import AssetCommandPresenter


class AssetManagementMixin:
    def _asset_commands(self) -> AssetCommandPresenter:
        return AssetCommandPresenter(
            self,
            self._services.lifecycle(self._repository, self._services.names),
            self._committed_asset_display_failed,
        )

    def _committed_asset_display_failed(self, error: Exception) -> None:
        self.show_command_error(
            f"Library change saved, but display update failed: {error}. Reload the library."
        )
        try:
            self.reload_library()
        except Exception as reload_error:
            self.show_command_error(f"Automatic reload failed: {reload_error}")

    def show_command_error(self, message: str) -> None:
        log_handler.LogHandler.log_msg(method=logging.error, msg=message)

    def _slot_cleanup_hda_record(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("Cleanup iHDA Record")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setText(
            "Are you sure you want to remove all unnecessary iHDA record data that does not exist?"
        )
        msgbox.setDetailedText(
            "NOTE: Don't worry. Only unused information is cleaned up."
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            self._delete_unused_hda_record_info(db_api=db_api)

    def _delete_unused_hda_record_info(
        self, db_api: SQLite3DatabaseAPI | None = None
    ) -> None:
        record_data = db_api.get_all_hda_record_fileinfo(user_id=self._user)
        if not len(record_data):
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="record data does not exist"
            )
            return
        for record_info_dat in record_data:
            record_id, hip_dirpath, hip_filename, hda_dirpath, hda_filename = (
                record_info_dat
            )
            hip_dirpath = pathlib.Path(hip_dirpath)
            hip_filepath = hip_dirpath / hip_filename
            hda_dirpath = pathlib.Path(hda_dirpath)
            hda_filepath = hda_dirpath / hda_filename
            if not hip_filepath.exists():
                db_api.delete_hda_record(record_id=record_id)
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg=f"ID {record_id} record information has been deleted",
                )
            if not hda_filepath.exists():
                db_api.delete_hda_record(record_id=record_id)
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg=f"ID {record_id} record information has been deleted",
                )
        self._ihda_record_model.remove_invalid_record_data()
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg="cleanup of iHDA record information is complete"
        )

    def _slot_favorite_node(self) -> None:
        is_favorite_nodes = self.pushButton__favorite_node.isChecked()
        self._ihda_list_proxy_model.is_favorite_nodes = is_favorite_nodes
        self._ihda_table_proxy_model.is_favorite_nodes = is_favorite_nodes
        self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self._get_category_count()))
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
        self.pushButton__favorite_node.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/main/icons/{favorite_icon}"))
        )

    @staticmethod
    def _ihda_license_check(hda_license: str | None = None) -> bool:
        # 만약 현재 Houdini는 상업용 라이센스이면
        if houdini_api.HoudiniAPI.is_houdini_commercial_license():
            # iHDA는 상업용 라이센스가 아니라면
            if hda_license != houdini_api.HoudiniAPI.commercial_license():
                return False
        return True

    def _slot_hda_name_changed(self) -> None:
        if not self._rename_ihda.is_valid_ihda_name:
            return
        new_name = self._rename_ihda.final_ihda_name
        self._dragdrop_overlay_show(text="Change iHDA Node Name")
        try:
            if self._change_ihda_name(new_hda_name=new_name):
                self._rename_ihda.close()
        finally:
            self._dragdrop_overlay_close()

    def _change_ihda_name(self, new_hda_name: str | None = None) -> bool:
        data = dict(self._selection.asset.data) if self._selection.asset.data else None
        if data is None or new_hda_name is None or self._repository is None:
            return False
        hda_id = data[public.Key.hda_id]
        row = self._assets.id_rows.get(hda_id)
        if row is None:
            return False
        self._video_player.player_stop()
        try:
            video_paths = self._repository.history_videos(hda_id)
        except Exception as error:
            self.show_command_error(str(error))
            return False

        def committed(result: RenameResult) -> None:
            self._delete_video_playlist(video_filepath_list=video_paths)
            self._apply_renamed_asset(data, result)

        return self._asset_commands().rename(
            dict(data),
            new_hda_name,
            committed,
        )

    def _apply_renamed_asset(self, data: AssetData, result: RenameResult) -> None:
        plan = result.plan
        hda_id, hda_version = data[public.Key.hda_id], data[public.Key.hda_version]
        row = self._assets.id_rows.get(hda_id)
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
            val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
            self._change_hda_data(row=row, key=public.Key.hda_name, val=new_hda_name)
            self._change_hda_data(
                row=row, key=public.Key.hda_filename, val=new_hda_filename
            )
            self._change_hda_data(
                row=row, key=public.Key.hda_dirpath, val=new_hda_dirpath
            )
            self._change_hda_data(
                row=row, key=public.Key.node_old_path, val=new_node_old_path
            )
            self._change_hda_data(row=row, key=public.Key.hda_mtime, val=val_datetime)
            if new_thumbnail_dirpath is not None:
                self._change_hda_data(
                    row=row, key=public.Key.thumbnail_dirpath, val=new_thumbnail_dirpath
                )
                self._change_hda_data(
                    row=row,
                    key=public.Key.thumbnail_filename,
                    val=new_thumbnail_filename,
                )
            if new_video_dirpath is not None:
                self._change_hda_data(
                    row=row, key=public.Key.video_dirpath, val=new_video_dirpath
                )
                self._change_hda_data(
                    row=row, key=public.Key.video_filename, val=new_video_filename
                )
            if new_thumbnail_dirpath is not None and new_thumbnail_filename:
                self._ihda_icons.update_pixmap_thumbnail_data(
                    hda_id, new_thumbnail_dirpath / new_thumbnail_filename
                )
            self._selection.select_asset(
                self._assets.rows[row], row, self._selection.asset.field
            )
            self._refresh_asset_search()
            # record 데이터 갱신 함수 호출. 이 함수만 하면 data는 바뀌지만 뷰에서는 바뀌지 않늗 문제가 있다.
            self._ihda_record_model.rename_record_item(
                hda_id=hda_id,
                new_name=new_hda_name,
                hda_dirpath=new_hda_dirpath,
                hda_version=hda_version,
            )
            # 그래서 임시 방편으로 reload 함수를 강제 호출했다.
            self._ihda_record_model.reload()
            if bool(is_update_hda_name_hist):
                # history ihda combobox text 변경
                find_cmbox_idx = self._find_hist_ihda_combobox_index(hkey_id=hda_id)
                if find_cmbox_idx is not None:
                    self.comboBox__hist_ihda_node.setItemText(
                        find_cmbox_idx, new_hda_name
                    )
                changed_history = self._ihda_history_model.relocate_asset_paths(
                    hda_id, plan.moves
                )
                self._ihda_icons.make_pixmap_hist_thumbnail_data(changed_history)
                self._restore_history_selection_data()
                # history trigger 주석처리로 인해 DB 삽입을 직접해줘야 한다.
                # The transactional audit records renames; no synthetic HDA version.

    def _restore_history_selection_data(self) -> None:
        history_id = self._selection.history.hist_id
        if history_id is None:
            return
        row = self._ihda_history_model.get_hist_id_row_map_from_model().get(history_id)
        if row is not None:
            data = self._ihda_history_model.index(row, 0).data(
                ihda_history_model.HistoryModel.data_role
            )
            self._selection.select_history(data, row, self._selection.history.field)

    def _get_hda_id_row_map(self) -> Mapping[int, int]:
        return self._assets.id_rows

    def _slot_db_cleanup(self) -> None:
        # Missing files are diagnostics, not evidence that their metadata is disposable.
        self._open_library_tools(0)

    def _slot_delete_all_history(self) -> None:
        cnt_hda_hist, cnt_hda_note_hist = self._repository.history_counts()
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
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
            all_hkey_id = self._repository.asset_ids(self._user)
            # player가 재생중이거나 일시정지 상태면 정지
            self._video_player.player_stop()
            del_hist_data_lst = []
            for hkey_id in sorted(all_hkey_id, reverse=True):
                hist_data_lst = (
                    self._ihda_history_model.get_hist_data_by_hkey_id_from_model(
                        hkey_id=hkey_id
                    )
                )
                del_hist_data_lst.extend(hist_data_lst)
            self._trash_history_rows(del_hist_data_lst)

    def _trash_history_rows(self, histories: Any) -> None:
        snapshots = {
            history[public.Key.History.hist_id]: dict(history) for history in histories
        }
        for history in snapshots.values():
            if not self._repository.is_latest_history(
                history[public.Key.History.hda_id], history[public.Key.History.hist_id]
            ):
                self._delete_each_hist_ihda_item(history)

    def _hda_favorite(self) -> None:
        if self._selection.asset.data is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="no node selected "
            )
            return
        hda_id = self._selection.asset.id
        is_update = self._repository.toggle_favorite(hda_id)
        if bool(is_update):
            row = self._assets.id_rows.get(self._selection.asset.id)
            key = public.Key.is_favorite_hda
            val = self._selection.asset.data.get(public.Key.is_favorite_hda) ^ 1
            hda_name = self._selection.asset.name
            self._change_hda_data(row=row, key=key, val=val)
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

    def _remove_selected_record_item(self, index: QtCore.QModelIndex = None) -> None:
        if not index.isValid():
            return
        record_data_name = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
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
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
        record_id_list = self._ihda_record_model.remove_selected_record_data(
            index=index
        )
        # DB 삭제
        for record_id in sorted(record_id_list):
            is_removed = self._repository.delete_scene_record(record_id)
            if is_removed:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg=f'"{record_data_name}" data on record ID {record_id} has been deleted',
                )
        # 유효한 데이터가 남아 있지 않은 껍데기 데이터 삭제하는 함수 호출
        self._ihda_record_model.remove_invalid_hull_record_item_model()
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )

    def _remove_hist_item(self) -> None:
        indexes = self._ihda_history_view.selectionModel().selectedRows(0)
        if not len(indexes):
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="iHDA history is not selected"
            )
            return
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msgbox.setWindowTitle("Remove iHDA History Node")
        msgbox.setText(
            f'Delete the <font color=red>"{len(indexes)}"</font> selected iHDA nodes?\n'
            "Move to Trash? Files are retained; the current version is protected."
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # player가 재생중이거나 일시 정지상태면 정지
            self._video_player.player_stop()
            selected = [
                dict(index.data(ihda_history_model.HistoryModel.data_role))
                for index in indexes
                if index.isValid()
            ]
            for hist_data in sorted(
                selected,
                key=lambda item: item[public.Key.History.item_row],
                reverse=True,
            ):
                self._delete_each_hist_ihda_item(hist_data=hist_data, verbose=True)

    def _remove_hda_item(self, indexes: Any = None) -> None:
        # player가 재생중이거나 일시 정지상태면 정지
        team = getattr(self, "_team_library", None)
        if team is not None and team.active:
            team.actions.remove()
            return
        self._video_player.player_stop()
        role = (
            ihda_list_model.ListModel.data_role
            if self._is_icon_mode
            else ihda_table_model.TableModel.data_role
        )
        selected = {
            index.data(role)[public.Key.hda_id]: dict(index.data(role))
            for index in (indexes or ())
            if index.isValid()
        }
        for hda_id, item in selected.items():
            if hda_id not in self._assets.id_rows:
                continue
            self._delete_ihda_item(
                hda_id=hda_id,
                hda_cate=item[public.Key.hda_cate],
                hda_name=item[public.Key.hda_name],
                hda_dirpath=item[public.Key.hda_dirpath],
            )

    def _delete_video_playlist(self, video_filepath_list: Any = None) -> None:
        for video_filepath in video_filepath_list:
            # iHDA video playlist 아이템 삭제 (이것을 삭제하지 않은 시, 파일이 삭제되지 않는다)
            self._video_player.delete_playlist_item_by_filepath(filepath=video_filepath)

    def _get_hda_model_row_by_hda_id(self, hda_id: int | None = None) -> int | None:
        return self._assets.id_rows.get(hda_id)

    def _delete_ihda_item(
        self,
        hda_id: int | None = None,
        hda_cate: Any = None,
        hda_name: str | None = None,
        hda_dirpath: pathlib.Path | None = None,
        item_row: int | None = None,
    ) -> bool:
        if hda_id is None or hda_dirpath is None:
            return False
        try:
            video_paths = self._repository.history_videos(hda_id)
        except Exception as error:
            self.show_command_error(str(error))
            return False
        return self._asset_commands().delete(
            hda_id,
            hda_dirpath,
            lambda _: self._apply_deleted_asset(
                hda_id, hda_cate, hda_name, video_paths
            ),
        )

    def _apply_deleted_asset(
        self, hda_id: int, category: str, name: str, video_paths: list[pathlib.Path]
    ) -> None:
        self._details.presenter.forget(hda_id)
        self._delete_video_playlist(video_filepath_list=video_paths)
        self._remove_hda_data(item_row=self._assets.id_rows.get(hda_id))
        histories = self._ihda_history_model.get_hist_data_by_hkey_id_from_model(
            hkey_id=hda_id
        )
        for history in sorted(
            histories, key=lambda item: item[public.Key.History.item_row], reverse=True
        ):
            self._ihda_history_model.remove_item(
                row=history[public.Key.History.item_row]
            )
            self._remove_pixmap_hist_thumbnail(
                hist_id=history[public.Key.History.hist_id]
            )
        self._delete_hist_combobox_ihda_item(hkey_id=hda_id)
        self._ihda_record_model.remove_record_item_by_hda_id(hda_id=hda_id)
        self._remove_pixmap_ihda(hkey_id=hda_id)
        self._remove_pixmap_thumbnail(hkey_id=hda_id)
        self._remove_category_item(
            category=category,
            category_list=self._repository.categories(owner=self._user),
        )
        if self._selection.asset.id == hda_id:
            self._initialize_current_attribs()
            self._clear_parms()
        if self._selection.history.id == hda_id:
            self._initialize_hist_current_attribs()
            self._set_hda_hist_info_to_parms()
        selected_row = self._assets.id_rows.get(self._selection.asset.id)
        if selected_row is not None:
            self._selection.select_asset(
                self._assets.rows[selected_row],
                selected_row,
                self._selection.asset.field,
            )
        self._restore_history_selection_data()
        self._clear_hist_parms()
        self._refresh_asset_search()
        self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self._get_category_count()))
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f'"{name}" moved to Trash'
        )

    def _delete_each_hist_ihda_item(
        self,
        hist_data: Any = None,
        verbose: bool = True,
    ) -> bool:
        history = dict(hist_data)
        return self._asset_commands().delete_history(
            history[public.Key.History.hda_id],
            history[public.Key.History.hist_id],
            [],
            lambda _: self._apply_deleted_history(history, verbose),
        )

    def _apply_deleted_history(self, history: Any, verbose: bool) -> None:
        hda_id, hist_id = (
            history[public.Key.History.hda_id],
            history[public.Key.History.hist_id],
        )
        # Resolve the row after commit: earlier batch items may have shifted it.
        for row in range(self._ihda_history_model.rowCount()):
            index = self._ihda_history_model.index(row, 0)
            if index.data(ihda_history_model.HistoryModel.hist_id_role) == hist_id:
                self._ihda_history_model.remove_item(row=row)
                break
        self._delete_hist_combobox_ihda_item(hkey_id=hda_id)
        self._remove_pixmap_hist_thumbnail(hist_id=hist_id)
        if self._selection.history.hist_id == hist_id:
            self._initialize_hist_current_attribs()
            self._set_hda_hist_info_to_parms()
        self._restore_history_selection_data()
        self._clear_hist_parms()
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.info,
                msg=f"Version {history[public.Key.History.version]} moved to Trash",
            )

    def _delete_hist_combobox_ihda_item(self, hkey_id: int | None = None) -> None:
        # history가 존재하지 않는다면
        if not self._ihda_history_model.is_exist_ihda_item_from_model(hkey_id=hkey_id):
            for idx in range(self.comboBox__hist_ihda_node.count()):
                hid = self.comboBox__hist_ihda_node.itemData(idx)
                if hkey_id == hid:
                    self.comboBox__hist_ihda_node.removeItem(idx)
