"""Houdini actions on the panel GUI thread.

Uses the shared panel protected state; no independent QObject ownership.
"""

from __future__ import annotations

from typing import Any

from libs.drag_payload import decode_payload
import logging
from datetime import datetime
from PySide6 import QtWidgets, QtCore
import public
import pathlib
from libs import houdini_api, log_handler
from libs import sqlite3_db_api

try:
    import hou
except ImportError:
    pass


class HoudiniActionsMixin:
    @QtCore.Slot(object)
    def _slot_mouse_move_event_on_houdini(self, drop_data: Any) -> None:
        # [[id, name, category, filename, dirpath, icon_lst, tag_lst], [...], ...]
        if not public.IS_HOUDINI:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="please drag from houdini"
            )
            self._dragdrop_overlay_close()
            return
        drop_action, model_data_lst = drop_data
        assert isinstance(model_data_lst, list)
        if drop_action != QtCore.Qt.IgnoreAction:
            self._dragdrop_overlay_close()
            return
        network_editor = houdini_api.HoudiniAPI.find_network_editor_by_cursor()
        if network_editor is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="houdini network not found"
            )
            self._dragdrop_overlay_close()
            return
        total_node_cnt = len(model_data_lst)
        if not total_node_cnt:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="imported iHDA data is empty"
            )
            self._dragdrop_overlay_close()
            return
        # 노드 개수가 30개를 초과하면 종료
        if total_node_cnt > self._MAX_NUM_OF_NODE_REGIST:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setWindowTitle("Import iHDA Node")
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText("Too many nodes to import")
            msgbox.setDetailedText(
                """
            Please bring no more than {0} items.
            Total Nodes: {1}
            """.format(self._MAX_NUM_OF_NODE_REGIST, total_node_cnt)
            )
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec()
            return
        # 만약 등록하려는 노드 개수가 10개를 초과하면 등록할 것인지 메시지박스를 띄운다.
        if total_node_cnt > public.Value.warning_num_of_node_regist:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setWindowTitle("Import iHDA Node")
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText(
                """
            The number of iHDA nodes you are trying to import exceeds {0}.
            Should I bring it though?

            NOTE: Registering a large number of nodes at a time may make the Houdini appear to be stationary.
            But it didn't stop, so please wait a little longer.
            """.format(public.Value.warning_num_of_node_regist)
            )
            msgbox.setDetailedText("Total Nodes: {0}".format(total_node_cnt))
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            reply = msgbox.exec()
            if reply == QtWidgets.QMessageBox.No:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="importing iHDA nodes was canceled"
                )
                self._dragdrop_overlay_close()
                return
        # 기존에 선택된 노드가 존재한다면 모두 선택 해제
        old_selected_nodes = houdini_api.HoudiniAPI.get_selected_nodes()
        if old_selected_nodes is not None:
            houdini_api.HoudiniAPI.all_clear_selected(node=old_selected_nodes[0])
        # node 위치 옵셋 값
        offset_pos = hou.Vector2((1, -1))
        network_editor.setIsCurrentTab()
        cursor_pos = houdini_api.HoudiniAPI.get_cursor_pos(
            network_editor=network_editor
        )
        self._wrapper_execute_deferred(
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
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        num_count = 0
        for node_cnt, model_data in enumerate(model_data_lst):
            model_data = decode_payload(model_data)
            # record data 인지 확인하는 변수
            is_record_data = model_data.get(public.Key.Record.record_id)
            # 만약 히스토리에서 드래그&드롭 하는 것이라면
            if self._is_ihda_history_view:
                hda_cate = model_data.get(public.Key.History.node_category)
                hda_id = model_data.get(public.Key.History.hda_id)
                hda_name = model_data.get(public.Key.History.org_hda_name)
                hda_ver = model_data.get(public.Key.History.version)
                hda_dirpath = model_data.get(public.Key.History.ihda_dirpath)
                hda_filename = model_data.get(public.Key.History.ihda_filename)
                hda_license = model_data.get(public.Key.History.hda_license)
                hda_note = db_api.get_hda_note_history_most_recent_by_ver(
                    hda_key_id=hda_id, version=hda_ver
                )
                item_row = model_data.get(public.Key.History.item_row)
            else:
                # record data가 아니라면
                if is_record_data is None:
                    hda_cate = model_data.get(public.Key.hda_cate)
                    hda_id = model_data.get(public.Key.hda_id)
                    hda_name = model_data.get(public.Key.hda_name)
                    hda_ver = model_data.get(public.Key.hda_version)
                    hda_dirpath = model_data.get(public.Key.hda_dirpath)
                    hda_filename = model_data.get(public.Key.hda_filename)
                    hda_license = model_data.get(public.Key.hda_license)
                    hda_note = db_api.get_note_info(hda_key_id=hda_id)
                    item_row = model_data.get(public.Key.item_row)
                # record data라면
                else:
                    hda_cate = model_data.get(public.Key.Record.node_cate)
                    hda_id = model_data.get(public.Key.Record.hda_id)
                    hda_name = model_data.get(public.Key.Record.org_node_name)
                    hda_ver = model_data.get(public.Key.Record.node_ver)
                    hda_dirpath = model_data.get(public.Key.Record.hda_dirpath)
                    hda_filename = model_data.get(public.Key.Record.hda_filename)
                    # 라이센스는 hda data 의 것을 가져와야 함. 왜냐면, loc data의 라이센스는 ihda노드를 후디니로
                    # 내보낼때 그 당시의 후디니 라이센스이기 때문이다. 허나 hda 데이터나 hda history 데이터는
                    # 후디니 노드를 hda로 만들 때의 후디니 라이센스라서 hda도 논커머셜인지 커머셜인지 결정 됨.
                    hda_license = db_api.get_hist_hda_license(
                        hda_key_id=hda_id, version=hda_ver, user_id=self._user
                    )
                    hda_note = db_api.get_hda_note_history_most_recent_by_ver(
                        hda_key_id=hda_id, version=hda_ver
                    )
                    item_row = self._get_ihda_data_by_id(
                        hda_id=hda_id, key=public.Key.item_row
                    )
            hda_filepath = hda_dirpath / hda_filename
            assert isinstance(hda_dirpath, pathlib.Path)
            # DB에는 존재하지만 지정된 곳에 파일이 존재하지 않는다면
            if not hda_filepath.exists():
                log_handler.LogHandler.log_msg(
                    method=logging.critical,
                    msg='[{0}/{1}] "{2} (v{3})" iHDA file does not exist'.format(
                        node_cnt + 1, total_node_cnt, hda_name, hda_ver
                    ),
                )
                continue
            # item의 row (model에서 셋팅해 놓았음)
            if self._is_ihda_history_view:
                self._selection.history.row = item_row
                self._selection.history.filepath = hda_filepath
                self._selection.history.name = hda_name
                self._selection.history.id = hda_id
                self._selection.history.data = model_data
                self._selection.history.cate = hda_cate
                self._selection.history.hist_id = model_data.get(
                    public.Key.History.hist_id
                )
                self._selection.history.version = hda_ver
            else:
                self._selection.asset.row = item_row
                self._selection.asset.filepath = hda_filepath
                self._selection.asset.name = hda_name
                self._selection.asset.id = hda_id
                self._selection.asset.data = model_data
                self._selection.asset.cate = hda_cate
                self._selection.asset.version = hda_ver
            # 현재 Houdini 라이센스
            curt_houdini_license = houdini_api.HoudiniAPI.current_houdini_license()
            # 후디니는 commercial라이센스인데 iHDA는 아니라면
            if not self._ihda_license_check(hda_license=hda_license):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='[{0}/{1}] houdini license and "{2} (v{3})" iHDA license are different'.format(
                        node_cnt + 1, total_node_cnt, hda_name, hda_ver
                    ),
                )
                msgbox = QtWidgets.QMessageBox(self)
                msgbox.setFont(self._get_default_font())
                msgbox.setWindowTitle("Import iHDA Node")
                msgbox.setIcon(QtWidgets.QMessageBox.Warning)
                msgbox.setText(
                    """
                [{0}/{1}] Imported "{2} (v{3})" iHDA are not commercial.
                When I import it into the current HIP file, the HIP file also becomes non-commercial.
                Should I bring it though?""".format(
                        node_cnt + 1, total_node_cnt, hda_name, hda_ver
                    )
                )
                msgbox.setDetailedText(
                    """
                Current HIP File License: {0}
                Current iHDA Node License: {1}
                """.format(curt_houdini_license, hda_license)
                )
                # msgbox.resize(msgbox.sizeHint())
                msgbox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                reply = msgbox.exec()
                if reply == QtWidgets.QMessageBox.No:
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg='[{0}/{1}] importing "{2} (v{3})" iHDA nodes was canceled'.format(
                            node_cnt + 1, total_node_cnt, hda_name, hda_ver
                        ),
                    )
                    continue
            if not self._is_valid_network_category(
                network_editor=network_editor, category=hda_cate, hda_name=hda_name
            ):
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] "{2} (v{3})" iHDA node\'s category and current network category are different'.format(
                        node_cnt + 1, total_node_cnt, hda_name, hda_ver
                    ),
                )
                continue
            node = self._import_hda_into_houdini(
                parent_node=hou.node(network_editor.pwd().path()),
                position=cursor_pos + (offset_pos * num_count),
                data=model_data,
            )
            if node is None:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] failed to get "{2} (v{3})" iHDA node'.format(
                        node_cnt + 1, total_node_cnt, hda_name, hda_ver
                    ),
                )
                continue
            db_api.update_load_count(hda_key_id=hda_id)
            # 서브넷인 경우 unpack할 수 있기때문에 unpack 함수 위에 둬야 한다.
            pnode_path = node.parent().path()
            node_type = houdini_api.HoudiniAPI.node_type_name(node)
            node_cate = houdini_api.HoudiniAPI.node_category_type_name(node)
            show_comments = self.actionComment.isChecked()
            self._hda_info_to_node_comment(
                node=node,
                hda_name=hda_name,
                hda_ver=hda_ver,
                hda_id=hda_id,
                show_comments=show_comments,
                is_unpack_subnet=self.actionUnpack_Subnet.isChecked(),
            )
            # node connections
            info_id = db_api.get_hou_node_info_id(hda_key_id=hda_id)
            node_input_connections = db_api.get_houdini_node_input_connect_info(
                info_id=info_id
            )
            node_output_connections = db_api.get_houdini_node_output_connect_info(
                info_id=info_id
            )
            self._set_node_connections(
                node=node,
                input_connectors=node_input_connections,
                output_connectors=node_output_connections,
            )
            node.setSelected(True, clear_all_selected=False)
            if (
                self.actionUnpack_Subnet.isChecked()
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
            declare_os = public.platform_system()
            frinfo = houdini_api.HoudiniAPI.frame_info()
            is_hda_node_loc_record = db_api.insert_hda_node_location_record(
                hda_key_id=hda_id,
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
            if is_hda_node_loc_record is None:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] cannot enter "{2} (v{3})" iHDA node information'.format(
                        node_cnt + 1, total_node_cnt, hda_name, hda_ver
                    ),
                )
                self._dragdrop_overlay_close()
                return
            last_hda_record_id = db_api.get_last_insert_id
            val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
            record_data = [
                last_hda_record_id,
                hda_id,
                hip_filename,
                hip_dirpath,
                hda_filename,
                hda_dirpath,
                pnode_path,
                node_type,
                node_cate,
                hda_name,
                hda_ver,
                hou_version,
                curt_houdini_license,
                declare_os,
                frinfo[0],
                frinfo[1],
                frinfo[2],
                val_datetime,
                val_datetime,
            ]
            self._insert_hda_node_loc_record(record_data=record_data)
            log_handler.LogHandler.log_msg(
                method=logging.debug,
                msg='[{0}/{1}] imported "{2} (v{3})" iHDA node'.format(
                    node_cnt + 1, total_node_cnt, hda_name, hda_ver
                ),
            )
            num_count += 1
        self._dragdrop_overlay_close()

    def _insert_hda_node_loc_record(self, record_data: Any = None) -> None:
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_record_key_lst()
        assert len(key_lst) == len(record_data)
        rdata = dict(zip(key_lst, record_data))
        hip_dpath = rdata.get(public.Key.Record.hip_dirpath).as_posix()
        hip_fname = rdata.get(public.Key.Record.hip_filename)
        hda_dpath = rdata.get(public.Key.Record.hda_dirpath)
        hda_fname = rdata.get(public.Key.Record.hda_filename)
        pnode_path = rdata.get(public.Key.Record.parent_node_path)
        node_name = rdata.get(public.Key.Record.node_name)
        node_ver = rdata.get(public.Key.Record.node_ver)
        node_type = rdata.get(public.Key.Record.node_type)
        node_cate = rdata.get(public.Key.Record.node_cate)
        record_id = rdata.get(public.Key.Record.record_id)
        hda_id = rdata.get(public.Key.Record.hda_id)
        hou_ver = rdata.get(public.Key.Record.houdini_version)
        hou_lic = rdata.get(public.Key.Record.houdini_license)
        curt_os = rdata.get(public.Key.Record.operating_system)
        sf = rdata.get(public.Key.Record.sf)
        ef = rdata.get(public.Key.Record.ef)
        fps = rdata.get(public.Key.Record.fps)
        ctime = rdata.get(public.Key.Record.ctime)
        mtime = rdata.get(public.Key.Record.mtime)
        # db_api 함수와 동일해야 한다. 그래서 노드 이름 변경함.
        node_name_with_ver = "{0} (v{1})".format(node_name, node_ver)
        new_data = {
            public.Type.root: {
                hip_dpath: {
                    hip_fname: {
                        # 2차원 배열이라는 것에 주의
                        pnode_path: [
                            [
                                record_id,
                                hda_id,
                                node_name_with_ver,
                                node_type,
                                node_cate,
                                node_ver,
                                ctime,
                                mtime,
                                pathlib.Path(hip_dpath),
                                hip_fname,
                                hda_dpath,
                                hda_fname,
                                hou_ver,
                                hou_lic,
                                curt_os,
                                sf,
                                ef,
                                fps,
                                node_name,
                            ]
                        ]
                    }
                }
            }
        }
        self._add_record_item(data=new_data)
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )

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
        ihda_name_key = public.Key.Comment.ihda_name
        ihda_ver_key = public.Key.Comment.ihda_version
        ihda_id_key = public.Key.Comment.ihda_id
        contents = "{0}: {1}\n{2}: {3}\n{4}: {5}".format(
            ihda_name_key, hda_name, ihda_ver_key, hda_ver, ihda_id_key, hda_id
        )
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
        data: Any = None,
    ) -> hou.Node | None:
        is_record_data = data.get(public.Key.Record.record_id)
        if self._is_ihda_history_view:
            hda_dirpath = data.get(public.Key.History.ihda_dirpath)
            hda_filename = data.get(public.Key.History.ihda_filename)
            hda_filepath = hda_dirpath / hda_filename
            hda_name = data.get(public.Key.History.org_hda_name)
            hda_type_name = data.get(public.Key.History.node_type_name)
            hda_id = data.get(public.Key.hda_id)
        else:
            # record 데이터가 아니라면
            if is_record_data is None:
                hda_dirpath = data.get(public.Key.hda_dirpath)
                hda_filename = data.get(public.Key.hda_filename)
                hda_filepath = hda_dirpath / hda_filename
                hda_name = data.get(public.Key.hda_name)
                hda_type_name = data.get(public.Key.node_type_name)
                hda_id = data.get(public.Key.hda_id)
            # record 데이터라면
            else:
                hda_dirpath = data.get(public.Key.Record.hda_dirpath)
                hda_filename = data.get(public.Key.Record.hda_filename)
                hda_filepath = hda_dirpath / hda_filename
                # model/data에서는 version과 함께 새로운 이름 쓰고 있어서 오리지날 이름으로 가져와야 함.
                hda_name = data.get(public.Key.Record.org_node_name)
                hda_type_name = data.get(public.Key.Record.node_type)
                hda_id = data.get(public.Key.Record.hda_id)
        assert isinstance(hda_dirpath, pathlib.Path)
        # 만약 hda 파일이 존재하지 않는다면
        if not hda_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg="")
            return None
        # 임포트하려는 노드이름이 현재 네트워크에 존재한다면
        self._change_org_node_name(parent_node=parent_node, node_name=hda_name)
        node = houdini_api.HoudiniAPI.import_individual_hda_into_houdini(
            node_filepath=hda_filepath,
            parent_node=parent_node,
            position=position,
            node_name=hda_name,
            node_type_name=hda_type_name,
        )
        if node is None:
            return None
        if not self._is_ihda_history_view:
            if is_record_data:
                hda_item_row = self._get_hda_id_row_map().get(hda_id)
                load_count = (
                    self._assets.rows[hda_item_row].get(public.Key.hda_load_count) + 1
                )
                self._change_hda_data(
                    row=hda_item_row, key=public.Key.hda_load_count, val=load_count
                )
            else:
                load_count = data.get(public.Key.hda_load_count) + 1
                self._change_hda_data(
                    row=self._assets.id_rows.get(self._selection.asset.id),
                    key=public.Key.hda_load_count,
                    val=load_count,
                )
        return node

    def _extract_subnet(
        self,
        node: hou.Node | None = None,
        note_contents: str | None = None,
        hda_name: str = "",
    ) -> None:
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
        if self.actionSticky_Note.isChecked():
            net_item = [x for x in items]
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
            net_box = houdini_api.HoudiniAPI.create_network_box(
                node=node, comment=hda_name, items=net_item
            )

    def _set_node_connections(
        self,
        node: hou.Node | None = None,
        input_connectors: Any = None,
        output_connectors: Any = None,
    ) -> None:
        if self.actionNull.isChecked():
            pass
        elif self.actionInput.isChecked():
            houdini_api.HoudiniAPI.set_node_input_connections(
                node=node, connection_lst=input_connectors
            )
        elif self.actionOuput.isChecked():
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
