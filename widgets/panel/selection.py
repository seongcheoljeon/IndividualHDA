"""Selection for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

import logging
from operator import itemgetter
from typing import Any

from PySide6 import QtCore, QtGui

import public
from libs import houdini_api, log_handler
from model import (
    ihda_history_model,
    ihda_inside_model,
    ihda_list_model,
    ihda_record_model,
    ihda_table_model,
)

try:
    import hou
except ImportError:
    pass


class SelectionMixin:
    def _init_set_first_ihda_item(self) -> None:
        # 처음 시작 시, 첫 번째 노드가 선택되어지도록
        self._ihda_list_view.setCurrentIndex(
            self._ihda_list_proxy_model.index(0, 0, QtCore.QModelIndex())
        )
        self._ihda_table_view.setCurrentIndex(
            self._ihda_table_proxy_model.index(0, 0, QtCore.QModelIndex())
        )
        self._slot_on_hda_item_clicked(
            self._ihda_list_proxy_model.index(0, 0, QtCore.QModelIndex())
        )

    def _init_select_ihda_category_model(self) -> None:
        idx = self._ihda_category_proxy_model.index(0, 0, QtCore.QModelIndex())
        self._ihda_category_view.setCurrentIndex(idx)
        self._slot_selected_category(idx)

    def _init_set_hist_ihda_combobox(self) -> None:
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        self._default_set_hist_ihda_combobox()
        for val_lst in db_api.get_hda_name(user_id=self._user, with_id=True):
            hkey_id, hda_name = val_lst
            if not db_api.is_exist_hda_history(hda_key_id=hkey_id):
                continue
            self._set_hist_ihda_to_combobox(hkey_id=hkey_id, hda_name=hda_name)

    def _default_set_hist_ihda_combobox(self) -> None:
        self.comboBox__hist_ihda_node.clear()
        root_icon = QtGui.QIcon(
            self._ihda_icons.pixmap_cate_data.get(public.Name.Icons.root).scaled(30, 30)
        )
        self.comboBox__hist_ihda_node.addItem(root_icon, "ALL", -1)
        self.comboBox__hist_ihda_node.setCurrentIndex(0)

    def _init_set_inside_ihda_combobox(self) -> None:
        self._default_set_inside_ihda_combobox()
        ihda_node_lst = self._ihda_inside_model.get_ihda_node_list()
        if not len(ihda_node_lst):
            return
        for node_info in sorted(ihda_node_lst, key=itemgetter(0)):
            node_name, hda_id, node_path = node_info
            self._set_inside_ihda_to_combobox(
                hkey_id=hda_id, hda_name=node_name, node_path=node_path
            )

    def _default_set_inside_ihda_combobox(self) -> None:
        self.comboBox__hda_inside_node.clear()
        root_icon = QtGui.QIcon(
            self._ihda_icons.pixmap_cate_data.get(public.Name.Icons.root).scaled(30, 30)
        )
        self.comboBox__hda_inside_node.addItem(root_icon, "ALL", -1)
        self.comboBox__hda_inside_node.setCurrentIndex(0)

    def _set_hist_ihda_to_combobox(
        self, hkey_id: int | None = None, hda_name: str | None = None
    ) -> None:
        if hkey_id not in self._get_all_hist_ihda_combobox_data():
            icon = QtGui.QIcon(
                self._ihda_icons.pixmap_ihda_data.get(hkey_id).scaled(30, 30)
            )
            self.comboBox__hist_ihda_node.addItem(icon, hda_name, hkey_id)

    def _set_inside_ihda_to_combobox(
        self,
        hkey_id: int | None = None,
        hda_name: str | None = None,
        node_path: str | None = None,
    ) -> None:
        pixmap = self._ihda_icons.pixmap_ihda_data.get(hkey_id)
        # 만약 iHDA 노드를 삭제해서 pixmap 데이터가 존재하지 않는다면 직접 후디니 icon을 가공하여 가져온다.
        if pixmap is None:
            node = hou.node(node_path)
            if node is None:
                icon_lst = None
            else:
                icon_lst = houdini_api.HoudiniAPI.node_icon_path_lst(node)
            pixmap = self._ihda_icons.get_houdini_icon(icon_lst=icon_lst)
        icon = QtGui.QIcon(pixmap.scaled(30, 30))
        self.comboBox__hda_inside_node.addItem(icon, hda_name, hkey_id)

    def _get_all_hist_ihda_combobox_data(self) -> list[Any]:
        return [
            int(self.comboBox__hist_ihda_node.itemData(i))
            for i in range(self.comboBox__hist_ihda_node.count())
        ]

    def _select_hist_ihda_combobox_item(self, hkey_id: int | None = None) -> None:
        find_idx = self._find_hist_ihda_combobox_index(hkey_id=hkey_id)
        if find_idx is not None:
            self.comboBox__hist_ihda_node.setCurrentIndex(find_idx)

    def _find_hist_ihda_combobox_index(self, hkey_id: int | None = None) -> int | None:
        find_idx = None
        for idx in range(self.comboBox__hist_ihda_node.count()):
            cm_item_hkey_id = int(self.comboBox__hist_ihda_node.itemData(idx))
            if hkey_id == cm_item_hkey_id:
                find_idx = idx
                break
        return find_idx

    def _slot_select_view(
        self, inst: Any = None, index: QtCore.QModelIndex = None
    ) -> None:
        view_idx_lst = [
            self._ihda_view_idx,
            self._video_view_idx,
            self._web_view_idx,
            self._hist_view_idx,
        ]
        btn_lst = [
            self.actioniHDA,
            self.actionVideo_Player,
            self.actionWeb,
            self.actionHistory,
        ]
        if index is not None:
            inst = btn_lst[index]
        if not inst.isChecked():
            inst.setChecked(True)
        for idx in range(len(btn_lst)):
            btn = btn_lst[idx]
            if btn != inst:
                btn.setChecked(False)
            else:
                view_idx = view_idx_lst[idx]
                self.stackedWidget__whole.setCurrentIndex(view_idx)

    def _slot_set_view_mode(self) -> None:
        if self._is_icon_mode:
            self.stackedWidget__hda.setCurrentIndex(0)
        else:
            self.stackedWidget__hda.setCurrentIndex(1)

    @QtCore.Slot(bool)
    def _slot_checkbox_hda_cate_casesensitive(self, idx: bool) -> None:
        self._search_filter_regexp_hda_cate(self.lineEdit__search_cate.text().strip())

    @QtCore.Slot(bool)
    def _slot_checkbox_hda_item_casesensitive(self, idx: bool) -> None:
        self._search_filter_regexp_hda_item(self.lineEdit__search_hda.text().strip())

    @QtCore.Slot(bool)
    def _slot_checkbox_hist_hda_item_casesensitive(self, idx: bool) -> None:
        self._search_filter_regexp_hist_hda_item(
            self.lineEdit__search_hda_hist.text().strip()
        )

    @QtCore.Slot(int)
    def _slot_set_search_target(self, idx: int) -> None:
        name = self.comboBox__search_type.itemText(idx)
        self._ihda_list_proxy_model.set_search_field(name)
        self._ihda_table_proxy_model.set_search_field(name)
        self._refresh_asset_search()

    @QtCore.Slot(int)
    def _slot_set_search_hist_field_target(self, idx: int) -> None:
        self._ihda_history_proxy_model.set_search_field(
            self.comboBox__search_field_hist.itemText(idx)
        )

    @QtCore.Slot(bool)
    def _slot_chk_hist_search_data(self, state: bool) -> None:
        self.dateEdit__hist_search_start.setEnabled(state)
        self.dateEdit__hist_search_end.setEnabled(state)
        self.label__join_str.setEnabled(state)
        self._slot_hist_ihda_search_date()

    @QtCore.Slot(int)
    def _slot_hist_ihda_combobox(self, idx: int) -> None:
        self.lineEdit__search_hda_hist.clear()
        hda_id = self.comboBox__hist_ihda_node.itemData(idx)
        self._ihda_history_proxy_model.set_hda_id(hda_id=hda_id)
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))

    @QtCore.Slot(int)
    def _slot_search_inside_node_combobox(self, idx: int) -> None:
        hda_id = self.comboBox__hda_inside_node.itemData(idx)
        self._ihda_inside_proxy_model.set_filter_attribute(hda_id=hda_id)
        self.label__found_hda_inside_hipfile_count.setText(
            str(self._ihda_inside_proxy_model.get_row_count())
        )
        self._ihda_inside_view.expandAll()

    def _slot_hist_ihda_search_date(self, *args: Any) -> None:
        datetime_lst = list()
        if self.checkBox__hist_search_date.isChecked():
            date_start = self.dateEdit__hist_search_start.date()
            date_end = self.dateEdit__hist_search_end.date()
            if date_start > date_end:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg="search date setting is wrong. please check and try again",
                )
                return
            datetime_lst = [
                date_start.toString(public.Value.qt_date_fmt_str),
                date_end.toString(public.Value.qt_date_fmt_str),
            ]
            log_handler.LogHandler.log_msg(
                method=logging.info,
                msg='historical data in the range of "{0} ~ {1}" were retrieved'.format(
                    *datetime_lst
                ),
            )
        self._ihda_history_proxy_model.set_datetime(datetime_lst=datetime_lst)
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))

    def _select_category(self, category: str | None = None) -> None:
        root_idx = self._ihda_category_proxy_model.index(0, 0, QtCore.QModelIndex())
        find_idx = self._find_tree_element_model(index=root_idx, find_name=category)
        if find_idx is None:
            return
        self._ihda_category_view.setCurrentIndex(find_idx)

    def _select_model_item_by_hda_id(self, hda_id: int | None = None) -> None:
        if self._is_ihda_history_view:
            # history가 존재하지 않으면
            if not self._ihda_history_model.is_exist_ihda_item_from_model(
                hkey_id=hda_id
            ):
                return
            self._select_hist_ihda_combobox_item(hkey_id=hda_id)
        else:
            if self._is_icon_mode:
                model_hda = self._ihda_list_proxy_model
                view_hda = self._ihda_list_view
            else:
                model_hda = self._ihda_table_proxy_model
                view_hda = self._ihda_table_view
            find_idx = self._find_hda_id_by_model_item(
                model_hda=model_hda, find_hda_id=hda_id
            )
            if find_idx is None:
                return
            view_hda.setCurrentIndex(find_idx)
            self._slot_on_hda_item_clicked(find_idx)

    def _refresh_history_current_attribs(self) -> None:
        hist_data = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.data_role
        )
        hist_row = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.row_role
        )
        hist_col = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.col_role
        )
        hist_hkey_id = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.id_role
        )
        hist_fpath = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.filepath_role
        )
        hist_name = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.name_role
        )
        hist_id = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.hist_id_role
        )
        hist_cate = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.cate_role
        )
        hist_ver = self._ihda_history_view.currentIndex().data(
            ihda_history_model.HistoryModel.version_role
        )
        self._selection.history.data = hist_data
        self._selection.history.row = hist_row
        self._selection.history.id = hist_hkey_id
        self._selection.history.filepath = hist_fpath
        self._selection.history.name = hist_name
        self._selection.history.hist_id = hist_id
        self._selection.history.cate = hist_cate
        self._selection.history.version = hist_ver

    def _refresh_current_attribs(self) -> None:
        if self._is_icon_mode:
            row = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.row_role
            )
            column = 0
            # hda_data = self._ihda_list_model.items[row]
            hda_data = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.data_role
            )
            hda_id = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.id_role
            )
            hda_filepath = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.filepath_role
            )
            hda_name = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.name_role
            )
            hda_cate = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.cate_role
            )
            hda_ver = self._ihda_list_view.currentIndex().data(
                ihda_list_model.ListModel.version_role
            )
        else:
            row = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.row_role
            )
            column = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.col_role
            )
            # hda_data = self._ihda_table_model.items[row]
            hda_data = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.data_role
            )
            hda_id = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.id_role
            )
            hda_filepath = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.filepath_role
            )
            hda_name = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.name_role
            )
            hda_cate = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.cate_role
            )
            hda_ver = self._ihda_table_view.currentIndex().data(
                ihda_table_model.TableModel.version_role
            )
        self._selection.asset.data = hda_data
        self._selection.asset.row = row
        self._selection.asset.id = hda_id
        self._selection.asset.filepath = hda_filepath
        self._selection.asset.name = hda_name
        self._selection.asset.cate = hda_cate
        self._selection.asset.version = hda_ver

    def _initialize_hist_current_attribs(self) -> None:
        self._selection.clear_history()

    def _initialize_current_attribs(self) -> None:
        self._selection.clear_asset()

    def _slot_record_only_curt_filter(self, *args: Any) -> None:
        if self.checkBox__record_only_current_hipfile.isChecked():
            hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        else:
            hip_filepath = None
        if self.checkBox__record_only_current_ihda.isChecked():
            hda_id = self._selection.asset.id
        else:
            hda_id = None
        self._ihda_record_proxy_model.set_filter_attribute(
            hda_id=hda_id, hip_filepath=hip_filepath
        )
        self._ihda_record_view.expandAll()
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )

    def _slot_inside_only_curt_filter(self, *args: Any) -> None:
        is_checked = self.checkBox__hda_inside_connect_to_view.isChecked()
        self.comboBox__hda_inside_node.setDisabled(is_checked)
        if is_checked:
            self.lineEdit__search_found_hda_inside_node.clear()
            hda_id = self._selection.asset.id
            self._ihda_inside_proxy_model.set_filter_attribute(hda_id=hda_id)
            self.label__found_hda_inside_hipfile_count.setText(
                str(self._ihda_inside_proxy_model.get_row_count())
            )
            self._ihda_inside_view.expandAll()
        else:
            self._slot_search_inside_node_combobox(
                self.comboBox__hda_inside_node.currentIndex()
            )

    @public.runtime_check_simple_with_param("iHDA node search")
    def _slot_refresh_inside_nodes(self) -> None:
        if not public.IS_HOUDINI:
            return
        root_node = hou.node("/")
        node_data = houdini_api.HoudiniAPI.get_ihda_node_instance_data(
            parent_node=root_node
        )
        if not len(node_data):
            node_data = dict()
            log_handler.LogHandler.log_msg(
                method=logging.debug, msg="iHDA node not found in current HIP file"
            )
        self._ihda_inside_model.make_node_tree(node_data=node_data)
        self._ihda_inside_view.expandAll()
        self.label__found_hda_inside_hipfile_count.setText(
            str(self._ihda_inside_proxy_model.get_row_count())
        )
        # inside node combobox 셋팅
        self._init_set_inside_ihda_combobox()
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="iHDA node search in the current HIP file has been updated",
        )

    def _slot_thumbnails(self) -> None:
        if self._is_show_thumbnail:
            thumb_icon = "ic_photo_white.png"
            self._ihda_list_model.show_thumbnail = True
            self._ihda_table_model.show_thumbnail = True
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="turn on thumbnail image"
            )
        else:
            thumb_icon = "network_sop.png"
            self._ihda_list_model.show_thumbnail = False
            self._ihda_table_model.show_thumbnail = False
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="turn off thumbnail image"
            )
        self.pushButton__thumbnail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/main/icons/{thumb_icon}"))
        )
        self._set_view_item_icon_size(self.doubleSpinBox__zoom.value())

    @staticmethod
    def _go_to_houdini_node(node_path: str | None = None) -> None:
        if not public.IS_HOUDINI:
            return
        if node_path is None:
            return
        node = hou.node(node_path)
        if node is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg=f'path "{node_path}" does not exist',
            )
            return
        if houdini_api.HoudiniAPI.is_root_network(node):
            return
        houdini_api.HoudiniAPI.go_to_node(node=node)
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f"{node_path} moved to path"
        )

    @QtCore.Slot(QtCore.QModelIndex)
    def _slot_on_hda_item_clicked(self, *args: Any) -> None:
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, list) or isinstance(model_idx, tuple):
            model_idx = model_idx[0]
        if not isinstance(model_idx, QtCore.QModelIndex):
            return
        self._selected_ihda_item(index=model_idx)

    def _play_video_most_recent_by_version(self, video_info: Any = None) -> None:
        video_filepath = video_info[0] / video_info[1]
        if not video_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="the video file has been renamed or has no video file",
            )
            return
        self._slot_select_view(index=self._video_view_idx)
        self._video_player.play_after_add_playlist(filepath_lst=[video_filepath])

    @QtCore.Slot(QtCore.QModelIndex)
    def _slot_hda_record_double_clicked(self, *args: Any) -> None:
        index = args[0]
        if not self._preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="ffmpeg is not installed"
            )
            return
        if not index.isValid():
            return
        record_data = index.data(ihda_record_model.RecordModel.record_data_role)
        if record_data is None:
            return
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        hda_id = index.data(ihda_record_model.RecordModel.hda_id_role)
        hda_name = index.data(ihda_record_model.RecordModel.name_role)
        hda_ver = record_data.get(public.Key.Record.node_ver)
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

    @QtCore.Slot(QtCore.QModelIndex)
    def _slot_hda_inside_double_clicked(self, *args: Any) -> None:
        index = args[0]
        if not index.isValid():
            return
        item_type = index.data(ihda_inside_model.InsideModel.node_type_role)
        if item_type != public.Type.ihda:
            return
        node_path = index.data(ihda_inside_model.InsideModel.node_path_role)
        self._go_to_houdini_node(node_path=node_path)

    @QtCore.Slot(QtCore.QModelIndex)
    def _slot_hda_double_clicked(self, *args: Any) -> None:
        index = args[0]
        if not self._preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="ffmpeg is not installed"
            )
            return
        if not index.isValid():
            return
        # self._selected_ihda_item(index=index)
        if self._is_ihda_history_view:
            video_dirpath = self._selection.history.data.get(
                public.Key.History.video_dirpath
            )
            ihda_ver = self._selection.history.data.get(public.Key.History.version)
            hist_id = self._selection.history.data.get(public.Key.History.hist_id)
            if video_dirpath is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'id: {hist_id} "{self._selection.history.name} [{ihda_ver}]" iHDA node has no video',
                )
                return
            video_filename = self._selection.history.data.get(
                public.Key.History.video_filename
            )
            video_filepath = video_dirpath / video_filename
        else:
            video_dirpath = self._selection.asset.data.get(public.Key.video_dirpath)
            if video_dirpath is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'"{self._selection.asset.name}" iHDA node has no video',
                )
                return
            video_filename = self._selection.asset.data.get(public.Key.video_filename)
            video_filepath = video_dirpath / video_filename
        if not video_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="the video file has been renamed or has no video file",
            )
            return
        self._slot_select_view(index=self._video_view_idx)
        self._video_player.play_after_add_playlist(filepath_lst=[video_filepath])

    def _selected_ihda_item(self, index: QtCore.QModelIndex = None) -> None:
        if not index.isValid():
            return
        if self._is_ihda_history_view:
            self._selection.history.field = str(index.data())
            self._refresh_history_current_attribs()
            self._set_hda_hist_info_to_parms()
        else:
            self._selection.asset.field = str(index.data())
            self._refresh_current_attribs()
            self._set_hda_info_to_parms()
        # record view 갱신
        if self.checkBox__record_only_current_ihda.isChecked():
            self._slot_record_only_curt_filter()
        if self.checkBox__hda_inside_connect_to_view.isChecked():
            self._slot_inside_only_curt_filter()

    def _slot_selected_category(self, *args: Any) -> None:
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, list) or isinstance(model_idx, tuple):
            model_idx = model_idx[0]
        # 카테고리를 검색했을 때, 아무것도 검색이 안되면 column 속성이 없다는 에러 발생하여 예외처리 함.
        try:
            self._selection.column_idx = model_idx.column()
            index_item = self._ihda_category_proxy_model.mapToSource(model_idx)
            item_text = str(index_item.data()).strip()
            self._selection.item_text = item_text
            par_lst = self._get_all_category_parent_by_selected_item(index_item)
            self._selection.parents = par_lst
            # 어느 카테고리를 클릭했는지 로깅하는 것인데 비활성화함.
            # log_handler.LogHandler.log_msg(method=logging.info, msg=' > '.join(par_lst))
            node_cate = None if item_text == public.Type.root else item_text
            self._ihda_list_proxy_model.node_category = node_cate
            self._ihda_table_proxy_model.node_category = node_cate
            self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
            self.label__cate_count.setText(str(self._get_category_count()))
        except AttributeError:
            # log_handler.LogHandler.log_msg(method=logging.warning, msg='search results do not exist')
            pass

    def _slot_selected_record(self, *args: Any) -> None:
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, list) or isinstance(model_idx, tuple):
            model_idx = model_idx[0]

    def _slot_stackedwidget_hda_infos(self) -> None:
        if self.pushButton__hda_info.isChecked():
            self.stackedWidget__hda_infos.setCurrentIndex(0)
        elif self.pushButton__hda_loc_record.isChecked():
            self.stackedWidget__hda_infos.setCurrentIndex(1)
        elif self.pushButton__hda_inside_node_view.isChecked():
            self.stackedWidget__hda_infos.setCurrentIndex(2)
