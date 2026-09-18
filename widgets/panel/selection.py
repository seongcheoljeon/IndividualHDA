"""Selection for the Houdini panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from operator import itemgetter
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs import host, houdini_api, keys, log_handler
from libs.domain import SelectionState
from libs.item_paths import item_path
from model import (
    ihda_history_model,
    ihda_inside_model,
    ihda_list_model,
    ihda_record_model,
    ihda_table_model,
)
from widgets.history.presenter import HistoryPresenter
from widgets.panel.selection_presenter import PanelSelectionPresenter
from widgets.ui_tokens import ASSET_COMBO_ICON_SIZE

if TYPE_CHECKING:
    from libs.ihda_icons import IHDAIcons
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.library_queries import PanelLibraryQueries
    from widgets.panel.model_binding import PanelModelBinding
    from widgets.panel.notes import PanelNotes
    from widgets.panel.presentation import PanelPresentation
    from widgets.panel.state import PanelSessionState, PanelViews
    from widgets.preference.preference import Preference
    from widgets.team_library.integration import MainLibraryIntegration
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer


@dataclass(frozen=True, slots=True)
class PanelSelectionBindings:
    icons: IHDAIcons
    models: PanelModelBinding
    notes: PanelNotes
    preference: Preference
    presentation: PanelPresentation
    queries: PanelLibraryQueries
    session: PanelSessionState
    team: Callable[[], MainLibraryIntegration]
    ui: MainWindowLayout
    video_player: VideoPlayer | UnavailableVideoPlayer
    views: PanelViews


class PanelSelection:
    bindings: PanelSelectionBindings

    def __init__(self) -> None:
        self.state = SelectionState()
        self.presenter = PanelSelectionPresenter(self.state, self)

    def _init_set_first_ihda_item(self) -> None:
        # 처음 시작 시, 첫 번째 노드가 선택되어지도록
        self.bindings.views.assets_list.setCurrentIndex(
            self.bindings.models.list_proxy_model.index(0, 0, QtCore.QModelIndex())
        )
        self.bindings.views.assets_table.setCurrentIndex(
            self.bindings.models.table_proxy_model.index(0, 0, QtCore.QModelIndex())
        )
        self._slot_on_hda_item_clicked(
            self.bindings.models.list_proxy_model.index(0, 0, QtCore.QModelIndex())
        )

    def _init_select_ihda_category_model(self) -> None:
        idx = self.bindings.models.category_proxy_model.index(
            0, 0, QtCore.QModelIndex()
        )
        self.bindings.views.category.setCurrentIndex(idx)
        self._slot_selected_category(idx)

    def _init_set_hist_ihda_combobox(self) -> None:
        if self.bindings.session.repository is None:
            return
        self._default_set_hist_ihda_combobox()
        for asset in self.bindings.session.require_repository().asset_names(
            self.bindings.session.user
        ):
            if not self.bindings.session.require_repository().has_history(
                asset.asset_id
            ):
                continue
            self._set_hist_ihda_to_combobox(hkey_id=asset.asset_id, hda_name=asset.name)

    def _default_set_hist_ihda_combobox(self) -> None:
        self.bindings.ui.comboBox__hist_ihda_node.clear()
        root_icon = QtGui.QIcon(
            self.bindings.icons.pixmap_cate_data.get(
                keys.Name.Icons.root, QtGui.QPixmap()
            ).scaled(ASSET_COMBO_ICON_SIZE, ASSET_COMBO_ICON_SIZE)
        )
        self.bindings.ui.comboBox__hist_ihda_node.addItem(root_icon, "ALL", -1)
        self.bindings.ui.comboBox__hist_ihda_node.setCurrentIndex(0)

    def _init_set_inside_ihda_combobox(self) -> None:
        self._default_set_inside_ihda_combobox()
        ihda_node_lst = self.bindings.models.inside_model.get_ihda_node_list()
        if not len(ihda_node_lst):
            return
        for node_info in sorted(ihda_node_lst, key=itemgetter(0)):
            node_name, hda_id, node_path = node_info
            self._set_inside_ihda_to_combobox(
                hkey_id=hda_id, hda_name=node_name, node_path=node_path
            )

    def _default_set_inside_ihda_combobox(self) -> None:
        self.bindings.ui.comboBox__hda_inside_node.clear()
        root_icon = QtGui.QIcon(
            self.bindings.icons.pixmap_cate_data.get(
                keys.Name.Icons.root, QtGui.QPixmap()
            ).scaled(ASSET_COMBO_ICON_SIZE, ASSET_COMBO_ICON_SIZE)
        )
        self.bindings.ui.comboBox__hda_inside_node.addItem(root_icon, "ALL", -1)
        self.bindings.ui.comboBox__hda_inside_node.setCurrentIndex(0)

    def _set_hist_ihda_to_combobox(
        self, hkey_id: int | None = None, hda_name: str | None = None
    ) -> None:
        if (
            hkey_id is not None
            and hkey_id not in self._get_all_hist_ihda_combobox_data()
        ):
            icon = QtGui.QIcon(
                self.bindings.icons.pixmap_ihda_data.get(
                    hkey_id, QtGui.QPixmap()
                ).scaled(ASSET_COMBO_ICON_SIZE, ASSET_COMBO_ICON_SIZE)
            )
            self.bindings.ui.comboBox__hist_ihda_node.addItem(
                icon, hda_name or "", hkey_id
            )

    def _set_inside_ihda_to_combobox(
        self,
        hkey_id: int | None = None,
        hda_name: str | None = None,
        node_path: str | None = None,
    ) -> None:
        pixmap = (
            self.bindings.icons.pixmap_ihda_data.get(hkey_id)
            if hkey_id is not None
            else None
        )
        # 만약 iHDA 노드를 삭제해서 pixmap 데이터가 존재하지 않는다면 직접 후디니 icon을 가공하여 가져온다.
        if pixmap is None:
            node = houdini_api.HoudiniAPI.find_node(node_path)
            if node is None:
                icon_lst = None
            else:
                icon_lst = houdini_api.HoudiniAPI.node_icon_path_lst(node)
            pixmap = self.bindings.icons.get_houdini_icon(icon_lst=icon_lst)
        icon = QtGui.QIcon(pixmap.scaled(ASSET_COMBO_ICON_SIZE, ASSET_COMBO_ICON_SIZE))
        self.bindings.ui.comboBox__hda_inside_node.addItem(
            icon, hda_name or "", hkey_id
        )

    def _get_all_hist_ihda_combobox_data(self) -> list[Any]:
        return [
            int(self.bindings.ui.comboBox__hist_ihda_node.itemData(i))
            for i in range(self.bindings.ui.comboBox__hist_ihda_node.count())
        ]

    def _select_hist_ihda_combobox_item(self, hkey_id: int | None = None) -> None:
        find_idx = self._find_hist_ihda_combobox_index(hkey_id=hkey_id)
        if find_idx is not None:
            self.bindings.ui.comboBox__hist_ihda_node.setCurrentIndex(find_idx)

    def _find_hist_ihda_combobox_index(self, hkey_id: int | None = None) -> int | None:
        find_idx = None
        for idx in range(self.bindings.ui.comboBox__hist_ihda_node.count()):
            cm_item_hkey_id = int(
                self.bindings.ui.comboBox__hist_ihda_node.itemData(idx)
            )
            if hkey_id == cm_item_hkey_id:
                find_idx = idx
                break
        return find_idx

    def _slot_select_view(self, inst: Any = None, index: int | None = None) -> None:
        pages = {
            self.bindings.ui.actioniHDA: self.bindings.ui.page__ihda,
            self.bindings.ui.actionVideo_Player: self.bindings.ui.page__video_player,
            self.bindings.ui.actionWeb: self.bindings.ui.page__web_view,
            self.bindings.ui.actionHistory: self.bindings.ui.page__history,
        }
        if index is not None:
            page = self.bindings.ui.stackedWidget__whole.widget(index)
            inst = next(
                (action for action, target in pages.items() if target is page), None
            )
        if inst not in pages:
            return
        for action in pages:
            action.setChecked(action is inst)
        page = pages[inst]
        self.bindings.ui.stackedWidget__whole.setCurrentWidget(page)
        if page is self.bindings.ui.page__history:
            self.bindings.session.actions.history()

    def _slot_set_view_mode(self) -> None:
        layout = (
            self.bindings.ui.verticalLayout__listview
            if self.bindings.presentation._is_icon_mode
            else self.bindings.ui.verticalLayout__tableview
        )
        page = layout.parentWidget()
        if page is not None:
            self.bindings.ui.stackedWidget__hda.setCurrentWidget(page)

    @QtCore.Slot(bool)
    def _slot_checkbox_hda_cate_casesensitive(self, idx: bool) -> None:
        self.bindings.models._search_filter_regexp_hda_cate(
            self.bindings.ui.lineEdit__search_cate.text().strip()
        )

    @QtCore.Slot(bool)
    def _slot_checkbox_hist_hda_item_casesensitive(self, idx: bool) -> None:
        self.bindings.models._search_filter_regexp_hist_hda_item(
            self.bindings.ui.lineEdit__search_hda_hist.text().strip()
        )

    @QtCore.Slot(int)
    def _slot_set_search_hist_field_target(self, idx: int) -> None:
        self.bindings.models.history_proxy_model.set_search_field(
            self.bindings.ui.comboBox__search_field_hist.itemText(idx)
        )

    @QtCore.Slot(bool)
    def _slot_chk_hist_search_data(self, state: bool) -> None:
        self.bindings.ui.dateEdit__hist_search_start.setEnabled(state)
        self.bindings.ui.dateEdit__hist_search_end.setEnabled(state)
        self.bindings.ui.label__join_str.setEnabled(state)
        self._slot_hist_ihda_search_date()

    @QtCore.Slot(int)
    def _slot_hist_ihda_combobox(self, idx: int) -> None:
        self.bindings.ui.lineEdit__search_hda_hist.clear()
        hda_id = self.bindings.ui.comboBox__hist_ihda_node.itemData(idx)
        self.bindings.models.history_proxy_model.set_hda_id(hda_id=hda_id)
        self.bindings.ui.label__hist_cnt.setText(
            str(self.bindings.models.history_proxy_model.rowCount())
        )

    @QtCore.Slot(int)
    def _slot_search_inside_node_combobox(self, idx: int) -> None:
        hda_id = self.bindings.ui.comboBox__hda_inside_node.itemData(idx)
        self.bindings.models.inside_proxy_model.set_filter_attribute(hda_id=hda_id)
        self.bindings.ui.label__found_hda_inside_hipfile_count.setText(
            str(self.bindings.models.inside_proxy_model.get_row_count())
        )
        self.bindings.views.inside.expandAll()

    def _slot_hist_ihda_search_date(self, *args: Any) -> None:
        HistoryPresenter(self).filter_dates(
            self.bindings.ui.checkBox__hist_search_date.isChecked(),
            date.fromisoformat(
                self.bindings.ui.dateEdit__hist_search_start.date().toString(
                    "yyyy-MM-dd"
                )
            ),
            date.fromisoformat(
                self.bindings.ui.dateEdit__hist_search_end.date().toString("yyyy-MM-dd")
            ),
        )

    def show_history_error(self, message: str) -> None:
        log_handler.LogHandler.log_msg(method=logging.warning, msg=message)

    def show_history_dates(self, dates: list[str]) -> None:
        self.bindings.models.history_proxy_model.set_datetime(datetime_lst=dates)
        self.bindings.ui.label__hist_cnt.setText(
            str(self.bindings.models.history_proxy_model.rowCount())
        )

    def _select_category(self, category: str | None = None) -> None:
        root_idx = self.bindings.models.category_proxy_model.index(
            0, 0, QtCore.QModelIndex()
        )
        find_idx = self.bindings.queries._find_tree_element_model(
            index=root_idx, find_name=category or ""
        )
        if find_idx is None:
            return
        self.bindings.views.category.setCurrentIndex(find_idx)

    def _select_model_item_by_hda_id(self, hda_id: int | None = None) -> None:
        model_hda: QtCore.QAbstractProxyModel
        view_hda: QtWidgets.QAbstractItemView
        if self.bindings.presentation._is_ihda_history_view:
            # history가 존재하지 않으면
            if not self.bindings.models.history_model.is_exist_ihda_item_from_model(
                hkey_id=hda_id
            ):
                return
            self._select_hist_ihda_combobox_item(hkey_id=hda_id)
        else:
            if self.bindings.presentation._is_icon_mode:
                model_hda = self.bindings.models.list_proxy_model
                view_hda = self.bindings.views.assets_list
            else:
                model_hda = self.bindings.models.table_proxy_model
                view_hda = self.bindings.views.assets_table
            find_idx = self.bindings.queries._find_hda_id_by_model_item(
                model_hda=model_hda, find_hda_id=hda_id
            )
            if find_idx is None:
                return
            view_hda.setCurrentIndex(find_idx)
            self._slot_on_hda_item_clicked(find_idx)

    def _restore_panel_selection(self) -> None:
        for view, proxy in (
            (self.bindings.views.assets_list, self.bindings.models.list_proxy_model),
            (self.bindings.views.assets_table, self.bindings.models.table_proxy_model),
        ):
            row = self.state.asset.row
            index = (
                proxy.mapFromSource(proxy.sourceModel().index(row, 0))
                if row is not None
                else QtCore.QModelIndex()
            )
            view.setCurrentIndex(index)
        row = self.state.history.row
        history_proxy = self.bindings.models.history_proxy_model
        index = (
            history_proxy.mapFromSource(history_proxy.sourceModel().index(row, 0))
            if row is not None
            else QtCore.QModelIndex()
        )
        self.bindings.views.history.setCurrentIndex(index)
        category = self.state.item_text
        if category:
            self._select_category(category)

    def _refresh_history_current_attribs(self) -> None:
        index = self.bindings.views.history.currentIndex()
        self.state.select_history(
            index.data(ihda_history_model.HistoryModel.data_role),
            index.data(ihda_history_model.HistoryModel.row_role),
            str(index.data()) if index.isValid() else None,
        )

    def _refresh_current_attribs(self) -> None:
        view = (
            self.bindings.views.assets_list
            if self.bindings.presentation._is_icon_mode
            else self.bindings.views.assets_table
        )
        roles = (
            ihda_list_model.ListModel
            if self.bindings.presentation._is_icon_mode
            else ihda_table_model.TableModel
        )
        index = view.currentIndex()
        self.state.select_asset(
            index.data(roles.data_role),
            index.data(roles.row_role),
            str(index.data()) if index.isValid() else None,
        )

    def _initialize_hist_current_attribs(self) -> None:
        self.state.clear_history()

    def _initialize_current_attribs(self) -> None:
        self.state.clear_asset()

    def _slot_record_only_curt_filter(self, *args: Any) -> None:
        if self.bindings.ui.checkBox__record_only_current_hipfile.isChecked():
            hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        else:
            hip_filepath = None
        if self.bindings.ui.checkBox__record_only_current_ihda.isChecked():
            hda_id = self.state.asset.id
        else:
            hda_id = None
        self.bindings.models.record_proxy_model.set_filter_attribute(
            hda_id=hda_id, hip_filepath=hip_filepath
        )
        self.bindings.views.record.expandAll()
        self.bindings.ui.label__loc_record_count.setText(
            str(self.bindings.models.record_proxy_model.get_row_count())
        )

    def _slot_inside_only_curt_filter(self, *args: Any) -> None:
        is_checked = self.bindings.ui.checkBox__hda_inside_connect_to_view.isChecked()
        self.bindings.ui.comboBox__hda_inside_node.setDisabled(is_checked)
        if is_checked:
            self.bindings.ui.lineEdit__search_found_hda_inside_node.clear()
            hda_id = self.state.asset.id
            self.bindings.models.inside_proxy_model.set_filter_attribute(hda_id=hda_id)
            self.bindings.ui.label__found_hda_inside_hipfile_count.setText(
                str(self.bindings.models.inside_proxy_model.get_row_count())
            )
            self.bindings.views.inside.expandAll()
        else:
            self._slot_search_inside_node_combobox(
                self.bindings.ui.comboBox__hda_inside_node.currentIndex()
            )

    @log_handler.log_elapsed("iHDA node search")
    def _slot_refresh_inside_nodes(self) -> None:
        if not host.IS_HOUDINI:
            return
        root_node = houdini_api.HoudiniAPI.find_node("/")
        node_data = houdini_api.HoudiniAPI.get_ihda_node_instance_data(
            parent_node=root_node
        )
        if not len(node_data):
            node_data = {}
            log_handler.LogHandler.log_msg(
                method=logging.debug, msg="iHDA node not found in current HIP file"
            )
        self.bindings.models.inside_model.make_node_tree(node_data=node_data)
        self.bindings.views.inside.expandAll()
        self.bindings.ui.label__found_hda_inside_hipfile_count.setText(
            str(self.bindings.models.inside_proxy_model.get_row_count())
        )
        # inside node combobox 셋팅
        self._init_set_inside_ihda_combobox()
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="iHDA node search in the current HIP file has been updated",
        )

    def _slot_thumbnails(self) -> None:
        if self.bindings.presentation._is_show_thumbnail:
            thumb_icon = "ic_photo_white.png"
            self.bindings.models.list_model.show_thumbnail = True
            self.bindings.models.table_model.show_thumbnail = True
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="turn on thumbnail image"
            )
        else:
            thumb_icon = "network_sop.png"
            self.bindings.models.list_model.show_thumbnail = False
            self.bindings.models.table_model.show_thumbnail = False
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="turn off thumbnail image"
            )
        self.bindings.ui.pushButton__thumbnail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/main/icons/{thumb_icon}"))
        )
        self.bindings.presentation._set_view_item_icon_size(
            self.bindings.ui.doubleSpinBox__zoom.value()
        )

    @staticmethod
    def _go_to_houdini_node(node_path: str | None = None) -> None:
        if not host.IS_HOUDINI:
            return
        if node_path is None:
            return
        node = houdini_api.HoudiniAPI.find_node(node_path)
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
        if isinstance(model_idx, (list, tuple)):
            model_idx = model_idx[0]
        if not isinstance(model_idx, QtCore.QModelIndex):
            return
        self._selected_ihda_item(index=model_idx)

    def _play_video_most_recent_by_version(self, video_info: Any = None) -> None:
        video_filepath = video_info
        if video_filepath is None or not video_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="the video file has been renamed or has no video file",
            )
            return
        self._slot_select_view(
            index=self.bindings.ui.stackedWidget__whole.indexOf(
                self.bindings.ui.page__video_player
            )
        )
        self.bindings.video_player.play_after_add_playlist(
            filepath_lst=[video_filepath]
        )

    @QtCore.Slot(QtCore.QModelIndex)
    def _slot_hda_record_double_clicked(self, *args: Any) -> None:
        index = args[0]
        if index is None or not index.isValid():
            return
        record_data = index.data(ihda_record_model.RecordModel.record_data_role)
        if record_data is None:
            return
        hda_id = index.data(ihda_record_model.RecordModel.hda_id_role)
        hda_name = index.data(ihda_record_model.RecordModel.name_role)
        hda_ver = record_data.node_ver
        video_info = self.bindings.session.require_repository().latest_video(
            hda_id, hda_ver
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
        if index is None or not index.isValid():
            return
        item_type = index.data(ihda_inside_model.InsideModel.node_type_role)
        if item_type != keys.Type.ihda:
            return
        node_path = index.data(ihda_inside_model.InsideModel.node_path_role)
        self._go_to_houdini_node(node_path=node_path)

    @QtCore.Slot(QtCore.QModelIndex)
    def _slot_hda_double_clicked(self, *args: Any) -> None:
        team = self.bindings.team()
        if team is not None and team.active:
            team.actions.play_video()
            return
        index = args[0]
        if index is None or not index.isValid():
            return
        # self._selected_ihda_item(index=index)
        if self.bindings.presentation._is_ihda_history_view:
            video_dirpath = self.state.history.require_data().video_dirpath
            ihda_ver = self.state.history.require_data().version
            hist_id = self.state.history.require_data().hist_id
            if video_dirpath is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'id: {hist_id} "{self.state.history.name} [{ihda_ver}]" iHDA node has no video',
                )
                return
            video_filename = self.state.history.require_data().video_filename
            video_filepath = item_path(video_dirpath, video_filename)
        else:
            video_dirpath = self.state.asset.require_data().video_dirpath
            if video_dirpath is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'"{self.state.asset.name}" iHDA node has no video',
                )
                return
            video_filename = self.state.asset.require_data().video_filename
            video_filepath = item_path(video_dirpath, video_filename)
        if video_filepath is None or not video_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="the video file has been renamed or has no video file",
            )
            return
        self._slot_select_view(
            index=self.bindings.ui.stackedWidget__whole.indexOf(
                self.bindings.ui.page__video_player
            )
        )
        self.bindings.video_player.play_after_add_playlist(
            filepath_lst=[video_filepath]
        )

    def _selected_ihda_item(self, index: QtCore.QModelIndex | None = None) -> None:
        if index is None or not index.isValid():
            return
        if self.bindings.presentation._is_ihda_history_view:
            roles: (
                type[ihda_history_model.HistoryModel]
                | type[ihda_list_model.ListModel]
                | type[ihda_table_model.TableModel]
            ) = ihda_history_model.HistoryModel
            self.presenter.select_history(
                index.data(roles.data_role),
                index.data(roles.row_role),
                str(index.data()),
            )
        else:
            roles = (
                ihda_list_model.ListModel
                if self.bindings.presentation._is_icon_mode
                else ihda_table_model.TableModel
            )
            self.presenter.select_asset(
                index.data(roles.data_role),
                index.data(roles.row_role),
                str(index.data()),
            )

    def show_asset_selection(self) -> None:
        self.bindings.notes._set_hda_info_to_parms()

    def show_history_selection(self) -> None:
        self.bindings.notes._set_hda_hist_info_to_parms()

    def refresh_selection_dependents(self) -> None:
        # record view 갱신
        if self.bindings.ui.checkBox__record_only_current_ihda.isChecked():
            self._slot_record_only_curt_filter()
        if self.bindings.ui.checkBox__hda_inside_connect_to_view.isChecked():
            self._slot_inside_only_curt_filter()

    def _slot_selected_category(self, *args: Any) -> None:
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, (list, tuple)):
            model_idx = model_idx[0]
        # 카테고리를 검색했을 때, 아무것도 검색이 안되면 column 속성이 없다는 에러 발생하여 예외처리 함.
        try:
            index_item = self.bindings.models.category_proxy_model.mapToSource(
                model_idx
            )
            item_text = str(index_item.data()).strip()
            par_lst = self.bindings.queries._get_all_category_parent_by_selected_item(
                index_item
            )
            self.state.select_category(model_idx.column(), item_text, par_lst)
            # 어느 카테고리를 클릭했는지 로깅하는 것인데 비활성화함.
            # log_handler.LogHandler.log_msg(method=logging.info, msg=' > '.join(par_lst))
            node_cate = None if item_text == keys.Type.root else item_text
            self.bindings.models.list_proxy_model.node_category = node_cate
            self.bindings.models.table_proxy_model.node_category = node_cate
            self.bindings.ui.label__hda_count.setText(
                str(self.bindings.models.list_proxy_model.rowCount())
            )
            self.bindings.ui.label__cate_count.setText(
                str(self.bindings.models._get_category_count())
            )
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
        if isinstance(model_idx, (list, tuple)):
            model_idx = model_idx[0]

    def _slot_stackedwidget_hda_infos(self) -> None:
        if self.bindings.ui.pushButton__hda_info.isChecked():
            self.bindings.ui.stackedWidget__hda_infos.setCurrentWidget(
                self.bindings.ui.page__hda_info
            )
        elif self.bindings.ui.pushButton__hda_loc_record.isChecked():
            self.bindings.ui.stackedWidget__hda_infos.setCurrentWidget(
                self.bindings.ui.page__hda_loc_record
            )
        elif self.bindings.ui.pushButton__hda_inside_node_view.isChecked():
            self.bindings.ui.stackedWidget__hda_infos.setCurrentWidget(
                self.bindings.ui.page__hda_inside_hipfile
            )
