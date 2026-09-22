"""Context menus for the Individual HDA panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

from libs import host, houdini_api, ihda_system, keys, log_handler
from libs.item_paths import item_path
from libs.ui_icons import Icon
from model import (
    ihda_history_model,
    ihda_inside_model,
    ihda_list_model,
    ihda_record_model,
    ihda_table_model,
)

if TYPE_CHECKING:
    from widgets.make_video_info.make_video_info import MakeVideoInfo
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.library_port import LibraryPort
    from widgets.panel.ports import (
        AssetManagementPort,
        AssetModelPort,
        CallbacksPort,
        LibraryQueryPort,
        LibraryToolsPort,
        MediaActionsPort,
        NotesPort,
        PresentationPort,
        SelectionPort,
    )
    from widgets.panel.state import PanelSessionState, PanelViews
    from widgets.rename_ihda.rename_ihda import RenameIHDA
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer


@dataclass(frozen=True, slots=True)
class PanelContextMenusBindings:
    host_enabled: bool
    callbacks: CallbacksPort
    management: AssetManagementPort
    media: MediaActionsPort
    models: AssetModelPort
    notes: NotesPort
    parent: QtWidgets.QWidget
    presentation: PresentationPort
    queries: LibraryQueryPort
    rename_dialog: RenameIHDA
    selection: SelectionPort
    session: PanelSessionState
    suggest: Callable[[], None]
    library: Callable[[], LibraryPort]
    tools: LibraryToolsPort
    ui: MainWindowLayout
    video_info: MakeVideoInfo
    video_player: VideoPlayer | UnavailableVideoPlayer
    views: PanelViews


class PanelContextMenus:
    bindings: PanelContextMenusBindings

    def _build_context_history_menu(self, point: QtCore.QPoint) -> None:
        if self.bindings.library().history_menu(point):
            return
        index = self.bindings.views.history.indexAt(point)
        if not index.isValid():
            return
        if not index.data(ihda_history_model.HistoryModel.data_role).is_version:
            return  # activity rows own no file to open, detail or delete
        if not self.bindings.queries.is_valid_hist_current_item_data:
            return
        context_menu = QtWidgets.QMenu(self.bindings.parent)
        open_context_menu = QtWidgets.QMenu("Open", self.bindings.parent)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
        )
        action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
        action_open_context_ihda_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
        )
        # hip folder
        action_open_context_hip_folder = open_context_menu.addAction("HIP Folder")
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
        )
        open_context_menu.addSeparator()
        # hip file
        action_open_context_hip_file = open_context_menu.addAction("HIP File")
        action_open_context_hip_file.setIcon(QtGui.QIcon(QtGui.QPixmap(Icon.HIPFILE)))
        action_context_menu_detail = context_menu.addAction("Detail")
        action_context_menu_detail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FORMAT_QUOTE_WHITE))
        )
        action_context_menu_remove = context_menu.addAction("Delete")
        action_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_DELETE_FOREVER_WHITE))
        )
        context_menu.addMenu(open_context_menu)
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_detail)
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_remove)
        # refresh current data
        self.bindings.selection.state.set_field(index.data(), history=True)
        self.bindings.selection.refresh_history_current_attribs()
        self.bindings.notes.set_hda_hist_info_to_parms()
        if self.bindings.selection.state.history.data is None:
            return
        hip_dirpath = self.bindings.selection.state.history.require_data().hip_dirpath
        action = context_menu.exec(self.bindings.views.history.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(
                dirpath=self.bindings.selection.state.history.filepath
            )
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            hip_filepath = item_path(
                hip_dirpath,
                self.bindings.selection.state.history.require_data().hip_filename,
            )
            self.bindings.presentation.open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_context_menu_detail:
            self.bindings.notes.detail_view_ihda_data(
                data=self.bindings.selection.state.history.data
            )
        elif action == action_context_menu_remove:
            self.bindings.management.remove_hist_item()
        else:
            pass

    def remove_selected_assets(self) -> None:
        """Move the selected assets to the Trash (context menu and the Delete key)."""
        if self.bindings.presentation.is_icon_mode:
            indexes = self.bindings.views.assets_list.selectedIndexes()
        else:
            # table 모델은 이렇게 해야한다. 왜냐면 cell 선택시 모든 cell을 선택되어지도록 했는데
            # 이것 때문에 중복 index가 생겨 첫번째 컬럼을 명확시 지정하였다.
            indexes = self.bindings.views.assets_table.selectionModel().selectedRows(0)
        if not len(indexes):
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="iHDA node is not selected"
            )
            return
        self.bindings.management.remove_hda_item(indexes=indexes)

    def _build_context_ihda_menu(self, point: QtCore.QPoint) -> None:
        if self.bindings.library().context_menu(point):
            return
        view = (
            self.bindings.views.assets_list
            if self.bindings.presentation.is_icon_mode
            else self.bindings.views.assets_table
        )
        index = view.indexAt(point)
        if not index.isValid():
            return
        if not self.bindings.queries.is_valid_current_hda_item_data:
            return
        context_menu = QtWidgets.QMenu(self.bindings.parent)
        open_context_menu = QtWidgets.QMenu("Open", self.bindings.parent)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
        )
        action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
        action_open_context_ihda_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
        )
        action_open_context_hip_folder = open_context_menu.addAction("HIP Folder")
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
        )
        open_context_menu.addSeparator()
        action_open_context_hip_file = open_context_menu.addAction("HIP File")
        action_open_context_hip_file.setIcon(QtGui.QIcon(QtGui.QPixmap(Icon.HIPFILE)))

        hda_context_menu = QtWidgets.QMenu("iHDA", self.bindings.parent)
        hda_context_menu.setIcon(QtGui.QIcon(QtGui.QPixmap(Icon.HOUDINI_LOGO_WHITE)))

        action_hda_context_menu_favorite = hda_context_menu.addAction("Favorite")
        favorite_icon = "ic_favorite_border_white.png"
        if self.bindings.selection.state.asset.require_data().is_favorite_hda:
            favorite_icon = "ic_favorite_white.png"
        action_hda_context_menu_favorite.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/main/icons/{favorite_icon}"))
        )

        action_hda_context_menu_copy = hda_context_menu.addAction("Copy to team…")
        action_hda_context_menu_copy.setIcon(QtGui.QIcon(QtGui.QPixmap(Icon.UPLOAD)))
        action_hda_context_menu_detail = hda_context_menu.addAction("Detail")
        action_hda_context_menu_detail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FORMAT_QUOTE_WHITE))
        )
        action_hda_context_menu_ai = hda_context_menu.addAction("AI: Suggest Note/Tags")
        action_hda_context_menu_ai.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.NETWORK_INTELLIGENCE))
        )
        action_hda_make_context_menu_rename = hda_context_menu.addAction("Rename")
        action_hda_make_context_menu_rename.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_BORDER_COLOR_WHITE))
        )
        hda_context_menu.addSeparator()
        hda_make_context_menu = QtWidgets.QMenu("Make", self.bindings.parent)
        hda_make_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_camera_white.png"))
        )
        action_hda_make_context_menu_thumbnail = hda_make_context_menu.addAction(
            "Thumbnail"
        )
        action_hda_make_context_menu_thumbnail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_CAMERA_ALT_WHITE))
        )
        action_hda_make_context_menu_video = hda_make_context_menu.addAction("Video")
        action_hda_make_context_menu_video.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_VIDEOCAM_WHITE))
        )
        for host_action in (
            action_hda_make_context_menu_thumbnail,
            action_hda_make_context_menu_video,
            action_hda_make_context_menu_rename,
        ):
            host_action.setEnabled(self.bindings.host_enabled)
            if not self.bindings.host_enabled:
                host_action.setToolTip(
                    "This action requires a running Houdini session."
                )
        hda_context_menu.addMenu(hda_make_context_menu)
        hda_context_menu.addSeparator()
        action_hda_context_menu_remove = hda_context_menu.addAction("Delete")
        action_hda_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_DELETE_FOREVER_WHITE))
        )
        # History
        hist_context_menu = QtWidgets.QMenu("History", self.bindings.parent)
        hist_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_QUERY_BUILDER_WHITE))
        )
        # history actions
        action_hist_context_menu_ihda_history = hist_context_menu.addAction("iHDA")
        action_hist_context_menu_ihda_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FIND_IN_PAGE_WHITE))
        )
        action_hist_context_menu_note_history = hist_context_menu.addAction("Note")
        action_hist_context_menu_note_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_assignment_white.png"))
        )
        hist_context_menu.addSeparator()
        action_hist_context_menu_remove_history = hist_context_menu.addAction("Delete")
        action_hist_context_menu_remove_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_DELETE_FOREVER_WHITE))
        )
        context_menu.addMenu(open_context_menu)
        context_menu.addMenu(hda_context_menu)
        context_menu.addMenu(hist_context_menu)
        context_menu.addSeparator()
        # refresh current data
        self.bindings.selection.state.set_field(index.data())
        self.bindings.selection.refresh_current_attribs()
        self.bindings.notes.set_hda_info_to_parms()

        if self.bindings.selection.state.asset.data is None:
            return
        hip_dirpath = self.bindings.selection.state.asset.require_data().hip_dirpath
        action = context_menu.exec(view.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(
                dirpath=self.bindings.selection.state.asset.filepath
            )
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            hip_filepath = item_path(
                hip_dirpath,
                self.bindings.selection.state.asset.require_data().hip_filename,
            )
            self.bindings.presentation.open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_hda_context_menu_copy:
            self.bindings.tools.open_copy_to_team()
        elif action == action_hda_context_menu_favorite:
            self.bindings.management.hda_favorite()
        elif action == action_hda_context_menu_detail:
            self.bindings.notes.detail_view_ihda_data(
                data=self.bindings.selection.state.asset.data
            )
        elif action == action_hda_context_menu_ai:
            self.bindings.suggest()
        elif action == action_hda_make_context_menu_thumbnail:
            self.bindings.callbacks.wrapper_execute_deferred(
                self.bindings.media.slot_make_thumbnail
            )
        elif action == action_hda_make_context_menu_video:
            if host.IS_HOUDINI:
                frinfo = houdini_api.HoudiniAPI.frame_info()
                self.bindings.video_info.sf = frinfo[0]
                self.bindings.video_info.ef = frinfo[1]
                self.bindings.video_info.fps = frinfo[2]
            self.bindings.video_info.show()
        elif action == action_hda_make_context_menu_rename:
            self.bindings.rename_dialog.clear_parms()
            self.bindings.rename_dialog.set_old_ihda_name(
                self.bindings.selection.state.asset.name or ""
            )
            self.bindings.rename_dialog.show()
        elif action == action_hda_context_menu_remove:
            self.remove_selected_assets()
        elif action == action_hist_context_menu_ihda_history:
            hda_name = self.bindings.selection.state.asset.name or ""
            hda_id = self.bindings.selection.state.asset.require_data().hda_id
            if not self.bindings.session.require_repository().has_history(hda_id):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'node history of "{hda_name}" iHDA node does not exist',
                )
                return
            self.bindings.selection.slot_select_view(
                index=self.bindings.ui.stackedWidget__whole.indexOf(
                    self.bindings.ui.page__history
                )
            )
            self.bindings.selection.select_hist_ihda_combobox_item(hkey_id=hda_id)
        elif action == action_hist_context_menu_note_history:
            hda_name = self.bindings.selection.state.asset.name or ""
            hda_id = self.bindings.selection.state.asset.require_data().hda_id
            hist_note_data = self.bindings.session.require_repository().note_history(
                hda_id
            )
            self.bindings.notes.slot_hda_note_history(
                hist_note_data=hist_note_data, hda_name=hda_name
            )
        elif action == action_hist_context_menu_remove_history:
            if self.bindings.presentation.is_icon_mode:
                indexes = self.bindings.views.assets_list.selectedIndexes()
            else:
                # table 모델은 이렇게 해야한다. 왜냐면 cell 선택시 모든 cell을 선택되어지도록 했는데
                # 이것 때문에 중복 index가 생겨 첫번째 컬럼을 명확시 지정하였다.
                indexes = (
                    self.bindings.views.assets_table.selectionModel().selectedRows(0)
                )
            if not len(indexes):
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="iHDA node is not selected"
                )
                return
            # player가 재생중이거나 일시정지 상태면 정지
            self.bindings.video_player.player_stop()
            del_hist_data_lst = []
            for index in sorted(indexes, key=lambda x: x.row(), reverse=True):
                if not index.isValid():
                    continue
                if self.bindings.presentation.is_icon_mode:
                    hda_id = index.data(ihda_list_model.ListModel.id_role)
                    hda_name = index.data(ihda_list_model.ListModel.name_role)
                else:
                    hda_id = index.data(ihda_table_model.TableModel.id_role)
                    hda_name = index.data(ihda_table_model.TableModel.name_role)
                if not self.bindings.session.require_repository().has_history(hda_id):
                    log_handler.LogHandler.log_msg(
                        method=logging.warning,
                        msg=f'node history of "{hda_name}" iHDA node does not exist',
                    )
                    continue
                # 삭제할 히스토리 데이터 수거
                hist_data_lst = self.bindings.models.history_model.get_hist_data_by_hkey_id_from_model(
                    hkey_id=hda_id
                )
                del_hist_data_lst.extend(hist_data_lst)
            self.bindings.management.trash_history_rows(del_hist_data_lst)
        else:
            pass

    def _build_context_category_menu(self, point: QtCore.QPoint) -> None:
        index = self.bindings.views.category.indexAt(point)
        if not index.isValid():
            return

    def _build_context_record_menu(self, point: QtCore.QPoint) -> None:
        index = self.bindings.views.record.indexAt(point)
        if not index.isValid():
            return
        item_type = index.data(ihda_record_model.RecordModel.record_type_role)
        if item_type == keys.Type.root:
            return
        hip_dirpath = index.data(ihda_record_model.RecordModel.hip_dirpath_role)
        hip_filepath = index.data(ihda_record_model.RecordModel.hip_filepath_role)
        hda_filepath = index.data(ihda_record_model.RecordModel.hda_filepath_role)
        record_data = index.data(ihda_record_model.RecordModel.record_data_role)
        pnode_path = index.data(ihda_record_model.RecordModel.pnode_path_role)
        context_menu = QtWidgets.QMenu(self.bindings.parent)
        open_context_menu = QtWidgets.QMenu("Open", self.bindings.parent)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
        )
        # hip folder
        action_open_context_hip_folder = open_context_menu.addAction("HIP Folder")
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
        )
        # hip file
        action_open_context_hip_file = None
        if hip_filepath is not None:
            action_open_context_hip_file = open_context_menu.addAction("HIP File")
            action_open_context_hip_file.setIcon(
                QtGui.QIcon(QtGui.QPixmap(Icon.HIPFILE))
            )
            open_context_menu.addSeparator()
        # iHDA folder
        action_open_context_ihda_folder = None
        if hda_filepath is not None:
            action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
            action_open_context_ihda_folder.setIcon(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
            )
        context_menu.addMenu(open_context_menu)
        context_menu.addSeparator()
        action_context_menu_go_to_network = None
        if pnode_path is not None:
            action_context_menu_go_to_network = context_menu.addAction("Go To Network")
            action_context_menu_go_to_network.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_flight_takeoff_white.png"))
            )
        action_context_menu_detail = None
        if record_data is not None:
            action_context_menu_detail = context_menu.addAction("Detail")
            action_context_menu_detail.setIcon(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_FORMAT_QUOTE_WHITE))
            )
        context_menu.addSeparator()
        action_context_menu_remove = context_menu.addAction("Delete")
        action_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(Icon.IC_DELETE_FOREVER_WHITE))
        )
        action = context_menu.exec(self.bindings.views.record.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hda_filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            self.bindings.presentation.open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_context_menu_go_to_network:
            self.bindings.selection.go_to_houdini_node(node_path=pnode_path)
        elif action == action_context_menu_detail:
            record_id = index.data(ihda_record_model.RecordModel.record_id_role)
            if record_id is None:
                return
            record_data = self.bindings.session.require_repository().record_detail(
                record_id
            )
            self.bindings.notes.detail_view_record_data(record_data=record_data)
        elif action == action_context_menu_remove:
            self.bindings.management.remove_selected_record_item(index=index)
        else:
            pass

    def _build_context_inside_menu(self, point: QtCore.QPoint) -> None:
        index = self.bindings.views.inside.indexAt(point)
        if not index.isValid():
            return
        item_type = index.data(ihda_inside_model.InsideModel.node_type_role)
        if item_type == keys.Type.root:
            return
        is_ihda_node = bool(item_type == keys.Type.ihda)
        hda_id = index.data(ihda_inside_model.InsideModel.hda_id_role)
        context_menu = QtWidgets.QMenu(self.bindings.parent)
        # go to node
        action_context_menu_go_to_node = context_menu.addAction("Go To Node")
        action_context_menu_go_to_node.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_flight_takeoff_white.png"))
        )
        context_menu.addAction(action_context_menu_go_to_node)
        context_menu.addSeparator()
        action_open_context_ihda_folder = None
        action_open_context_ihda_video = None
        if is_ihda_node:
            open_context_menu = QtWidgets.QMenu("Open", self.bindings.parent)
            open_context_menu.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_donut_large_white.png"))
            )
            # iHDA folder
            action_open_context_ihda_folder = open_context_menu.addAction("iHDA Folder")
            action_open_context_ihda_folder.setIcon(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_FOLDER_WHITE))
            )
            open_context_menu.addSeparator()
            # iHDA video
            action_open_context_ihda_video = open_context_menu.addAction("iHDA Video")
            action_open_context_ihda_video.setIcon(
                QtGui.QIcon(QtGui.QPixmap(Icon.IC_MOVIE_WHITE))
            )
            context_menu.addMenu(open_context_menu)
            context_menu.addSeparator()
        action = context_menu.exec(self.bindings.views.inside.mapToGlobal(point))
        if action == action_open_context_ihda_folder:
            if hda_id is None:
                return
            hda_fpath = self.bindings.session.require_repository().asset_filepath(
                hda_id
            )
            ihda_system.IHDASystem.open_folder(dirpath=hda_fpath)
        elif action == action_open_context_ihda_video:
            if hda_id is None:
                return
            hda_ver = index.data(ihda_inside_model.InsideModel.version_role)
            hda_name = index.data(ihda_inside_model.InsideModel.hda_org_name_role)
            video_info = self.bindings.session.require_repository().latest_video(
                hda_id, hda_ver
            )
            if video_info is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'"{hda_name} (v{hda_ver})" iHDA node has no video',
                )
                return
            self.bindings.selection.play_video_most_recent_by_version(
                video_info=video_info
            )
        elif action == action_context_menu_go_to_node:
            node_path = index.data(ihda_inside_model.InsideModel.node_path_role)
            self.bindings.selection.go_to_houdini_node(node_path=node_path)
        else:
            pass
