"""Asset registration for the Individual HDA panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets

from libs import host, houdini_api, keys, log_handler, platform_info
from libs.repository import RegistrationPayload, RegistrationResult
from widgets.asset_lifecycle.capture import HoudiniRegistrationCapture

if TYPE_CHECKING:
    import hou

    from widgets.panel.library_port import LibraryPort
    from widgets.panel.ports import (
        AssetManagementPort,
        AssetModelPort,
        CallbacksPort,
        HoudiniActionsPort,
        InsidePagePort,
        LibraryQueryPort,
        PresentationPort,
        SelectionPort,
    )


from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState
    from widgets.preference.preference import Preference


@dataclass(frozen=True, slots=True)
class PanelAssetRegistrationBindings:
    callbacks: CallbacksPort
    houdini: HoudiniActionsPort
    management: AssetManagementPort
    models: AssetModelPort
    parent: QtWidgets.QWidget
    preference: Preference
    presentation: PresentationPort
    queries: LibraryQueryPort
    reload_library: Callable[[], None]
    selection: SelectionPort
    inside_page: Callable[[], InsidePagePort]
    services: PanelServices
    session: PanelSessionState
    library: Callable[[], LibraryPort]
    ui: MainWindowLayout


class PanelAssetRegistration:
    bindings: PanelAssetRegistrationBindings

    @QtCore.Slot(object)
    def _slot_drop_node_into_hda_view(
        self, node_lst: list[hou.Node] | tuple[hou.Node, ...] | None
    ) -> None:
        if not self.bindings.services.host_actions_enabled:
            return
        if self.bindings.library().register_nodes(node_lst):
            return
        if not host.IS_HOUDINI:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="houdini is not running"
            )
            return
        if not self.bindings.preference.is_valid_data_dirpath():
            log_handler.LogHandler.log_msg(
                method=logging.critical,
                msg="folder where the data is stored has not been set or the folder does not exist",
            )
            self.bindings.preference.show()
            return
        if not node_lst:
            return
        total_node_cnt = len(node_lst)
        if total_node_cnt > self.bindings.services.policy.maximum_node_batch:
            self.bindings.presentation.notify(
                f"Too many nodes to register: {total_node_cnt} dropped, the limit is"
                f" {self.bindings.services.policy.maximum_node_batch}.",
                level="error",
            )
            return
        if total_node_cnt > self.bindings.services.policy.warn_node_batch:
            msgbox = QtWidgets.QMessageBox(self.bindings.parent)
            msgbox.setFont(self.bindings.presentation.get_default_font())
            msgbox.setWindowTitle("iHDA Node Registration")
            msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msgbox.setText(
                f"""
The number of nodes you are trying to register exceeds {self.bindings.services.policy.warn_node_batch}.
Should I proceed with registration?

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
                    method=logging.info, msg="Node registration has been canceled"
                )
                return
        self.bindings.presentation.dragdrop_overlay_show(
            text="Create iHDA node\nPlease wait..."
        )
        self.bindings.callbacks.wrapper_execute_deferred(
            lambda: self._make_houdini_node_to_ihda_node(
                node_lst=node_lst, total_node_cnt=total_node_cnt
            )
        )

    def _make_houdini_node_to_ihda_node(
        self,
        node_lst: list[hou.Node] | tuple[hou.Node, ...] | None = None,
        total_node_cnt: int | None = None,
    ) -> None:
        try:
            self._register_dropped_nodes(node_lst or (), total_node_cnt or 0)
        finally:
            self.bindings.presentation.dragdrop_overlay_close()

    def _register_dropped_nodes(self, node_lst: Any, total_node_cnt: int) -> None:
        is_declare = False
        skipped = 0
        for node_cnt, node_dat in enumerate(node_lst):
            node_path = (
                node_dat
                if isinstance(node_dat, str)
                else bytes(node_dat).decode("utf-8")
            )
            node = houdini_api.HoudiniAPI.find_node(node_path)
            if node is None:
                continue
            node_name = node.name()
            # 유효한 후디니 노드인지
            if not houdini_api.HoudiniAPI.is_valid_node(node=node):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'[{node_cnt + 1}/{total_node_cnt}] "{node_name}" node cannot be registered. check the error message',
                )
                skipped += 1
                continue
            # 유효한 후디니 노드 이름인지
            if (
                (
                    not houdini_api.HoudiniAPI.is_valid_node_name(
                        node=node, verbose=False
                    )
                )
                or (node_name.startswith("_"))
                or (node_name[0].isdigit())
            ):
                # 자동 이름 변경이 활성화되어있다면
                if self.bindings.ui.actionAutomatic_Name_Change.isChecked():
                    new_node_name = f"{keys.Name.hda_prefix_str.lower()}_{node_name}"
                    # 노드 이름 변경
                    node.setName(new_node_name, unique_name=True)
                    node_path = node.path()
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg=f'[{node_cnt + 1}/{total_node_cnt}] (automatically rename) "{node_name}" >>>>> "{new_node_name}"',
                    )
                else:
                    if not houdini_api.HoudiniAPI.is_valid_node_name(
                        node=node, verbose=True
                    ):
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg=f'[{node_cnt + 1}/{total_node_cnt}] "{node_name}" node cannot be registered. check the error message',
                        )
                        skipped += 1
                        continue
                    # 현재 후디니버전 18.0.429 에서 노드이름이 _(언더바)/숫자로 처음 시작하게 되면 에러 발생한다. 그래서 아래 코드 추가함.
                    if (node_name.startswith("_")) or (node_name[0].isdigit()):
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg=f'[{node_cnt + 1}/{total_node_cnt}] "{node_name}" _(underline) or numbers should not be in the first \
                            word of the node name. change the node name',
                        )
                        skipped += 1
                        continue
            node_cate = houdini_api.HoudiniAPI.node_category_type_name(node) or ""
            try:
                is_done_node = self._node_declare(node=node)
            except Exception as error:
                self.bindings.management.show_command_error(
                    f"Registration failed for {node_name}: {error}"
                )
                is_done_node = False
            if not is_done_node:
                node.setName(node_name, unique_name=True)
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg=f'[{node_cnt + 1}/{total_node_cnt}] "{node_name}" node DB input failed',
                )
                skipped += 1
                continue
            self.bindings.models.add_category_item(category=node_cate)
            is_declare = True
            log_handler.LogHandler.log_msg(
                method=logging.debug,
                msg=f'[{node_cnt + 1}/{total_node_cnt}] node dropped "{node_path}" ({node_cate})',
            )
        if skipped:
            self.bindings.presentation.notify(
                f"Skipped {skipped} of {total_node_cnt} nodes; the log says why.",
                level="warning",
            )
        if is_declare:
            self.bindings.selection.select_category(
                category=self.bindings.selection.state.item_text
            )
            self.bindings.inside_page().mark_stale()  # comments were written

    def _node_declare(self, node: hou.Node | None = None) -> bool:
        if node is None:
            return False
        is_display_flag = None
        is_render_flag = None
        if hasattr(node, "isDisplayFlagSet"):
            is_display_flag = node.isDisplayFlagSet()
        if hasattr(node, "isRenderFlagSet"):
            is_render_flag = node.isRenderFlagSet()
        try:
            return self._declare_registration(node)
        finally:
            if is_display_flag is not None:
                node.setDisplayFlag(is_display_flag)
            if is_render_flag is not None:
                node.setRenderFlag(is_render_flag)

    def _declare_registration(self, node: hou.Node) -> bool:
        node_name = node.name()
        node_cate = houdini_api.HoudiniAPI.node_category_type_name(node) or ""
        item_key_lst = [node_cate, node_name]
        is_exist_hda_name = self.bindings.session.require_repository().has_asset(
            self.bindings.session.user, node_cate, node_name
        )
        self.bindings.selection.state.set_category_parents(item_key_lst)
        # 만약 등록하려는 Category의 HDA의 이름이 DB에 존재한다면,
        if is_exist_hda_name:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg=f"{node_name} in the {node_cate} category exists...",
            )
            identity = self.bindings.session.require_repository().asset_identity(
                self.bindings.session.user, node_cate, node_name
            )
            if identity is None:
                return False
            hda_key_id = identity.asset_id
            # 업데이트하려는 노드가 저장되어있는 노드 타입과 같은지 확인
            if identity.node_type != houdini_api.HoudiniAPI.node_type_name(node):
                self.bindings.presentation.notify(
                    f'"{node_name}" is a different node type from the stored asset;'
                    " rename it to register it separately.",
                    level="error",
                )
                return False
            from libs.registration_request import RegistrationRequest, bump_version
            from widgets.registration_dialog import RegistrationDialog

            dialog = RegistrationDialog(
                self.bindings.parent,
                title="Update iHDA Node",
                request=RegistrationRequest(
                    node_name, node_cate, bump_version(identity.version or "")
                ),
                categories=[node_cate],
                lock_identity=True,
            )
            dialog.setFont(self.bindings.presentation.get_default_font())
            accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
            request = dialog.request()
            dialog.deleteLater()
            if not accepted:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="update has been canceled"
                )
                return False
            version, description = request.version, request.description
            node_info_dict = self._node_info_data(
                key_lst=item_key_lst, node=node, version=version
            )
            if node_info_dict is None:
                return False
            # update 진행
            node_info_dict["version_description"] = description
            is_done_db = self._update_to_hda_db(
                info_data=node_info_dict, hda_key_id=hda_key_id
            )
        else:
            node_info_dict = self._node_info_data(
                key_lst=item_key_lst, node=node, version=keys.Value.init_hda_version
            )
            if node_info_dict is None:
                return False
            is_done_db = self._insert_to_hda_db(info_data=node_info_dict)
        return bool(is_done_db)

    def _node_info_data(
        self,
        key_lst: list[str] | None = None,
        node: hou.Node | None = None,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        # hda info
        node_info_dict = self._get_hda_info(key_lst=key_lst, node=node, version=version)
        if node_info_dict is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="invalid node. stop node creation"
            )
            return None
        return node_info_dict

    def _get_hda_info(
        self,
        key_lst: list[str] | None = None,
        node: hou.Node | None = None,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        base = self.bindings.queries.hda_base_dirpath
        if base is None or node is None or key_lst is None or version is None:
            return None
        hda_dirpath = base.joinpath("/".join(key_lst))
        hda = houdini_api.HoudiniAPI(
            hda_version=version, node_path=node.path(), hda_dirpath=hda_dirpath
        )
        node_info_dict = hda.get_individual_hda_data()
        if not len(node_info_dict):
            return None
        return node_info_dict

    def _registration_payload(self, info_data: dict[str, Any]) -> RegistrationPayload:
        """Gather everything HOM knows on the GUI thread; the repository writes it."""
        node = info_data[keys.Key.node]
        version = info_data[keys.Key.hda_version]
        hda_dirpath = info_data[keys.Key.hda_dirpath]
        assert isinstance(hda_dirpath, pathlib.Path)
        thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(
            hda_dirpath=hda_dirpath
        )
        thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(
            name=node.name(), version=version
        )
        hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        sf, ef, fps = houdini_api.HoudiniAPI.frame_info()
        return RegistrationPayload(
            user=self.bindings.session.user,
            node_name=node.name(),
            node_path=node.path(),
            version=version,
            hda_dirpath=hda_dirpath,
            hda_filename=info_data[keys.Key.hda_filename],
            type_name=info_data[keys.Key.node_type_name],
            cate_name=info_data[keys.Key.node_cate_name],
            def_desc=info_data[keys.Key.node_def_desc],
            is_network=info_data[keys.Key.is_network],
            is_sub_network=info_data[keys.Key.is_sub_network],
            type_path_lst=tuple(info_data[keys.Key.node_type_path_list]),
            cate_path_lst=tuple(info_data[keys.Key.node_cate_path_list]),
            icon_path_lst=tuple(info_data[keys.Key.node_icon_path_list]),
            input_conn=tuple(info_data[keys.Key.node_input_connections]),
            output_conn=tuple(info_data[keys.Key.node_output_connections]),
            hou_version=houdini_api.HoudiniAPI.current_houdini_version(),
            hou_license=houdini_api.HoudiniAPI.current_houdini_license(),
            operating_system=platform_info.platform_system(),
            hip_filename=hip_filepath.name,
            hip_dirpath=hip_filepath.parent,
            sf=sf,
            ef=ef,
            fps=fps,
            thumb_dirpath=thumb_dirpath,
            thumb_filename=thumb_filename,
            registered_at=datetime.today().strftime(keys.Value.datetime_fmt_str),
            description=info_data.get("version_description", ""),
        )

    def _update_to_hda_db(
        self,
        info_data: dict[str, Any] | None = None,
        hda_key_id: int | None = None,
    ) -> bool:
        if info_data is None or hda_key_id is None:
            return False
        payload = self._registration_payload(info_data)
        return self._register_captured_asset(
            payload,
            hda_key_id,
            lambda result: self._apply_registered_version(hda_key_id, payload, result),
        )

    def _register_captured_asset(
        self,
        payload: RegistrationPayload,
        asset_id: int | None,
        committed: Callable[[RegistrationResult], None],
    ) -> bool:
        gateway = self.bindings.services.lifecycle(
            self.bindings.session.require_repository(), self.bindings.services.names
        )
        service = self.bindings.services.registration(gateway)
        node = houdini_api.HoudiniAPI.find_node(payload.node_path)
        if node is None:
            self.bindings.management.show_command_error(
                "The Houdini node no longer exists"
            )
            return False

        def show_committed(result: RegistrationResult) -> None:
            try:
                committed(result)
            except Exception as error:
                self.bindings.management.show_command_error(
                    f"Asset saved, but the display could not be updated: {error}. Reload the library."
                )
                try:
                    self.bindings.reload_library()
                except Exception as reload_error:
                    self.bindings.management.show_command_error(
                        f"Automatic reload failed: {reload_error}"
                    )

        return self.bindings.management.asset_commands().capture_and_register(
            service,
            payload,
            HoudiniRegistrationCapture(
                node, payload.version, self.bindings.services.host_capture
            ),
            asset_id,
            show_committed,
        )

    def _apply_registered_version(
        self, hda_key_id: int, payload: RegistrationPayload, result: RegistrationResult
    ) -> None:
        self.bindings.models.update_pixmap_thumbnail(
            hkey_id=hda_key_id, thumb_filepath=result.thumb_filepath
        )
        self.bindings.models.update_item_row_data(
            row=self.bindings.management.get_hda_id_row_map().get(hda_key_id),
            row_data=result.asset,
        )
        self.bindings.models.add_pixmap_hist_thumbnail(
            hist_id=result.history_id, thumb_filepath=result.thumb_filepath
        )
        self.bindings.models.insert_ihda_history_data_model(
            data=result.history,
            hist_id=result.history_id,
            tags=result.asset.hda_tags,
        )
        self.bindings.selection.set_hist_ihda_to_combobox(
            hkey_id=hda_key_id, hda_name=payload.node_name
        )

    def _insert_to_hda_db(
        self,
        info_data: dict[str, Any] | None = None,
    ) -> bool:
        if info_data is None:
            return False
        payload = self._registration_payload(info_data)
        return self._register_captured_asset(
            payload,
            None,
            lambda result: self._apply_registered_asset(info_data, payload, result),
        )

    def _apply_registered_asset(
        self,
        info_data: dict[str, Any],
        payload: RegistrationPayload,
        result: RegistrationResult,
    ) -> None:
        key_id = result.asset.hda_id
        self.bindings.models.add_pixmap_ihda(
            hkey_id=key_id, icon_lst=list(payload.icon_path_lst)
        )
        self.bindings.models.add_pixmap_thumbnail(
            hkey_id=key_id, thumb_filepath=result.thumb_filepath
        )
        self.bindings.models.add_pixmap_hist_thumbnail(
            hist_id=result.history_id, thumb_filepath=result.thumb_filepath
        )
        self.bindings.models.insert_ihda_data_model(data=result.asset)
        self.bindings.models.refresh_asset_search()
        self.bindings.ui.label__hda_count.setText(
            str(self.bindings.models.list_proxy_model.rowCount())
        )
        self.bindings.ui.label__cate_count.setText(
            str(self.bindings.models.get_category_count())
        )
        self.bindings.models.insert_ihda_history_data_model(
            data=result.history, hist_id=result.history_id, tags=[]
        )
        self.bindings.selection.set_hist_ihda_to_combobox(
            hkey_id=key_id, hda_name=payload.node_name
        )
        self.bindings.houdini.hda_info_to_node_comment(
            node=info_data.get(keys.Key.node),
            hda_name=payload.node_name,
            hda_ver=payload.version,
            hda_id=key_id,
        )
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="comments have been added to existing Houdini node(s)",
        )
