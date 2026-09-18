#!/usr/bin/env python
from __future__ import annotations

import logging
import pathlib

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 02:34
# modify date       :
# description       :
from contextlib import suppress
from typing import Any

from libs import keys, log_handler
from libs.houdini import assets, editor, nodes, session

with suppress(ImportError):
    import hou

try:
    import hdefereval
except ImportError:  # not hosted by Houdini
    hdefereval = None


# (2020.03.14): hda_dirpath 파라미터의 들어오는 값은 pathlib.Path 객체이다.


class HoudiniAPI:
    """One registered node's HDA facts, plus the host functions as static aliases.

    The functions live in libs.houdini.{session,nodes,editor,assets}; the aliases
    keep every caller and test patch (HoudiniAPI.name) working.
    """

    main_window = staticmethod(session.main_window)
    help_server_url = staticmethod(session.help_server_url)
    qt_library_dirpath = staticmethod(session.qt_library_dirpath)
    host_stylesheet = staticmethod(session.host_stylesheet)
    host_icon = staticmethod(session.host_icon)
    scaled_size = staticmethod(session.scaled_size)
    global_scale_factor = staticmethod(session.global_scale_factor)
    undo_group = staticmethod(session.undo_group)
    execute_deferred = staticmethod(session.execute_deferred)
    add_event_loop_callback = staticmethod(session.add_event_loop_callback)
    remove_event_loop_callback = staticmethod(session.remove_event_loop_callback)
    has_event_loop_callback = staticmethod(session.has_event_loop_callback)
    current_hipfile = staticmethod(session.current_hipfile)
    current_houdini_version = staticmethod(session.current_houdini_version)
    current_houdini_license = staticmethod(session.current_houdini_license)
    commercial_license = staticmethod(session.commercial_license)
    is_houdini_commercial_license = staticmethod(session.is_houdini_commercial_license)
    frame_info = staticmethod(session.frame_info)
    vector2 = staticmethod(session.vector2)
    find_node = staticmethod(nodes.find_node)
    node_type_name = staticmethod(nodes.node_type_name)
    node_category_type_name = staticmethod(nodes.node_category_type_name)
    node_definition_description = staticmethod(nodes.node_definition_description)
    node_icon_path_lst = staticmethod(nodes.node_icon_path_lst)
    is_root_network = staticmethod(nodes.is_root_network)
    is_subnet_nodetype = staticmethod(nodes.is_subnet_nodetype)
    set_node_input_connections = staticmethod(nodes.set_node_input_connections)
    set_node_output_connections = staticmethod(nodes.set_node_output_connections)
    is_valid_node = staticmethod(nodes.is_valid_node)
    is_valid_node_name = staticmethod(nodes.is_valid_node_name)
    set_node_comment = staticmethod(nodes.set_node_comment)
    get_node_comment = staticmethod(nodes.get_node_comment)
    get_node_datetime = staticmethod(nodes.get_node_datetime)
    create_sticky_note = staticmethod(nodes.create_sticky_note)
    create_network_box = staticmethod(nodes.create_network_box)
    get_hda_info_by_selection_node = staticmethod(nodes.get_hda_info_by_selection_node)
    pane_tab_under_cursor = staticmethod(editor.pane_tab_under_cursor)
    network_editor = staticmethod(editor.network_editor)
    add_selection_callback = staticmethod(editor.add_selection_callback)
    remove_selection_callback = staticmethod(editor.remove_selection_callback)
    has_selection_callback = staticmethod(editor.has_selection_callback)
    items_position = staticmethod(editor.items_position)
    current_network_editor_type_name = staticmethod(
        editor.current_network_editor_type_name
    )
    find_network_editor = staticmethod(editor.find_network_editor)
    find_network_editor_by_cursor = staticmethod(editor.find_network_editor_by_cursor)
    get_cursor_pos = staticmethod(editor.get_cursor_pos)
    get_selected_nodes = staticmethod(editor.get_selected_nodes)
    all_clear_selected = staticmethod(editor.all_clear_selected)
    go_to_node = staticmethod(editor.go_to_node)
    hda_definitions_in_file = staticmethod(assets.hda_definitions_in_file)
    hda_expand_to_directory = staticmethod(assets.hda_expand_to_directory)
    make_hda_filename = staticmethod(assets.make_hda_filename)
    make_thumbnail_filename = staticmethod(assets.make_thumbnail_filename)
    make_thumbnail_dirpath = staticmethod(assets.make_thumbnail_dirpath)
    make_preview_filename = staticmethod(assets.make_preview_filename)
    make_preview_dirpath = staticmethod(assets.make_preview_dirpath)
    make_video_filename = staticmethod(assets.make_video_filename)
    make_video_dirpath = staticmethod(assets.make_video_dirpath)
    create_hda_file = staticmethod(assets.create_hda_file)
    create_thumbnail = staticmethod(assets.create_thumbnail)
    create_preview = staticmethod(assets.create_preview)
    clean_hda_library = staticmethod(assets.clean_hda_library)
    import_individual_hda_into_houdini = staticmethod(
        assets.import_individual_hda_into_houdini
    )
    get_ihda_node_instance_data = staticmethod(assets.get_ihda_node_instance_data)
    get_ihda_node_instance_nested_list = staticmethod(
        assets.get_ihda_node_instance_nested_list
    )

    def __init__(
        self,
        hda_version: str = "1.0",
        node_path: str | None = None,
        hda_dirpath: pathlib.Path | None = None,
    ) -> None:
        assert isinstance(hda_dirpath, pathlib.Path)
        self.__hda_version = hda_version
        self.__node_path = node_path
        if node_path is None:
            raise ValueError("A node path is required")
        self.__node = hou.node(self.__node_path)
        self.__hda_dirpath = hda_dirpath
        self.__hda_filename: str | None = None
        self.__hda_filepath: pathlib.Path | None = None
        if self.__node is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="node does not exist"
            )
            return
        self.__hda_dirpath = hda_dirpath
        self.__hda_filename = None
        self.__hda_filepath = None

    @property
    def node(self) -> hou.Node | None:
        return self.__node

    @property
    def hda_version(self) -> str:
        return self.__hda_version

    @property
    def hda_dirpath(self) -> pathlib.Path | None:
        return self.__hda_dirpath

    @property
    def hda_filename(self) -> str | None:
        return self.__hda_filename

    @hda_filename.setter
    def hda_filename(self, val: Any) -> None:
        self.__hda_filename = val

    @property
    def hda_filepath(self) -> pathlib.Path | None:
        return self.__hda_filepath

    @hda_filepath.setter
    def hda_filepath(self, val: Any) -> None:
        self.__hda_filepath = val

    def get_individual_hda_data(self) -> dict[str, Any]:
        node = self.node
        if node is None:
            raise ValueError("Node no longer exists")
        filename = assets.make_hda_filename(
            name=node.name(), version=self.hda_version, with_suffix=True
        )
        self.hda_filename = filename
        self.hda_filepath = self.__hda_dirpath / filename
        return self.__info_dict_individual_node(node=self.node)

    def __info_dict_individual_node(
        self, node: hou.Node | None = None
    ) -> dict[str, Any]:
        d = {}
        # houdini node instance
        d[keys.Key.node] = node
        # houdini hda version
        d[keys.Key.hda_version] = self.hda_version
        # hda dirpath
        d[keys.Key.hda_dirpath] = self.hda_dirpath
        # hda file name
        d[keys.Key.hda_filename] = self.hda_filename
        # node type path list
        d[keys.Key.node_type_path_list] = nodes._node_type_path_list(node)
        # node category path list
        d[keys.Key.node_cate_path_list] = nodes._node_category_path_list(node)
        # node type name
        d[keys.Key.node_type_name] = nodes.node_type_name(node)
        # node category type name
        d[keys.Key.node_cate_name] = nodes.node_category_type_name(node)
        # node definition description
        d[keys.Key.node_def_desc] = nodes.node_definition_description(node)
        # node icon path list
        d[keys.Key.node_icon_path_list] = nodes.node_icon_path_lst(node)
        # node is network
        d[keys.Key.is_network] = nodes._is_network_node(node)
        # node is sub network
        d[keys.Key.is_sub_network] = nodes._is_sub_network_node(node)
        # node input connections
        d[keys.Key.node_input_connections] = nodes._get_node_input_connections_lst(node)
        # node output connections
        d[keys.Key.node_output_connections] = nodes._get_node_output_connections_lst(
            node
        )
        return d
