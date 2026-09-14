"""Asset registration for the Individual HDA panel.

Mixin methods run on the panel GUI thread and share its protected state.
They do not own a separate QWidget or change the public panel interface.
"""

from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

from decimal import Decimal
import logging
import sqlite3
from datetime import datetime
from PySide6 import QtWidgets, QtCore
import public
import pathlib
from libs import houdini_api, log_handler
from libs import sqlite3_db_api, ihda_system

try:
    import hou
except ImportError:
    pass


class AssetRegistrationMixin:
    @QtCore.Slot(object)
    def _slot_drop_node_into_hda_view(
        self, node_lst: list[hou.Node] | tuple[hou.Node, ...] | None
    ) -> None:
        if not public.IS_HOUDINI:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="houdini is not running"
            )
            return
        if not self._preference.is_valid_data_dirpath():
            log_handler.LogHandler.log_msg(
                method=logging.critical,
                msg="folder where the data is stored has not been set or the folder does not exist",
            )
            self._preference.show()
            return
        total_node_cnt = len(node_lst)
        # 만약 한번에 등록하려는 노드 개수가 30개를 초과하면 종료
        if total_node_cnt > self._MAX_NUM_OF_NODE_REGIST:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setWindowTitle("iHDA Node Registration")
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText("Too many nodes to register")
            msgbox.setDetailedText(
                """
Please register less than {0} items.
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
            msgbox.setWindowTitle("iHDA Node Registration")
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText(
                """
The number of nodes you are trying to register exceeds {0}.
Should I proceed with registration?

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
                    method=logging.info, msg="Node registration has been canceled"
                )
                return
        self._dragdrop_overlay_show(text="Create iHDA node\nPlease wait...")
        self._wrapper_execute_deferred(
            lambda: self._make_houdini_node_to_ihda_node(
                node_lst=node_lst, total_node_cnt=total_node_cnt
            )
        )

    def _make_houdini_node_to_ihda_node(
        self,
        node_lst: list[hou.Node] | tuple[hou.Node, ...] | None = None,
        total_node_cnt: int | None = None,
    ) -> None:
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        is_declare = False
        for node_cnt, node_dat in enumerate(node_lst):
            node_path = (
                node_dat
                if isinstance(node_dat, str)
                else bytes(node_dat).decode("utf-8")
            )
            node = hou.node(node_path)
            if node is None:
                continue
            node_name = node.name()
            # 유효한 후디니 노드인지
            if not houdini_api.HoudiniAPI.is_valid_node(node=node):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='[{0}/{1}] "{2}" node cannot be registered. check the error message'.format(
                        node_cnt + 1, total_node_cnt, node_name
                    ),
                )
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
                if self.actionAutomatic_Name_Change.isChecked():
                    new_node_name = "{0}_{1}".format(
                        public.Name.hda_prefix_str.lower(), node_name
                    )
                    # 노드 이름 변경
                    node.setName(new_node_name, unique_name=True)
                    node_path = node.path()
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg='[{0}/{1}] (automatically rename) "{2}" >>>>> "{3}"'.format(
                            node_cnt + 1, total_node_cnt, node_name, new_node_name
                        ),
                    )
                else:
                    if not houdini_api.HoudiniAPI.is_valid_node_name(
                        node=node, verbose=True
                    ):
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg='[{0}/{1}] "{2}" node cannot be registered. check the error message'.format(
                                node_cnt + 1, total_node_cnt, node_name
                            ),
                        )
                        continue
                    # 현재 후디니버전 18.0.429 에서 노드이름이 _(언더바)/숫자로 처음 시작하게 되면 에러 발생한다. 그래서 아래 코드 추가함.
                    if (node_name.startswith("_")) or (node_name[0].isdigit()):
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg='[{0}/{1}] "{2}" _(underline) or numbers should not be in the first \
                            word of the node name. change the node name'.format(
                                node_cnt + 1, total_node_cnt, node_name
                            ),
                        )
                        continue
            node_cate = houdini_api.HoudiniAPI.node_category_type_name(node)
            is_done_node = self._node_declare(node=node, db_api=db_api)
            if not is_done_node:
                node.setName(node_name, unique_name=True)
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] "{2}" node DB input failed'.format(
                        node_cnt + 1, total_node_cnt, node_name
                    ),
                )
                continue
            self._add_category_item(category=node_cate)
            is_declare = True
            log_handler.LogHandler.log_msg(
                method=logging.debug,
                msg='[{0}/{1}] node dropped "{2}" ({3})'.format(
                    node_cnt + 1, total_node_cnt, node_path, node_cate
                ),
            )
        if is_declare:
            self._select_category(category=self._sel_item_text)
        self._dragdrop_overlay_close()

    def _node_declare(
        self, node: hou.Node | None = None, db_api: SQLite3DatabaseAPI | None = None
    ) -> bool:
        node_name = node.name()
        is_display_flag = None
        is_render_flag = None
        if hasattr(node, "isDisplayFlagSet"):
            is_display_flag = node.isDisplayFlagSet()
        if hasattr(node, "isRenderFlagSet"):
            is_render_flag = node.isRenderFlagSet()
        node_cate = houdini_api.HoudiniAPI.node_category_type_name(node)
        item_key_lst = [node_cate, node_name]
        is_exist_hda_name = db_api.is_exist_hda_name(
            user_id=self._user, category=node_cate, hda_name=node_name
        )
        self._sel_parent_lst = item_key_lst
        # 만약 등록하려는 Category의 HDA의 이름이 DB에 존재한다면,
        if is_exist_hda_name:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="{0} in the {1} category exists...".format(node_name, node_cate),
            )
            # 업데이트 할 것인지 물어 본 다음 업데이트 진행
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(self._get_default_font())
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setWindowTitle("Update iHDA Node")
            msgbox.setText(
                """
<font color=red size=5>{0}</font> the same name exists in the category<br>
<font color=red size=5>{1}</font> do you want to update iHDA node?""".format(
                    node_cate, node_name
                )
            )
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            reply = msgbox.exec()
            if reply == QtWidgets.QMessageBox.No:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="update has been canceled"
                )
                return False
            hda_key_id = db_api.get_hda_key_id(
                category=node_cate, name=node_name, user_id=self._user
            )
            if hda_key_id is None:
                return False
            hda_key_id = hda_key_id[0]
            # 업데이트하려는 노드가 저장되어있는 노드 타입과 같은지 확인
            hda_node_type = db_api.get_hda_node_type(hda_key_id=hda_key_id)
            if hda_node_type != houdini_api.HoudiniAPI.node_type_name(node):
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg="node you want to update is different from the node type stored in DB",
                )
                return False
            version = self._get_new_up_version(
                version=db_api.get_hda_version(hda_key_id=hda_key_id)
            )
            node_info_dict = self._node_info_data(
                key_lst=item_key_lst, node=node, version=version
            )
            if node_info_dict is None:
                return False
            # update 진행
            is_done_db = self._update_to_hda_db(
                info_data=node_info_dict, hda_key_id=hda_key_id, db_api=db_api
            )
        else:
            node_info_dict = self._node_info_data(
                key_lst=item_key_lst, node=node, version=public.Value.init_hda_version
            )
            if node_info_dict is None:
                return False
            is_done_db = self._insert_to_hda_db(info_data=node_info_dict, db_api=db_api)
        # DB 입력 실패면
        if not is_done_db:
            return False
        if is_display_flag is not None:
            node.setDisplayFlag(is_display_flag)
        if is_render_flag is not None:
            node.setRenderFlag(is_render_flag)
        return True

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
        get_node = node_info_dict.get(public.Key.node)
        get_hda_dirpath = node_info_dict.get(public.Key.hda_dirpath)
        get_hda_filename = node_info_dict.get(public.Key.hda_filename)
        get_hda_version = node_info_dict.get(public.Key.hda_version)
        assert isinstance(get_hda_dirpath, pathlib.Path)
        # hda_dirpath 경로에 HDA file 생성
        if not get_hda_dirpath.exists():
            get_hda_dirpath.mkdir(parents=True)
        is_houdini_api_file = houdini_api.HoudiniAPI.create_hda_file(
            node=get_node,
            hda_dirpath=get_hda_dirpath,
            hda_filename=get_hda_filename,
            hda_version=get_hda_version,
        )
        if not is_houdini_api_file:
            return None
        return node_info_dict

    def _get_hda_info(
        self,
        key_lst: list[str] | None = None,
        node: hou.Node | None = None,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        hda_dirpath = self._hda_base_dirpath.joinpath("/".join(key_lst))
        hda = houdini_api.HoudiniAPI(
            hda_version=version, node_path=node.path(), hda_dirpath=hda_dirpath
        )
        node_info_dict = hda.get_individual_hda_data()
        if not len(node_info_dict):
            return None
        return node_info_dict

    @staticmethod
    def _get_new_up_version(version: str | None = None) -> str:
        return str(Decimal(version) + Decimal("0.1"))

    def _update_to_hda_db(
        self,
        info_data: dict[str, Any] | None = None,
        hda_key_id: int | None = None,
        db_api: SQLite3DatabaseAPI | None = None,
    ) -> bool:
        node = info_data.get(public.Key.node)
        node_name = node.name()
        node_path = node.path()
        node_ver = info_data.get(public.Key.hda_version)
        hda_dirpath = info_data.get(public.Key.hda_dirpath)
        hda_filename = info_data.get(public.Key.hda_filename)
        type_path_lst = info_data.get(public.Key.node_type_path_list)
        cate_path_lst = info_data.get(public.Key.node_cate_path_list)
        type_name = info_data.get(public.Key.node_type_name)
        cate_name = info_data.get(public.Key.node_cate_name)
        def_desc = info_data.get(public.Key.node_def_desc)
        icon_path_lst = info_data.get(public.Key.node_icon_path_list)
        is_net = info_data.get(public.Key.is_network)
        is_sub_net = info_data.get(public.Key.is_sub_network)
        input_conn = info_data.get(public.Key.node_input_connections)
        output_conn = info_data.get(public.Key.node_output_connections)
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        declare_os = public.platform_system()
        assert isinstance(hda_dirpath, pathlib.Path)
        # thumbnail
        thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(
            hda_dirpath=hda_dirpath
        )
        thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(
            name=node_name, version=node_ver
        )
        thumb_filepath = thumb_dirpath / thumb_filename
        if not thumb_dirpath.exists():
            thumb_dirpath.mkdir(parents=True)
        houdini_api.HoudiniAPI.create_thumbnail(output_filepath=thumb_filepath)
        try:
            with db_api.transaction():
                is_hda_info = db_api.update_hda_info(
                    hda_key_id=hda_key_id,
                    version=node_ver,
                    filename=hda_filename,
                    dirpath=hda_dirpath,
                )
                is_icon_info = db_api.update_icon_info(
                    hda_key_id=hda_key_id, icon_lst=icon_path_lst
                )
                hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
                hip_dirpath = hip_filepath.parent
                hip_filename = hip_filepath.name
                assert isinstance(hip_filepath, pathlib.Path)
                frinfo = houdini_api.HoudiniAPI.frame_info()
                is_hipfile_info = db_api.update_hipfile_info(
                    hda_key_id=hda_key_id,
                    filename=hip_filepath.name,
                    dirpath=hip_filepath.parent,
                    houdini_version=hou_version,
                    hda_license=hou_license,
                    operating_system=declare_os,
                    sf=frinfo[0],
                    ef=frinfo[1],
                    fps=frinfo[2],
                )
                is_update_thumb = db_api.update_thumbnail_info(
                    hda_key_id=hda_key_id,
                    dirpath=thumb_dirpath,
                    filename=thumb_filename,
                    version=node_ver,
                )
                if is_update_thumb:
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg="thumbnail update complete"
                    )
                is_hou_node_info = db_api.update_houdini_node_info(
                    hda_key_id=hda_key_id, node_path=node_path
                )
                # houdini node info 테이블의 id
                info_id = db_api.get_hou_node_info_id(hda_key_id=hda_key_id)
                is_hou_node_cate_path_info = (
                    db_api.update_houdini_node_category_path_info(
                        info_id=info_id, node_category_lst=cate_path_lst
                    )
                )
                is_hou_node_type_path_info = db_api.update_houdini_node_type_path_info(
                    info_id=info_id, node_type_lst=type_path_lst
                )
                is_hou_node_input_connect_info = (
                    db_api.update_houdini_node_input_connect_info(
                        info_id=info_id, node_input_connect_lst=input_conn
                    )
                )
                is_hou_node_output_connect_info = (
                    db_api.update_houdini_node_output_connect_info(
                        info_id=info_id, node_output_connect_lst=output_conn
                    )
                )
                if (
                    (is_hda_info is None)
                    or (is_hou_node_info is None)
                    or (is_icon_info is None)
                    or (is_hou_node_cate_path_info is None)
                    or (is_hou_node_type_path_info is None)
                    or (is_hou_node_input_connect_info is None)
                    or (is_hou_node_output_connect_info is None)
                    or (is_hipfile_info is None)
                ):
                    raise sqlite3.DatabaseError("Incomplete asset update")
                # ihda_data변수에 db데이터를 한번 읽어들여 그것을 운용하는 방식으로
                # 변경해야 할 데이터: is_favorite_hda, hda_load_count, hda_ctime, hda_tags
                key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_info_key_lst()
                before_data = db_api.get_update_before_data(hda_key_id=hda_key_id)
                is_favorite_hda = before_data.get(public.Key.is_favorite_hda)
                hda_load_count = before_data.get(public.Key.hda_load_count)
                hda_ctime = before_data.get(public.Key.hda_ctime)
                hda_tags = before_data.get(public.Key.hda_tags)
                video_dirpath = before_data.get(public.Key.video_dirpath)
                video_filename = before_data.get(public.Key.video_filename)
                hda_note = before_data.get(public.Key.hda_note)
                val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
                val_lst = [
                    hda_key_id,
                    node_name,
                    cate_name,
                    node_ver,
                    hda_filename,
                    hda_dirpath,
                    is_favorite_hda,
                    hda_load_count,
                    hda_ctime,
                    val_datetime,
                    hou_version,
                    type_name,
                    def_desc,
                    is_net,
                    is_sub_net,
                    node_path,
                    hou_license,
                    hip_filename,
                    hip_dirpath,
                    thumb_filename,
                    thumb_dirpath,
                    video_filename,
                    video_dirpath,
                    hda_note,
                    icon_path_lst,
                    hda_tags,
                ]
                assert len(key_lst) == len(val_lst)
                dat = dict(zip(key_lst, val_lst))
                # history
                hist_data = [
                    hda_key_id,
                    "NODE (UPDATE)",
                    node_name,
                    node_ver,
                    hda_filename,
                    hda_dirpath,
                    val_datetime,
                    hou_version,
                    hip_filename,
                    hip_dirpath,
                    hou_license,
                    declare_os,
                    node_path,
                    def_desc,
                    type_name,
                    cate_name,
                    self._user,
                    icon_path_lst,
                    thumb_filename,
                    thumb_dirpath,
                    video_filename,
                    video_dirpath,
                ]
                is_hda_history = db_api.insert_hda_history(data=hist_data)
                if is_hda_history is None:
                    raise sqlite3.DatabaseError("Could not write asset history")
                # 추가 된 hda key의 id 반환
                last_hda_hist_id = db_api.get_last_insert_id
        except sqlite3.Error as error:
            logging.error("Asset update rolled back: %s", error)
            return False
        self._update_pixmap_thumbnail(hkey_id=hda_key_id, thumb_filepath=thumb_filepath)
        hda_id_row_map = self._get_hda_id_row_map()
        self._update_item_row_data(row=hda_id_row_map.get(hda_key_id), row_data=dat)
        # hist_id & tag 추가
        self._add_pixmap_hist_thumbnail(
            hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath
        )
        self._insert_ihda_history_data_model(
            data=hist_data, hist_id=last_hda_hist_id, tags=hda_tags
        )
        # history combobox 아이템 추가
        self._set_hist_ihda_to_combobox(hkey_id=hda_key_id, hda_name=node_name)
        return True

    def _insert_to_hda_db(
        self,
        info_data: dict[str, Any] | None = None,
        db_api: SQLite3DatabaseAPI | None = None,
    ) -> bool:
        node = info_data.get(public.Key.node)
        node_name = node.name()
        node_path = node.path()
        node_ver = info_data.get(public.Key.hda_version)
        hda_dirpath = info_data.get(public.Key.hda_dirpath)
        hda_filename = info_data.get(public.Key.hda_filename)
        type_path_lst = info_data.get(public.Key.node_type_path_list)
        cate_path_lst = info_data.get(public.Key.node_cate_path_list)
        type_name = info_data.get(public.Key.node_type_name)
        cate_name = info_data.get(public.Key.node_cate_name)
        def_desc = info_data.get(public.Key.node_def_desc)
        icon_path_lst = info_data.get(public.Key.node_icon_path_list)
        is_net = info_data.get(public.Key.is_network)
        is_sub_net = info_data.get(public.Key.is_sub_network)
        input_conn = info_data.get(public.Key.node_input_connections)
        output_conn = info_data.get(public.Key.node_output_connections)
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        declare_os = public.platform_system()
        assert isinstance(hda_dirpath, pathlib.Path)
        # thumbnail
        thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(
            hda_dirpath=hda_dirpath
        )
        thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(
            name=node_name, version=node_ver
        )
        thumb_filepath = thumb_dirpath / thumb_filename
        if not thumb_dirpath.exists():
            thumb_dirpath.mkdir(parents=True)
        houdini_api.HoudiniAPI.create_thumbnail(output_filepath=thumb_filepath)
        # insert db
        try:
            with db_api.transaction():
                is_hda_cate = db_api.insert_hda_category(
                    category=cate_name, user_id=self._user
                )
                if is_hda_cate is None:
                    raise sqlite3.DatabaseError("Could not create asset category")
                if not db_api.insert_hda_key(
                    name=node_name, category=cate_name, user_id=self._user
                ):
                    raise sqlite3.DatabaseError("Could not create asset key")
                # 추가 된 hda key의 id 반환
                last_hda_key_id = db_api.get_last_insert_id
                is_hda_info = db_api.insert_hda_info(
                    hda_key_id=last_hda_key_id,
                    version=node_ver,
                    is_favorite=False,
                    load_count=0,
                    filename=hda_filename,
                    dirpath=hda_dirpath,
                )
                is_icon_info = db_api.insert_icon_info(
                    hda_key_id=last_hda_key_id, icon_lst=icon_path_lst
                )
                hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
                hip_filename = hip_filepath.name
                hip_dirpath = hip_filepath.parent
                assert isinstance(hip_filepath, pathlib.Path)
                frinfo = houdini_api.HoudiniAPI.frame_info()
                is_hipfile_info = db_api.insert_hipfile_info(
                    hda_key_id=last_hda_key_id,
                    filename=hip_filename,
                    dirpath=hip_dirpath,
                    houdini_version=hou_version,
                    hda_license=hou_license,
                    operating_system=declare_os,
                    sf=frinfo[0],
                    ef=frinfo[1],
                    fps=frinfo[2],
                )
                is_insert_thumb = db_api.insert_thumbnail_info(
                    hda_key_id=last_hda_key_id,
                    dirpath=thumb_dirpath,
                    filename=thumb_filename,
                    version=node_ver,
                )
                if is_insert_thumb:
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg="finished creating thumbnails"
                    )
                else:
                    ihda_system.IHDASystem.remove_dir(
                        dirpath=thumb_dirpath, verbose=False
                    )
                is_hou_node_info = db_api.insert_houdini_node_info(
                    hda_key_id=last_hda_key_id,
                    type_name=type_name,
                    def_desc=def_desc,
                    is_net=is_net,
                    is_sub_net=is_sub_net,
                    old_path=node_path,
                )
                # 추가 된 houdini node info의 id 반환
                last_hou_node_info_id = db_api.get_last_insert_id
                is_hou_node_cate_path_info = (
                    db_api.insert_houdini_node_category_path_info(
                        info_id=last_hou_node_info_id, node_category_lst=cate_path_lst
                    )
                )
                is_hou_node_type_path_info = db_api.insert_houdini_node_type_path_info(
                    info_id=last_hou_node_info_id, node_type_lst=type_path_lst
                )
                is_hou_node_input_conn_info = (
                    db_api.insert_houdini_node_input_connect_info(
                        info_id=last_hou_node_info_id, node_input_connect_lst=input_conn
                    )
                )
                is_hou_node_output_conn_info = (
                    db_api.insert_houdini_node_output_connect_info(
                        info_id=last_hou_node_info_id,
                        node_output_connect_lst=output_conn,
                    )
                )
                val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
                # history
                hist_data = [
                    last_hda_key_id,
                    "NODE (INSERT)",
                    node_name,
                    node_ver,
                    hda_filename,
                    hda_dirpath,
                    val_datetime,
                    hou_version,
                    hip_filename,
                    hip_dirpath,
                    hou_license,
                    declare_os,
                    node_path,
                    def_desc,
                    type_name,
                    cate_name,
                    self._user,
                    icon_path_lst,
                    thumb_filename,
                    thumb_dirpath,
                    None,
                    None,
                ]
                is_hda_history = db_api.insert_hda_history(data=hist_data)
                # 추가 된 hda history의 id 반환
                last_hda_hist_id = db_api.get_last_insert_id
                if (
                    (is_hda_info is None)
                    or (is_icon_info is None)
                    or (is_hou_node_info is None)
                    or (is_hou_node_cate_path_info is None)
                    or (is_hou_node_type_path_info is None)
                    or (is_hou_node_input_conn_info is None)
                    or (is_hou_node_output_conn_info is None)
                    or (is_hipfile_info is None)
                    or (is_hda_history is None)
                ):
                    raise sqlite3.DatabaseError("Incomplete asset registration")
        except sqlite3.Error as error:
            logging.error("Asset registration rolled back: %s", error)
            return False
        self._add_pixmap_ihda(hkey_id=last_hda_key_id, icon_lst=icon_path_lst)
        self._add_pixmap_thumbnail(
            hkey_id=last_hda_key_id, thumb_filepath=thumb_filepath
        )
        self._add_pixmap_hist_thumbnail(
            hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath
        )
        # ihda_data변수에 db데이터를 한번 읽어들여 그것을 운용하는 방식으로
        # sqlite3_db_api get_hda_data와 맞춰야 한다.
        val_lst = [
            last_hda_key_id,
            node_name,
            cate_name,
            node_ver,
            hda_filename,
            hda_dirpath,
            0,
            0,
            val_datetime,
            val_datetime,
            hou_version,
            type_name,
            def_desc,
            is_net,
            is_sub_net,
            node_path,
            hou_license,
            hip_filename,
            hip_dirpath,
            thumb_filename,
            thumb_dirpath,
            None,
            None,
            None,
            icon_path_lst,
            list(),
        ]
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_info_key_lst()
        assert len(key_lst) == len(val_lst)
        dat = dict(zip(key_lst, val_lst))
        self._insert_ihda_data_model(data=dat)
        self._refresh_asset_search()
        self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self._get_category_count()))
        # history 모델에 아이템 add
        # hist_id & tag 추가
        self._insert_ihda_history_data_model(
            data=hist_data, hist_id=last_hda_hist_id, tags=list()
        )
        # history combobox 아이템 추가
        self._set_hist_ihda_to_combobox(hkey_id=last_hda_key_id, hda_name=node_name)
        # 후디니 노드에 코멘트 추가
        self._hda_info_to_node_comment(
            node=node, hda_name=node_name, hda_ver=node_ver, hda_id=last_hda_key_id
        )
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="comments have been added to existing Houdini node(s)",
        )
        return True
