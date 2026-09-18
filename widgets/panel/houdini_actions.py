"""Houdini actions on the panel GUI thread.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
import pathlib
from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets

from libs import host, houdini_api, keys, log_handler, platform_info
from libs.asset_contracts import AssetData, HistoryData
from libs.drag_payload import DragRecord, decode_drag_record
from libs.record_codec import decode_record
from libs.repository import LibraryError
from libs.scene_contracts import SceneRecord, SceneRecordInput

if TYPE_CHECKING:
    import hou


from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from widgets.panel.asset_management import PanelAssetManagement
    from widgets.panel.host_callbacks import PanelHostCallbacks
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.library_queries import PanelLibraryQueries
    from widgets.panel.model_binding import PanelModelBinding
    from widgets.panel.presentation import PanelPresentation
    from widgets.panel.scene_usage import SceneUsageIntegration
    from widgets.panel.selection import PanelSelection
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState
    from widgets.team_library.integration import MainLibraryIntegration


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportedNode:
    node: hou.Node
    version_uuid: str | None


@dataclass(frozen=True, slots=True)
class PanelHoudiniActionsBindings:
    callbacks: PanelHostCallbacks
    management: PanelAssetManagement
    models: PanelModelBinding
    parent: QtWidgets.QWidget
    presentation: PanelPresentation
    queries: PanelLibraryQueries
    scene_usage: Callable[[], SceneUsageIntegration]
    selection: PanelSelection
    services: PanelServices
    session: PanelSessionState
    team: Callable[[], MainLibraryIntegration]
    ui: MainWindowLayout


class PanelHoudiniActions:
    bindings: PanelHoudiniActionsBindings

    @QtCore.Slot(object)
    def _slot_mouse_move_event_on_houdini(self, drop_data: Any) -> None:
        # [[id, name, category, filename, dirpath, icon_lst, tag_lst], [...], ...]
        if not self.bindings.services.host_actions_enabled:
            return
        team = self.bindings.team()
        if team is not None and team.active:
            team.actions.import_drop(drop_data)
            return
        if not host.IS_HOUDINI:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="please drag from houdini"
            )
            self.bindings.presentation._dragdrop_overlay_close()
            return
        drop_action, model_data_lst = drop_data
        assert isinstance(model_data_lst, list)
        if drop_action != QtCore.Qt.DropAction.IgnoreAction:
            self.bindings.presentation._dragdrop_overlay_close()
            return
        network_editor = houdini_api.HoudiniAPI.find_network_editor_by_cursor()
        if network_editor is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="houdini network not found"
            )
            self.bindings.presentation._dragdrop_overlay_close()
            return
        total_node_cnt = len(model_data_lst)
        if not total_node_cnt:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="imported iHDA data is empty"
            )
            self.bindings.presentation._dragdrop_overlay_close()
            return
        if total_node_cnt > self.bindings.services.policy.maximum_node_batch:
            msgbox = QtWidgets.QMessageBox(self.bindings.parent)
            msgbox.setFont(self.bindings.presentation._get_default_font())
            msgbox.setWindowTitle("Import iHDA Node")
            msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msgbox.setText("Too many nodes to import")
            msgbox.setDetailedText(
                f"""
            Please bring no more than {self.bindings.services.policy.maximum_node_batch} items.
            Total Nodes: {total_node_cnt}
            """
            )
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            _ = msgbox.exec()
            return
        if total_node_cnt > self.bindings.services.policy.warn_node_batch:
            msgbox = QtWidgets.QMessageBox(self.bindings.parent)
            msgbox.setFont(self.bindings.presentation._get_default_font())
            msgbox.setWindowTitle("Import iHDA Node")
            msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msgbox.setText(
                f"""
            The number of iHDA nodes you are trying to import exceeds {self.bindings.services.policy.warn_node_batch}.
            Should I bring it though?

            NOTE: Registering a large number of nodes at a time may make the Houdini appear to be stationary.
            But it didn't stop, so please wait a little longer.
            """
            )
            msgbox.setDetailedText(f"Total Nodes: {total_node_cnt}")
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
            )
            reply = msgbox.exec()
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="importing iHDA nodes was canceled"
                )
                self.bindings.presentation._dragdrop_overlay_close()
                return
        # 기존에 선택된 노드가 존재한다면 모두 선택 해제
        old_selected_nodes = houdini_api.HoudiniAPI.get_selected_nodes()
        if old_selected_nodes is not None:
            houdini_api.HoudiniAPI.all_clear_selected(node=old_selected_nodes[0])
        # node 위치 옵셋 값
        offset_pos = houdini_api.HoudiniAPI.vector2(1, -1)
        network_editor.setIsCurrentTab()
        cursor_pos = houdini_api.HoudiniAPI.get_cursor_pos(
            network_editor=network_editor
        )
        self.bindings.callbacks._wrapper_execute_deferred(
            lambda: self._create_ihda_node_in_houdini(
                model_data_lst=model_data_lst,
                network_editor=network_editor,
                cursor_pos=cursor_pos,
                offset_pos=offset_pos,
                total_node_cnt=total_node_cnt,
            )
        )

    def _create_ihda_node_in_houdini(
        self,
        model_data_lst: Any = None,
        network_editor: hou.NetworkEditor | None = None,
        cursor_pos: Any = None,
        offset_pos: Any = None,
        total_node_cnt: int | None = None,
    ) -> None:
        if network_editor is None:
            return
        repository = self.bindings.session.repository
        if repository is None:
            return
        num_count = 0
        for node_cnt, encoded_data in enumerate(model_data_lst):
            model_data = decode_drag_record(encoded_data)
            # record data 인지 확인하는 변수
            if isinstance(model_data, SceneRecord):
                record = self.bindings.session.require_repository().record_detail(
                    model_data.record_id
                )
                if record:
                    model_data = replace(model_data, version_uuid=record.version_uuid)
            # 만약 히스토리에서 드래그&드롭 하는 것이라면
            if isinstance(model_data, HistoryData):
                if not model_data.is_version:
                    continue  # activity rows carry no HDA file
                hda_cate = model_data.node_category
                hda_id = model_data.hda_id
                hda_name = model_data.org_hda_name
                hda_ver = model_data.version
                hda_dirpath = model_data.ihda_dirpath
                hda_filename = model_data.ihda_filename
                hda_license: str | None = model_data.hda_license
                hda_note = repository.import_note(hda_id, hda_ver)
                item_row = model_data.item_row
            else:
                # record data가 아니라면
                if isinstance(model_data, AssetData):
                    hda_cate = model_data.hda_cate
                    hda_id = model_data.hda_id
                    hda_name = model_data.hda_name
                    hda_ver = model_data.hda_version
                    hda_dirpath = model_data.hda_dirpath
                    hda_filename = model_data.hda_filename
                    hda_license = model_data.hda_license
                    hda_note = repository.import_note(hda_id)
                    item_row = model_data.item_row
                # record data라면
                else:
                    hda_cate = model_data.node_cate
                    hda_id = model_data.hda_id
                    hda_name = model_data.node_name
                    hda_ver = model_data.node_ver
                    hda_dirpath = model_data.hda_dirpath
                    hda_filename = model_data.hda_filename
                    # 라이센스는 hda data 의 것을 가져와야 함. 왜냐면, loc data의 라이센스는 ihda노드를 후디니로
                    # 내보낼때 그 당시의 후디니 라이센스이기 때문이다. 허나 hda 데이터나 hda history 데이터는
                    # 후디니 노드를 hda로 만들 때의 후디니 라이센스라서 hda도 논커머셜인지 커머셜인지 결정 됨.
                    hda_license = repository.import_license(
                        hda_id, hda_ver, self.bindings.session.user
                    )
                    hda_note = repository.import_note(hda_id, hda_ver)
                    item_row = self.bindings.queries._get_ihda_data_by_id(
                        hda_id=hda_id, key=keys.Key.item_row
                    )
            if not repository.asset_available(
                hda_id,
                model_data.hist_id if isinstance(model_data, HistoryData) else None,
            ):
                self.bindings.management.show_command_error(
                    "This asset or version is in Trash. Refresh the library."
                )
                continue
            if not isinstance(hda_dirpath, pathlib.Path) or not hda_filename:
                continue
            hda_filepath = hda_dirpath / hda_filename
            # DB에는 존재하지만 지정된 곳에 파일이 존재하지 않는다면
            if not hda_filepath.exists():
                log_handler.LogHandler.log_msg(
                    method=logging.critical,
                    msg=f'[{node_cnt + 1}/{total_node_cnt}] "{hda_name} (v{hda_ver})" iHDA file does not exist',
                )
                continue
            # item의 row (model에서 셋팅해 놓았음)
            if isinstance(model_data, HistoryData):
                self.bindings.selection.state.select_history(model_data, item_row)
            else:
                self.bindings.selection.state.select_asset(
                    (
                        self.bindings.queries._get_ihda_data_by_id(hda_id=hda_id)
                        if isinstance(model_data, SceneRecord)
                        else model_data
                    ),
                    item_row,
                )
            # 현재 Houdini 라이센스
            curt_houdini_license = houdini_api.HoudiniAPI.current_houdini_license()
            # 후디니는 commercial라이센스인데 iHDA는 아니라면
            if not self.bindings.management._ihda_license_check(
                hda_license=hda_license
            ):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'[{node_cnt + 1}/{total_node_cnt}] houdini license and "{hda_name} (v{hda_ver})" iHDA license are different',
                )
                msgbox = QtWidgets.QMessageBox(self.bindings.parent)
                msgbox.setFont(self.bindings.presentation._get_default_font())
                msgbox.setWindowTitle("Import iHDA Node")
                msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                msgbox.setText(
                    f"""
                [{node_cnt + 1}/{total_node_cnt}] Imported "{hda_name} (v{hda_ver})" iHDA are not commercial.
                When I import it into the current HIP file, the HIP file also becomes non-commercial.
                Should I bring it though?"""
                )
                msgbox.setDetailedText(
                    f"""
                Current HIP File License: {curt_houdini_license}
                Current iHDA Node License: {hda_license}
                """
                )
                # msgbox.resize(msgbox.sizeHint())
                msgbox.setStandardButtons(
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No
                )
                reply = msgbox.exec()
                if reply == QtWidgets.QMessageBox.StandardButton.No:
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg=f'[{node_cnt + 1}/{total_node_cnt}] importing "{hda_name} (v{hda_ver})" iHDA nodes was canceled',
                    )
                    continue
            if not self.bindings.callbacks._is_valid_network_category(
                network_editor=network_editor, category=hda_cate, hda_name=hda_name
            ):
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg=f'[{node_cnt + 1}/{total_node_cnt}] "{hda_name} (v{hda_ver})" iHDA node\'s category and current network category are different',
                )
                continue
            imported = self._import_hda_into_houdini(
                parent_node=network_editor.pwd(),
                position=cursor_pos + (offset_pos * num_count),
                data=model_data,
            )
            if imported is None:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg=f'[{node_cnt + 1}/{total_node_cnt}] failed to get "{hda_name} (v{hda_ver})" iHDA node',
                )
                continue
            node = imported.node
            repository.record_use(hda_id)
            # 서브넷인 경우 unpack할 수 있기때문에 unpack 함수 위에 둬야 한다.
            pnode_path = node.parent().path()
            node_type = houdini_api.HoudiniAPI.node_type_name(node) or ""
            node_cate = houdini_api.HoudiniAPI.node_category_type_name(node) or ""
            show_comments = self.bindings.ui.actionComment.isChecked()
            self._hda_info_to_node_comment(
                node=node,
                hda_name=hda_name,
                hda_ver=hda_ver,
                hda_id=hda_id,
                show_comments=show_comments,
                is_unpack_subnet=self.bindings.ui.actionUnpack_Subnet.isChecked(),
            )
            # node connections
            connections = repository.node_connections(hda_id)
            self._set_node_connections(
                node=node,
                input_connectors=connections.inputs,
                output_connectors=connections.outputs,
            )
            node.setSelected(True, clear_all_selected=False)
            if (
                self.bindings.ui.actionUnpack_Subnet.isChecked()
                and houdini_api.HoudiniAPI.is_subnet_nodetype(node)
            ):
                self._extract_subnet(
                    node=node, note_contents=hda_note, hda_name=hda_name
                )
            else:
                # subnet을 풀지 않았다면
                # iHDA 노트 내용을 Houdini Sticky Note로
                self._create_sticky_netbox(
                    node=node.parent(),
                    note_contents=hda_note,
                    hda_name=hda_name,
                    items=(node,),
                )
            hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
            hip_dirpath = hip_filepath.parent
            hip_filename = hip_filepath.name
            hou_version = houdini_api.HoudiniAPI.current_houdini_version()
            declare_os = platform_info.platform_system()
            frinfo = houdini_api.HoudiniAPI.frame_info()
            usage = SceneRecordInput(
                hda_key_id=hda_id,
                version_uuid=imported.version_uuid,
                hip_filename=hip_filename,
                hip_dirpath=hip_dirpath,
                hda_filename=hda_filename,
                hda_dirpath=hda_dirpath,
                parent_node_path=pnode_path,
                node_type=node_type,
                node_cate=node_cate,
                node_name=hda_name,
                node_ver=hda_ver,
                hou_version=hou_version,
                hou_license=curt_houdini_license,
                operating_sys=declare_os,
                sf=frinfo[0],
                ef=frinfo[1],
                fps=frinfo[2],
            )
            try:
                last_hda_record_id = repository.record_scene_usage(usage)
            except LibraryError:
                logging.exception("Imported node, but scene usage could not be saved")
                self.bindings.presentation._dragdrop_overlay_close()
                return
            val_datetime = datetime.today().strftime(keys.Value.datetime_fmt_str)
            record_data = decode_record(
                SceneRecord,
                {
                    "record_id": last_hda_record_id,
                    "hda_id": hda_id,
                    "hip_filename": hip_filename,
                    "hip_dirpath": hip_dirpath,
                    "hda_filename": hda_filename,
                    "hda_dirpath": hda_dirpath,
                    "parent_node_path": pnode_path,
                    "node_type": node_type,
                    "node_cate": node_cate,
                    "node_name": hda_name,
                    "node_ver": hda_ver,
                    "houdini_version": hou_version,
                    "houdini_license": curt_houdini_license,
                    "operating_system": declare_os,
                    "sf": frinfo[0],
                    "ef": frinfo[1],
                    "fps": frinfo[2],
                    "ctime": val_datetime,
                    "mtime": val_datetime,
                },
            )
            self._insert_hda_node_loc_record(record_data=record_data)
            log_handler.LogHandler.log_msg(
                method=logging.debug,
                msg=f'[{node_cnt + 1}/{total_node_cnt}] imported "{hda_name} (v{hda_ver})" iHDA node',
            )
            num_count += 1
        self.bindings.presentation._dragdrop_overlay_close()

    def _insert_hda_node_loc_record(self, record_data: SceneRecord) -> None:
        self.bindings.models._add_record_item(data=record_data)

    @staticmethod
    def _hda_note_to_sticky_note(
        node: hou.Node | None = None, note_contents: str | None = None
    ) -> hou.StickyNote | None:
        if (note_contents is None) or (not len(note_contents)):
            return None
        sticky = houdini_api.HoudiniAPI.create_sticky_note(
            node=node, contents=note_contents
        )
        return sticky

    @staticmethod
    def _hda_info_to_node_comment(
        node: hou.Node | None = None,
        hda_name: str | None = None,
        hda_ver: Any = None,
        hda_id: int | None = None,
        show_comments: bool = False,
        is_unpack_subnet: bool = False,
    ) -> None:
        ihda_name_key = keys.Key.Comment.ihda_name
        ihda_ver_key = keys.Key.Comment.ihda_version
        ihda_id_key = keys.Key.Comment.ihda_id
        contents = f"{ihda_name_key}: {hda_name}\n{ihda_ver_key}: {hda_ver}\n{ihda_id_key}: {hda_id}"
        houdini_api.HoudiniAPI.set_node_comment(
            node=node,
            contents=contents,
            show_comments=show_comments,
            is_unpack_subnet=is_unpack_subnet,
        )

    def _import_hda_into_houdini(
        self,
        parent_node: hou.Node | None = None,
        position: hou.Vector2 | None = None,
        data: DragRecord | None = None,
    ) -> ImportedNode | None:
        if data is None:
            return None
        if isinstance(data, HistoryData):
            hda_dirpath = data.ihda_dirpath
            hda_filename = data.ihda_filename
            hda_name = data.org_hda_name
            hda_type_name = data.node_type_name
            hda_id = data.hda_id
        else:
            # record 데이터가 아니라면
            if isinstance(data, AssetData):
                hda_dirpath = data.hda_dirpath
                hda_filename = data.hda_filename
                hda_name = data.hda_name
                hda_type_name = data.node_type_name
                hda_id = data.hda_id
            # record 데이터라면
            else:
                hda_dirpath = data.hda_dirpath
                hda_filename = data.hda_filename
                # model/data에서는 version과 함께 새로운 이름 쓰고 있어서 오리지날 이름으로 가져와야 함.
                hda_name = data.node_name
                hda_type_name = data.node_type
                hda_id = data.hda_id
        if hda_dirpath is None or not hda_filename:
            return None
        hda_filepath = hda_dirpath / hda_filename
        # 만약 hda 파일이 존재하지 않는다면
        if not hda_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg="")
            return None
        # 임포트하려는 노드이름이 현재 네트워크에 존재한다면
        self.bindings.presentation._change_org_node_name(
            parent_node=parent_node, node_name=hda_name
        )
        node = self.bindings.services.host_scene.import_individual_hda_into_houdini(
            node_filepath=hda_filepath,
            parent_node=parent_node,
            position=position,
            node_name=hda_name,
            node_type_name=hda_type_name,
        )
        if node is None:
            return None
        if not isinstance(data, HistoryData):
            row = self.bindings.models.assets.id_rows.get(hda_id)
            if row is not None:
                self.bindings.queries._change_hda_data(
                    row=row,
                    key=keys.Key.hda_load_count,
                    val=self.bindings.models.assets.rows[row].hda_load_count + 1,
                )
        version_uuid = data.version_uuid if isinstance(data, SceneRecord) else None
        if self.bindings.session.context is not None and (
            not isinstance(data, SceneRecord) or version_uuid
        ):
            try:
                uuid = self.bindings.session.require_repository().version_identity(
                    hda_id,
                    data.hist_id if isinstance(data, HistoryData) else None,
                    version_uuid,
                )
                if uuid:
                    version_uuid = uuid
                    self.bindings.scene_usage().observe(
                        node,
                        uuid,
                        "local:"
                        + str(self.bindings.session.context.db_filepath.resolve()),
                    )
            except Exception:
                logging.exception(
                    "Imported asset; version tracking could not be recorded"
                )
        return ImportedNode(node=node, version_uuid=version_uuid)

    def _extract_subnet(
        self,
        node: hou.Node | None = None,
        note_contents: str | None = None,
        hda_name: str = "",
    ) -> None:
        if node is None:
            return
        if hasattr(node, "extractAndDelete"):
            self._create_sticky_netbox(
                node=node, note_contents=note_contents, hda_name=hda_name
            )
            node.extractAndDelete()

    def _create_sticky_netbox(
        self,
        node: hou.Node | None = None,
        note_contents: str | None = None,
        hda_name: str = "",
        items: Any = (),
    ) -> None:
        # iHDA 노트 내용을 Houdini Sticky Note로
        if node is None:
            return
        if self.bindings.ui.actionSticky_Note.isChecked():
            net_item = list(items)
            # hda note의 내용이 있다면, subnet안에 sticky note 생성 후 내용 입력
            sticky = self._hda_note_to_sticky_note(
                node=node, note_contents=note_contents
            )
            if sticky is None:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg="content of the iHDA note was empty, so didn't create houdini sticky note",
                )
                if len(net_item) == 1:
                    return
            else:
                if len(net_item):
                    sticky.move(houdini_api.HoudiniAPI.items_position(items=items))
                    net_item.append(sticky)
                else:
                    sticky.move(
                        houdini_api.HoudiniAPI.items_position(items=node.allItems())
                    )
            # networkbox 생성
            houdini_api.HoudiniAPI.create_network_box(
                node=node, comment=hda_name, items=net_item
            )

    def _set_node_connections(
        self,
        node: hou.Node | None = None,
        input_connectors: Any = None,
        output_connectors: Any = None,
    ) -> None:
        if self.bindings.ui.actionNull.isChecked():
            pass
        elif self.bindings.ui.actionInput.isChecked():
            houdini_api.HoudiniAPI.set_node_input_connections(
                node=node, connection_lst=input_connectors
            )
        elif self.bindings.ui.actionOuput.isChecked():
            houdini_api.HoudiniAPI.set_node_output_connections(
                node=node, connection_lst=output_connectors
            )
        else:
            houdini_api.HoudiniAPI.set_node_input_connections(
                node=node, connection_lst=input_connectors
            )
            houdini_api.HoudiniAPI.set_node_output_connections(
                node=node, connection_lst=output_connectors
            )
