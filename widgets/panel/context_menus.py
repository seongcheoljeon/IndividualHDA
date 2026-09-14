"""Context menus for the Individual HDA panel.

Mixin methods run on the panel GUI thread and share its protected state.
They do not own a separate QWidget or change the public panel interface.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtGui, QtWidgets

import public
from libs import houdini_api, ihda_system, log_handler
from model import (
    ihda_inside_model,
    ihda_list_model,
    ihda_record_model,
    ihda_table_model,
)


class ContextMenusMixin:
    def _build_context_history_menu(self, point: QtCore.QPoint) -> None:
        index = self._ihda_history_view.indexAt(point)
        if not index.isValid():
            return
        if not self._is_valid_hist_current_item_data:
            return
        context_menu = QtWidgets.QMenu(self)
        open_context_menu = QtWidgets.QMenu("Open", self)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
        )
        action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
        action_open_context_ihda_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
        )
        # hip folder
        action_open_context_hip_folder = open_context_menu.addAction("HIP Folder")
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
        )
        open_context_menu.addSeparator()
        # hip file
        action_open_context_hip_file = open_context_menu.addAction("HIP File")
        action_open_context_hip_file.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/hipfile.png"))
        )
        action_context_menu_detail = context_menu.addAction("Detail")
        action_context_menu_detail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_format_quote_white.png"))
        )
        action_context_menu_remove = context_menu.addAction("Delete")
        action_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_delete_forever_white.png"))
        )
        context_menu.addMenu(open_context_menu)
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_detail)
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_remove)
        # refresh current data
        self._selection.history.field = index.data()
        self._refresh_history_current_attribs()
        self._set_hda_hist_info_to_parms()
        if self._selection.history.data is None:
            return
        hip_dirpath = self._selection.history.data.get(public.Key.History.hip_dirpath)
        action = context_menu.exec(self._ihda_history_view.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=self._selection.history.filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            hip_filepath = hip_dirpath / self._selection.history.data.get(
                public.Key.History.hip_filename
            )
            self._open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_context_menu_detail:
            self._detail_view_ihda_data(data=self._selection.history.data)
        elif action == action_context_menu_remove:
            self._remove_hist_item()
        else:
            pass

    def _build_context_ihda_menu(self, point: QtCore.QPoint) -> None:
        if self._is_icon_mode:
            view = self._ihda_list_view
        else:
            view = self._ihda_table_view
        index = view.indexAt(point)
        if not index.isValid():
            return
        if not self._is_valid_current_hda_item_data:
            return
        context_menu = QtWidgets.QMenu(self)
        open_context_menu = QtWidgets.QMenu("Open", self)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
        )
        action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
        action_open_context_ihda_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
        )
        action_open_context_hip_folder = open_context_menu.addAction("HIP Folder")
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
        )
        open_context_menu.addSeparator()
        action_open_context_hip_file = open_context_menu.addAction("HIP File")
        action_open_context_hip_file.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/hipfile.png"))
        )

        hda_context_menu = QtWidgets.QMenu("iHDA", self)
        hda_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/houdini_logo_white.png"))
        )

        action_hda_context_menu_favorite = hda_context_menu.addAction("Favorite")
        favorite_icon = "ic_favorite_border_white.png"
        if self._selection.asset.data.get(public.Key.is_favorite_hda):
            favorite_icon = "ic_favorite_white.png"
        action_hda_context_menu_favorite.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/main/icons/{favorite_icon}"))
        )

        action_hda_context_menu_detail = hda_context_menu.addAction("Detail")
        action_hda_context_menu_detail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_format_quote_white.png"))
        )
        action_hda_context_menu_ai = hda_context_menu.addAction("AI: Suggest Note/Tags")
        action_hda_context_menu_ai.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_new_releases_white.png"))
        )
        action_hda_make_context_menu_rename = hda_context_menu.addAction("Rename")
        action_hda_make_context_menu_rename.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_border_color_white.png"))
        )
        hda_context_menu.addSeparator()
        hda_make_context_menu = QtWidgets.QMenu("Make", self)
        hda_make_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_camera_white.png"))
        )
        action_hda_make_context_menu_thumbnail = hda_make_context_menu.addAction(
            "Thumbnail"
        )
        action_hda_make_context_menu_thumbnail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_camera_alt_white.png"))
        )
        action_hda_make_context_menu_video = hda_make_context_menu.addAction("Video")
        action_hda_make_context_menu_video.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_videocam_white.png"))
        )
        hda_context_menu.addMenu(hda_make_context_menu)
        hda_context_menu.addSeparator()
        action_hda_context_menu_remove = hda_context_menu.addAction("Delete")
        action_hda_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_delete_forever_white.png"))
        )
        # History
        hist_context_menu = QtWidgets.QMenu("History", self)
        hist_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_query_builder_white.png"))
        )
        # history actions
        action_hist_context_menu_ihda_history = hist_context_menu.addAction("iHDA")
        action_hist_context_menu_ihda_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_find_in_page_white.png"))
        )
        action_hist_context_menu_note_history = hist_context_menu.addAction("Note")
        action_hist_context_menu_note_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_assignment_white.png"))
        )
        hist_context_menu.addSeparator()
        action_hist_context_menu_remove_history = hist_context_menu.addAction("Delete")
        action_hist_context_menu_remove_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_delete_forever_white.png"))
        )
        context_menu.addMenu(open_context_menu)
        context_menu.addMenu(hda_context_menu)
        context_menu.addMenu(hist_context_menu)
        context_menu.addSeparator()
        # refresh current data
        self._selection.asset.field = index.data()
        self._refresh_current_attribs()
        self._set_hda_info_to_parms()

        if self._selection.asset.data is None:
            return
        hip_dirpath = self._selection.asset.data.get(public.Key.hip_dirpath)
        action = context_menu.exec(view.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=self._selection.asset.filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            hip_filepath = hip_dirpath / self._selection.asset.data.get(
                public.Key.hip_filename
            )
            self._open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_hda_context_menu_favorite:
            self._hda_favorite()
        elif action == action_hda_context_menu_detail:
            self._detail_view_ihda_data(data=self._selection.asset.data)
        elif action == action_hda_context_menu_ai:
            self._slot_ai_suggest()
        elif action == action_hda_make_context_menu_thumbnail:
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            self._wrapper_execute_deferred(
                lambda: self._slot_make_thumbnail(db_api=db_api)
            )
        elif action == action_hda_make_context_menu_video:
            if public.IS_HOUDINI:
                frinfo = houdini_api.HoudiniAPI.frame_info()
                self._make_videoinfo.sf = frinfo[0]
                self._make_videoinfo.ef = frinfo[1]
                self._make_videoinfo.fps = frinfo[2]
            self._make_videoinfo.show()
        elif action == action_hda_make_context_menu_rename:
            self._rename_ihda.clear_parms()
            self._rename_ihda.set_old_ihda_name(self._selection.asset.name)
            self._rename_ihda.show()
        elif action == action_hda_context_menu_remove:
            if self._is_icon_mode:
                indexes = self._ihda_list_view.selectedIndexes()
            else:
                # table 모델은 이렇게 해야한다. 왜냐면 cell 선택시 모든 cell을 선택되어지도록 했는데
                # 이것 때문에 중복 index가 생겨 첫번째 컬럼을 명확시 지정하였다.
                indexes = self._ihda_table_view.selectionModel().selectedRows(0)
            if not len(indexes):
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="iHDA node is not selected"
                )
                return
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setIcon(QtWidgets.QMessageBox.Question)
            msgbox.setWindowTitle("Remove iHDA Node")
            msgbox.setText(
                f'Delete the <font color=red>"{len(indexes)}"</font> selected iHDA nodes?'
            )
            msgbox.setInformativeText(
                "All information about that node, including previews, video, thumbnails\n"
                "history and reocrds, will be deleted. (Folder/File/DB is also deleted)"
            )
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            msgbox.setStyleSheet("QLabel {min-width: 500px;}")
            msgbox.resize(msgbox.sizeHint())
            reply = msgbox.exec()
            if reply != QtWidgets.QMessageBox.Yes:
                return
            self._remove_hda_item(indexes=indexes)
        elif action == action_hist_context_menu_ihda_history:
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            hda_name = self._selection.asset.name
            hda_id = self._selection.asset.id
            if not db_api.is_exist_hda_history(hda_key_id=hda_id):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'node history of "{hda_name}" iHDA node does not exist',
                )
                return
            self._slot_select_view(index=self._hist_view_idx)
            self._select_hist_ihda_combobox_item(hkey_id=hda_id)
        elif action == action_hist_context_menu_note_history:
            hda_name = self._selection.asset.name
            hda_id = self._selection.asset.id
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            hist_note_data = db_api.get_hda_note_history(
                hda_key_id=hda_id, with_datetime=True
            )
            self._slot_hda_note_history(
                hist_note_data=hist_note_data, hda_name=hda_name
            )
        elif action == action_hist_context_menu_remove_history:
            if self._is_icon_mode:
                indexes = self._ihda_list_view.selectedIndexes()
            else:
                # table 모델은 이렇게 해야한다. 왜냐면 cell 선택시 모든 cell을 선택되어지도록 했는데
                # 이것 때문에 중복 index가 생겨 첫번째 컬럼을 명확시 지정하였다.
                indexes = self._ihda_table_view.selectionModel().selectedRows(0)
            if not len(indexes):
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="iHDA node is not selected"
                )
                return
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setWindowTitle("Delete iHDA node history")
            msgbox.setIcon(QtWidgets.QMessageBox.Question)
            msgbox.setText(
                f'Delete the selected <font color=red>"{len(indexes)}"</font> iHDA node history?'
            )
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            reply = msgbox.exec()
            if reply == QtWidgets.QMessageBox.No:
                return
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            # player가 재생중이거나 일시정지 상태면 정지
            self._video_player.player_stop()
            del_hist_data_lst = list()
            for index in sorted(indexes, key=lambda x: x.row(), reverse=True):
                if not index.isValid():
                    continue
                if self._is_icon_mode:
                    hda_id = index.data(ihda_list_model.ListModel.id_role)
                    hda_name = index.data(ihda_list_model.ListModel.name_role)
                else:
                    hda_id = index.data(ihda_table_model.TableModel.id_role)
                    hda_name = index.data(ihda_table_model.TableModel.name_role)
                if db_api.is_exist_hda_note_history(hda_key_id=hda_id):
                    db_api.delete_hda_note_history(hda_key_id=hda_id)
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg=f'all the note history of "{hda_name}" iHDA node has been deleted',
                    )
                if not db_api.is_exist_hda_history(hda_key_id=hda_id):
                    log_handler.LogHandler.log_msg(
                        method=logging.warning,
                        msg=f'node history of "{hda_name}" iHDA node does not exist',
                    )
                    continue
                # 삭제할 히스토리 데이터 수거
                hist_data_lst = (
                    self._ihda_history_model.get_hist_data_by_hkey_id_from_model(
                        hkey_id=hda_id
                    )
                )
                del_hist_data_lst.extend(hist_data_lst)
                # video playlist 삭제
                # 현재 iHDA 노드의 모든 video file 정보
                video_filepath_lst = db_api.get_history_video_info(hda_key_id=hda_id)
                self._delete_video_playlist(video_filepath_list=video_filepath_lst)
            # 히스토리 데이터 삭제
            for hist_data in sorted(
                del_hist_data_lst,
                key=lambda x: x.get(public.Key.History.item_row),
                reverse=True,
            ):
                self._delete_each_hist_ihda_item(
                    hist_data=hist_data, db_api=db_api, verbose=True
                )
            self._initialize_hist_current_attribs()
            self._clear_hist_parms()
        else:
            pass

    def _build_context_category_menu(self, point: QtCore.QPoint) -> None:
        index = self._ihda_category_view.indexAt(point)
        if not index.isValid():
            return

    def _build_context_record_menu(self, point: QtCore.QPoint) -> None:
        index = self._ihda_record_view.indexAt(point)
        if not index.isValid():
            return
        item_type = index.data(ihda_record_model.RecordModel.record_type_role)
        if item_type == public.Type.root:
            return
        hip_dirpath = index.data(ihda_record_model.RecordModel.hip_dirpath_role)
        hip_filepath = index.data(ihda_record_model.RecordModel.hip_filepath_role)
        hda_filepath = index.data(ihda_record_model.RecordModel.hda_filepath_role)
        record_data = index.data(ihda_record_model.RecordModel.record_data_role)
        pnode_path = index.data(ihda_record_model.RecordModel.pnode_path_role)
        context_menu = QtWidgets.QMenu(self)
        open_context_menu = QtWidgets.QMenu("Open", self)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
        )
        # hip folder
        action_open_context_hip_folder = open_context_menu.addAction("HIP Folder")
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
        )
        # hip file
        action_open_context_hip_file = None
        if hip_filepath is not None:
            action_open_context_hip_file = open_context_menu.addAction("HIP File")
            action_open_context_hip_file.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/hipfile.png"))
            )
            open_context_menu.addSeparator()
        # iHDA folder
        action_open_context_ihda_folder = None
        if hda_filepath is not None:
            action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
            action_open_context_ihda_folder.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
            )
        # go to network
        action_context_menu_go_to_network = None
        if pnode_path is not None:
            action_context_menu_go_to_network = context_menu.addAction("Go To Network")
            action_context_menu_go_to_network.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_flight_takeoff_white.png"))
            )
            context_menu.addAction(action_context_menu_go_to_network)
        # detail view
        action_context_menu_detail = None
        if record_data is not None:
            action_context_menu_detail = context_menu.addAction("Detail")
            action_context_menu_detail.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_format_quote_white.png"))
            )
            context_menu.addAction(action_context_menu_detail)
        action_context_menu_remove = context_menu.addAction("Delete")
        action_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_delete_forever_white.png"))
        )
        context_menu.addMenu(open_context_menu)
        context_menu.addSeparator()
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_remove)
        action = context_menu.exec(self._ihda_record_view.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hda_filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            self._open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_context_menu_go_to_network:
            self._go_to_houdini_node(node_path=pnode_path)
        elif action == action_context_menu_detail:
            record_id = index.data(ihda_record_model.RecordModel.record_id_role)
            if record_id is None:
                return
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            record_data = db_api.get_only_detailview_record_data(record_id=record_id)
            self._detail_view_record_data(record_data=record_data)
        elif action == action_context_menu_remove:
            self._remove_selected_record_item(index=index)
        else:
            pass

    def _build_context_inside_menu(self, point: QtCore.QPoint) -> None:
        index = self._ihda_inside_view.indexAt(point)
        if not index.isValid():
            return
        item_type = index.data(ihda_inside_model.InsideModel.node_type_role)
        if item_type == public.Type.root:
            return
        is_ihda_node = bool(item_type == public.Type.ihda)
        hda_id = index.data(ihda_inside_model.InsideModel.hda_id_role)
        context_menu = QtWidgets.QMenu(self)
        # go to node
        action_context_menu_go_to_node = context_menu.addAction("Go To Node")
        action_context_menu_go_to_node.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_flight_takeoff_white.png"))
        )
        context_menu.addAction(action_context_menu_go_to_node)
        context_menu.addSeparator()
        action_open_context_ihda_folder = None
        action_open_context_ihda_video = None
        action_context_menu_detail = None
        if is_ihda_node:
            open_context_menu = QtWidgets.QMenu("Open", self)
            open_context_menu.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
            )
            # iHDA folder
            action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
            action_open_context_ihda_folder.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_folder_white.png"))
            )
            open_context_menu.addSeparator()
            # iHDA video
            action_open_context_ihda_video = open_context_menu.addAction("iHDA Video")
            action_open_context_ihda_video.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_movie_white.png"))
            )
            context_menu.addMenu(open_context_menu)
            context_menu.addSeparator()
        action = context_menu.exec(self._ihda_inside_view.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            if hda_id is None:
                return
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            hda_fpath = db_api.get_hda_filepath(hda_key_id=hda_id)
            ihda_system.IHDASystem.open_folder(dirpath=hda_fpath)
        elif action == action_open_context_ihda_video:
            if hda_id is None:
                return
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            hda_ver = index.data(ihda_inside_model.InsideModel.version_role)
            hda_name = index.data(ihda_inside_model.InsideModel.hda_org_name_role)
            video_info = db_api.get_hda_history_video_most_recent_by_ver(
                hda_key_id=hda_id, version=hda_ver
            )
            if video_info is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'"{hda_name} (v{hda_ver})" iHDA node has no video',
                )
                return
            self._play_video_most_recent_by_version(video_info=video_info)
        elif action == action_context_menu_go_to_node:
            node_path = index.data(ihda_inside_model.InsideModel.node_path_role)
            self._go_to_houdini_node(node_path=node_path)
        else:
            pass
