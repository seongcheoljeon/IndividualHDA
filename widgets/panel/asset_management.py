"""Asset management for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

from libs.asset_rename import build_rename_plan, rename_asset
from libs.asset_commands import delete_asset, delete_history
from collections.abc import Mapping
from typing import Any
import pathlib
from PySide6 import QtCore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
import logging
from datetime import datetime
from bisect import insort_right
from PySide6 import QtWidgets, QtGui
import public
from model import ihda_list_model
from model import ihda_table_model
from model import ihda_history_model
from libs import houdini_api, log_handler


class AssetManagementMixin:
    def _slot_cleanup_hda_record(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("Cleanup iHDA Record")
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText(
            "Are you sure you want to remove all unnecessary iHDA record data that does not exist?"
        )
        msgbox.setDetailedText(
            "NOTE: Don't worry. Only unused information is cleaned up."
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.Yes:
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
                    msg="ID {0} record information has been deleted".format(record_id),
                )
            if not hda_filepath.exists():
                db_api.delete_hda_record(record_id=record_id)
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg="ID {0} record information has been deleted".format(record_id),
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
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/{0}".format(favorite_icon)))
        )

    @staticmethod
    def _ihda_license_check(hda_license: str | None = None) -> bool:
        # 만약 현재 Houdini는 상업용 라이센스이면
        if houdini_api.HoudiniAPI.is_houdini_commercial_license():
            # iHDA는 상업용 라이센스가 아니라면
            if hda_license != houdini_api.HoudiniAPI.commercial_license():
                return False
        return True

    def _alert_invalid_rename(self, msg: str | None = None) -> None:
        self._rename_ihda.set_confirm_pixmap(False)
        self._rename_ihda.set_confirm_text(msg)
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("iHDA Node Rename")
        msgbox.setIcon(QtWidgets.QMessageBox.Warning)
        msgbox.setText("It's not a valid iHDA name.")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        _ = msgbox.exec()

    def _slot_hda_name_changed(self) -> None:
        if self._rename_ihda.is_valid_ihda_name:
            category = self._selection.asset.cate
            old_hda_name = self._selection.asset.name
            new_hda_name = self._rename_ihda.final_ihda_name
            hda_type_name = self._selection.asset.data.get(public.Key.node_type_name)
            if hda_type_name.find(":") >= 0:
                hda_type_name = hda_type_name.split(":")[0].strip()
            wrong_name = "{0}1".format(hda_type_name)
            # 등록해서는 안되는 노드 이름들
            if new_hda_name in [hda_type_name, wrong_name]:
                self._alert_invalid_rename(
                    msg="""
The "{0}" name is not allowed because it is the same or
similar to the current node type.

Type of current node: "{1}"
                """.format(new_hda_name, hda_type_name)
                )
            else:
                db_api = self._db_api_wrap(self._db_filepath)
                if db_api is None:
                    return
                is_exist_hda_name = db_api.is_exist_hda_name(
                    user_id=self._user, category=category, hda_name=new_hda_name
                )
                if is_exist_hda_name:
                    self._alert_invalid_rename(msg="iHDA with the same name exists.")
                else:
                    # iHDA directory 정보가 없다면
                    hda_dirpath = self._selection.asset.data.get(public.Key.hda_dirpath)
                    if hda_dirpath is None:
                        log_handler.LogHandler.log_msg(
                            method=logging.error, msg="no iHDA folder information"
                        )
                        self._rename_ihda.close()
                        return
                    # 만약 같은 공간에 같은 이름의 디렉토리가 존재한다면
                    dirname_lst = [
                        x.name if x.is_dir() else None
                        for x in hda_dirpath.parent.glob("*")
                    ]
                    if new_hda_name in dirname_lst:
                        self._alert_invalid_rename(
                            msg="A folder with the same name exists"
                        )
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg='a folder with the same name exists in the "{0}" space'.format(
                                hda_dirpath.parent.as_posix()
                            ),
                        )
                    else:
                        self._rename_ihda.close()
                        self._dragdrop_overlay_show(text="Change iHDA Node Name")
                        is_done = self._change_ihda_name(
                            new_hda_name=new_hda_name, db_api=db_api
                        )
                        self._dragdrop_overlay_close()
                        if is_done:
                            log_handler.LogHandler.log_msg(
                                method=logging.debug,
                                msg='renamed "{0}" >>>>> "{1}"'.format(
                                    old_hda_name, new_hda_name
                                ),
                            )

    def _change_ihda_name(
        self, new_hda_name: str | None = None, db_api: SQLite3DatabaseAPI | None = None
    ) -> bool:
        data = self._selection.asset.data
        if data is None or new_hda_name is None or db_api is None:
            return False
        hda_id = data[public.Key.hda_id]
        hda_version = data[public.Key.hda_version]
        row = self._assets.id_rows.get(hda_id)
        if row is None:
            return False
        self._video_player.player_stop()
        self._delete_video_playlist(
            video_filepath_list=db_api.get_history_video_info(hda_key_id=hda_id)
        )
        try:
            plan = build_rename_plan(
                data,
                new_hda_name,
                self._services.names,
                rename_video=db_api.is_video_and_ihda_same_version(
                    hda_key_id=hda_id, version=hda_version
                ),
            )
            is_update_hda_name, is_update_hda_name_hist = rename_asset(
                self._services.rename_repository(db_api), plan
            )
        except Exception:
            logging.exception(
                "Could not rename asset; recovery copies retained if rollback failed"
            )
            return False
        new_hda_dirpath, new_hda_filename = plan.directory, plan.filename
        new_node_old_path = plan.node_path
        new_hda_filepath = plan.directory / plan.filename
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
            self._selection.asset.name = new_hda_name
            self._selection.asset.filepath = new_hda_filepath
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
                # history trigger 주석처리로 인해 DB 삽입을 직접해줘야 한다.
                self._insert_hist_db_from_curt_hist_data(
                    db_api=db_api, comment="NAME (CHANGE)"
                )
            return True
        else:
            return False

    def _get_hda_id_row_map(self) -> Mapping[int, int]:
        return self._assets.id_rows

    def _slot_db_cleanup(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("iHDA Database Optimization")
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText("Cleanup unnecessary information from database?")
        msgbox.setDetailedText(
            "NOTE: Don't worry. Only unused information is cleaned up."
        )
        chkbox = QtWidgets.QCheckBox(msgbox)
        chkbox.setText("Cleanup other info together")
        chkbox.setChecked(True)
        chkbox.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_query_builder_white.png"))
        )
        chkbox.setToolTip("Cleanup other information together (history & record)")
        msgbox.setCheckBox(chkbox)
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.Yes:
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            item_row_dat = dict()
            for hda_info_dat in db_api.get_all_hda_fileinfo(user_id=self._user):
                hda_id, hda_dirpath, hda_filename, hda_cate = hda_info_dat
                hda_dirpath = pathlib.Path(hda_dirpath)
                hda_filepath = hda_dirpath / hda_filename
                if not hda_filepath.exists():
                    db_api.delete_hda_key_with_id(hda_key_id=hda_id)
                    item_row = self._get_hda_model_row_by_hda_id(hda_id=hda_id)
                    if item_row is not None:
                        item_row_dat[item_row] = [hda_id, hda_cate]
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg="ID {0} iHDA information has been cleaned up".format(
                            hda_id
                        ),
                    )
            if len(item_row_dat):
                cate_lst = db_api.get_hda_category(user_id=self._user)
                for hrow, hval in sorted(iter(item_row_dat.items()), reverse=True):
                    hid, hcate = hval
                    self._remove_hda_data(item_row=hrow)
                    self._delete_hist_combobox_ihda_item(hkey_id=hid)
                    self._remove_category_item(category=hcate, category_list=cate_lst)
            if chkbox.isChecked():
                # history 정리
                item_row_lst = list()
                for hist_info_dat in db_api.get_all_hda_history_fileinfo(
                    user_id=self._user
                ):
                    hist_id, hda_id, hda_dirpath, hda_filename = hist_info_dat
                    hda_dirpath = pathlib.Path(hda_dirpath)
                    hda_filepath = hda_dirpath / hda_filename
                    if not hda_filepath.exists():
                        db_api.delete_hda_history(hist_id=hist_id)
                        self._delete_hist_combobox_ihda_item(hkey_id=hda_id)
                        item_row = self._ihda_history_model.get_hist_item_row_by_hist_id_from_model(
                            hist_id=hist_id
                        )
                        if item_row is not None:
                            insort_right(item_row_lst, item_row)
                        log_handler.LogHandler.log_msg(
                            method=logging.info,
                            msg="ID {0} history information has been cleaned up".format(
                                hist_id
                            ),
                        )
                hist_id_row_map = (
                    self._ihda_history_model.get_hist_id_row_map_from_model()
                )
                for item_row in reversed(item_row_lst):
                    if item_row in list(hist_id_row_map.values()):
                        self._ihda_history_model.remove_item(row=item_row)
                # record 정리
                self._delete_unused_hda_record_info(db_api=db_api)
            log_handler.LogHandler.log_msg(
                method=logging.debug, msg="iHDA database optimization is complete"
            )
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setWindowTitle("Cleanup iHDA Database")
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText("iHDA database optimization is complete.")
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec()

    def _slot_delete_all_history(self) -> None:
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        cnt_hda_hist = db_api.count_hda_history()
        cnt_hda_note_hist = db_api.count_hda_note_history()
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("Delete all iHDA history")
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText("Delete all iHDA node's node/note history?")
        # chkbox = QtWidgets.QCheckBox(msgbox)
        # chkbox.setText('Delete All History Files')
        # chkbox.setChecked(True)
        # chkbox.setIcon(QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        # chkbox.setToolTip('Delete all iHDA history files')
        # msgbox.setCheckBox(chkbox)
        msgbox.setDetailedText(
            """
All of them are deleted, leaving minimal data for data tracking.
iHDA node history: {0}
iHDA note history: {1}
        """.format(cnt_hda_hist, cnt_hda_note_hist)
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgbox.setStyleSheet("QLabel {min-width: 500px;}")
        msgbox.resize(msgbox.sizeHint())
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.Yes:
            # 만약 파일들까지 삭제한다면
            # if chkbox.isChecked():
            all_hkey_id = db_api.get_hda_key_id(user_id=self._user)
            if all_hkey_id is None:
                return
            # player가 재생중이거나 일시정지 상태면 정지
            self._video_player.player_stop()
            del_hist_data_lst = list()
            for hkey_id in sorted(all_hkey_id, reverse=True):
                # video playlist 삭제
                # 현재 iHDA 노드의 모든 video file 정보
                video_filepath_lst = db_api.get_history_video_info(hda_key_id=hkey_id)
                self._delete_video_playlist(video_filepath_list=video_filepath_lst)
                hist_data_lst = (
                    self._ihda_history_model.get_hist_data_by_hkey_id_from_model(
                        hkey_id=hkey_id
                    )
                )
                del_hist_data_lst.extend(hist_data_lst)
            for hist_data in sorted(
                del_hist_data_lst,
                key=lambda x: x.get(public.Key.History.item_row),
                reverse=True,
            ):
                self._delete_each_hist_ihda_item(
                    hist_data=hist_data, db_api=db_api, verbose=True
                )
            # note history 정보 삭제
            db_api.delete_hda_note_history()
            self._initialize_hist_current_attribs()
            self._clear_hist_parms()

    def _hda_favorite(self) -> None:
        if self._selection.asset.data is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="no node selected "
            )
            return
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        hda_id = self._selection.asset.id
        is_update = db_api.update_hda_favorite(hda_key_id=hda_id)
        if bool(is_update):
            row = self._assets.id_rows.get(self._selection.asset.id)
            key = public.Key.is_favorite_hda
            val = self._selection.asset.data.get(public.Key.is_favorite_hda) ^ 1
            hda_name = self._selection.asset.name
            self._change_hda_data(row=row, key=key, val=val)
            if val:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='the "{0}" node has been set as a favorite node'.format(
                        hda_name
                    ),
                )
            else:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='the "{0}" node has been released from the favorites node'.format(
                        hda_name
                    ),
                )

    def _remove_selected_record_item(self, index: QtCore.QModelIndex = None) -> None:
        if not index.isValid():
            return
        record_data_name = index.data(QtCore.Qt.DisplayRole)
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setWindowTitle("Remove iHDA Record Information")
        msgbox.setText(
            'Are you sure you want to delete the selected "{0}" record information?'.format(
                record_data_name
            )
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.No:
            return
        record_id_list = self._ihda_record_model.remove_selected_record_data(
            index=index
        )
        # DB 삭제
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        for record_id in sorted(record_id_list):
            is_removed = db_api.delete_hda_record(record_id=record_id)
            if is_removed:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='"{0}" data on record ID {1} has been deleted'.format(
                        record_data_name, record_id
                    ),
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
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setWindowTitle("Remove iHDA History Node")
        msgbox.setText(
            'Delete the <font color=red>"{0}"</font> selected iHDA nodes?\n'
            "File/DB is also deleted".format(len(indexes))
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.Yes:
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
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
                self._delete_each_hist_ihda_item(
                    hist_data=hist_data, db_api=db_api, verbose=True
                )
        self._initialize_hist_current_attribs()
        self._clear_hist_parms()

    def _remove_hda_item(self, indexes: Any = None) -> None:
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        # player가 재생중이거나 일시 정지상태면 정지
        self._video_player.player_stop()
        # 삭제할 히스토리 데이터 수거
        del_hist_data_lst = list()
        # iHDA 노드 데이터 삭제
        role = (
            ihda_list_model.ListModel.data_role
            if self._is_icon_mode
            else ihda_table_model.TableModel.data_role
        )
        selected = {
            index.data(role)[public.Key.hda_id]: dict(index.data(role))
            for index in indexes
            if index.isValid()
        }
        for hda_id, item in selected.items():
            item_row = self._get_hda_id_row_map().get(hda_id)
            if item_row is None:
                continue
            hda_name = item[public.Key.hda_name]
            hda_dirpath = item[public.Key.hda_dirpath]
            hda_cate = item[public.Key.hda_cate]
            self._delete_ihda_item(
                hda_id=hda_id,
                hda_cate=hda_cate,
                hda_name=hda_name,
                hda_dirpath=hda_dirpath,
                item_row=item_row,
                db_api=db_api,
            )
            # 삭제할 히스토리 데이터 수거
            hist_data_lst = (
                self._ihda_history_model.get_hist_data_by_hkey_id_from_model(
                    hkey_id=hda_id
                )
            )
            del_hist_data_lst.extend(hist_data_lst)
        # 히스토리 데이터 삭제 (DB는 삭제 안해도 된다. hda 데이터 지우면 자동 삭제 됨)
        # iHDA 데이터를 지우면 constraint로 인하여 history 데이터도 지워져서 DB는 지울 필요 없다.
        for hist_data in sorted(
            del_hist_data_lst,
            key=lambda x: x.get(public.Key.History.item_row),
            reverse=True,
        ):
            del_hist_row = hist_data.get(public.Key.History.item_row)
            del_hist_id = hist_data.get(public.Key.History.hist_id)
            del_hda_id = hist_data.get(public.Key.History.hda_id)
            self._ihda_history_model.remove_item(row=del_hist_row)
            self._remove_pixmap_hist_thumbnail(hist_id=del_hist_id)
            # 히스토리 콤보박스 아이템 삭제
            self._delete_hist_combobox_ihda_item(hkey_id=del_hda_id)
        self._initialize_current_attribs()
        self._initialize_hist_current_attribs()
        self._clear_parms()
        self._clear_hist_parms()
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
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
        db_api: SQLite3DatabaseAPI | None = None,
    ) -> None:
        assert isinstance(hda_dirpath, pathlib.Path)
        video_filepath_lst = db_api.get_history_video_info(hda_key_id=hda_id)
        self._delete_video_playlist(video_filepath_list=video_filepath_lst)
        try:
            delete_asset(db_api, hda_id, hda_dirpath)
        except Exception:
            logging.exception("Asset deletion failed; library views retained")
            return
        self._remove_hda_data(item_row=item_row)
        self._ihda_record_model.remove_record_item_by_hda_id(hda_id=hda_id)
        self._remove_pixmap_ihda(hkey_id=hda_id)
        self._remove_pixmap_thumbnail(hkey_id=hda_id)
        cate_lst = db_api.get_hda_category(user_id=self._user)
        self._remove_category_item(category=hda_cate, category_list=cate_lst)
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f'"{hda_name}" iHDA node has been removed'
        )

    def _delete_each_hist_ihda_item(
        self,
        hist_data: Any = None,
        db_api: SQLite3DatabaseAPI | None = None,
        verbose: bool = True,
    ) -> bool:
        hda_id = hist_data.get(public.Key.History.hda_id)
        hist_id = hist_data.get(public.Key.History.hist_id)
        hda_name = hist_data.get(public.Key.History.org_hda_name)
        row = hist_data.get(public.Key.History.item_row)
        hda_ver = hist_data.get(public.Key.History.version)
        hda_dirpath = hist_data.get(public.Key.History.ihda_dirpath)
        hda_filename = hist_data.get(public.Key.History.ihda_filename)
        hda_filepath = hda_dirpath / hda_filename
        thumb_dirpath = hist_data.get(public.Key.History.thumb_dirpath)
        video_dirpath = hist_data.get(public.Key.History.video_dirpath)
        # 가장 최근의 히스토리라면, 삭제를 진행하지 않는다.
        if db_api.is_most_recent_ihda_history(hda_key_id=hda_id, hist_id=hist_id):
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg="[{0}/{1}] node is the most recent iHDA history. it cannot be deleted".format(
                        hda_name, hda_ver
                    ),
                )
            return False
        files = []
        if not db_api.is_ihda_lastest_version(hda_key_id=hda_id, version=hda_ver):
            files.append(hda_filepath)
            if thumb_dirpath is not None:
                files.append(
                    thumb_dirpath / hist_data[public.Key.History.thumb_filename]
                )
            if video_dirpath is not None:
                video_filepath = (
                    video_dirpath / hist_data[public.Key.History.video_filename]
                )
                self._video_player.delete_playlist_item_by_filepath(
                    filepath=video_filepath
                )
                files.append(video_filepath)
        try:
            delete_history(db_api, hda_id, hist_id, files)
        except Exception:
            logging.exception("History deletion failed; library views retained")
            return False
        self._ihda_history_model.remove_item(row=row)
        self._delete_hist_combobox_ihda_item(hkey_id=hda_id)
        self._remove_pixmap_hist_thumbnail(hist_id=hist_id)
        rowcnt = 1
        if bool(rowcnt):
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg="[{0}/{1}] iHDA history removed".format(hda_name, hda_ver),
                )
            return True
        return False

    def _delete_hist_combobox_ihda_item(self, hkey_id: int | None = None) -> None:
        # history가 존재하지 않는다면
        if not self._ihda_history_model.is_exist_ihda_item_from_model(hkey_id=hkey_id):
            for idx in range(self.comboBox__hist_ihda_node.count()):
                hid = self.comboBox__hist_ihda_node.itemData(idx)
                if hkey_id == hid:
                    self.comboBox__hist_ihda_node.removeItem(idx)
