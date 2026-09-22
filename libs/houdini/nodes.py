"""Node inspection and editing: types, categories, connections, comments, network boxes.

Only libs.houdini_api and this package import hou.
"""

from __future__ import annotations

import logging
import math
from contextlib import suppress
from typing import Any

from libs import keys, log_handler, paths
from libs.asset_contracts import NodeConnection
from libs.host import IS_HOUDINI
from libs.houdini import session

with suppress(ImportError):
    import hou

try:
    import hdefereval
except ImportError:  # not hosted by Houdini
    hdefereval = None


def find_node(path: str | None) -> hou.Node | None:
    if not IS_HOUDINI or path is None:
        return None
    return hou.node(path)


def node_type_name(node: hou.Node | None) -> str | None:
    if node is None:
        return None
    return node.type().name()


def node_category_type_name(node: hou.Node | None) -> str | None:
    if node is None:
        return None
    # 원래 대문자로 나오지만, 소문자로 바꿈.
    return node.type().category().typeName().lower()


def _node_type_path_list(node: hou.Node | None) -> list[str]:
    if node is None:
        return []
    node_type_lst = []
    node_type_lst.append(node_type_name(node) or "")
    return _node_type_path_list(node.parent()) + node_type_lst


def _node_category_path_list(node: hou.Node | None) -> list[str]:
    if node is None:
        return []
    node_category_lst = []
    node_category_lst.append(node_category_type_name(node) or "")
    return _node_category_path_list(node.parent()) + node_category_lst


def _node_type_description(node: hou.Node | None) -> str | None:
    if node is None:
        return None
    return node.type().description()


def node_definition_description(node: hou.Node | None) -> str | None:
    if node is None:
        return None
    node_type = node.type()
    try:
        return node_type.definition().description()
    except AttributeError:
        return node_type.description()


def node_icon_path_lst(node: hou.Node | None) -> list[str] | None:
    if node is None:
        return None
    try:
        if (
            keys.Name.company_initial
            in (node_definition_description(node) or "").lower()
        ):
            return [
                keys.Name.company_icon_dirname,
                keys.Name.company_log_icon_filename,
            ]
        icon = node.type().definition().icon().strip()
        if icon == "":
            icon = node.type().icon().strip()
    except AttributeError:
        icon = node.type().icon().strip()
    icon_lst = icon.split("_", 1)
    find_idx = icon_lst[1].find("-")
    if find_idx >= 0:
        icon_lst[1] = icon_lst[1][:find_idx]
    return icon_lst


def _is_network_node(node: hou.Node | None) -> bool | None:
    if node is None:
        return None
    return node.isNetwork()


def _is_sub_network_node(node: hou.Node | None) -> bool | None:
    if node is None:
        return None
    return node.isSubNetwork()


def _is_shop_network(node: hou.Node | None = None) -> bool:
    return bool(node_category_type_name(node) == keys.Type.shop)


def _is_vop_network(node: hou.Node | None = None) -> bool:
    return bool(node_category_type_name(node) == keys.Type.vop)


def is_root_network(node: hou.Node | None = None) -> bool:
    return bool(node_type_name(node) == keys.Type.root)


def is_subnet_nodetype(node: hou.Node | None = None) -> bool:
    return bool(node_type_name(node) == keys.Type.subnet_node)


def _set_node_general_connections(
    connections: Any = None, target_node: hou.Node | None = None
) -> None:
    if connections is None:
        return
    for connect in connections:
        input_idx = connect.inputItemOutputIndex()
        input_node = connect.inputNode()
        cur_idx = connect.inputIndex()
        cur_node = connect.outputNode()
        if target_node is not None:
            cur_node = target_node
        cur_node.setInput(cur_idx, input_node, input_idx)


def _get_node_input_connections_lst(node: hou.Node) -> list[Any]:
    conn_lst = []
    for connect in node.inputConnections():
        conn_node = connect.inputNode()
        if conn_node is None:
            continue
        conn_idx = connect.inputItemOutputIndex()
        cur_idx = connect.inputIndex()
        conn_lst.append(
            NodeConnection(
                port=cur_idx,
                node_name=conn_node.name(),
                node_type=conn_node.type().name(),
                peer_port=conn_idx,
            )
        )
    return conn_lst


def _get_node_output_connections_lst(node: hou.Node) -> list[Any]:
    conn_lst = []
    for connect in node.outputConnections():
        conn_node = connect.outputNode()
        if conn_node is None:
            continue
        cur_idx = connect.inputItemOutputIndex()
        conn_idx = connect.inputIndex()
        conn_lst.append(
            NodeConnection(
                port=cur_idx,
                node_name=conn_node.name(),
                node_type=conn_node.type().name(),
                peer_port=conn_idx,
            )
        )
    return conn_lst


def set_node_input_connections(
    node: hou.Node | None = None, connection_lst: Any = None
) -> None:
    if node is None:
        return
    if connection_lst is None:
        return
    if not len(connection_lst):
        return
    child_type_dict = _get_child_type_by_name_dict(node)
    child_node_name_lst = list(child_type_dict.keys())
    with hou.undos.group(session.UNDO_NAME_IMPORT_IHDA):
        for conn_info in connection_lst:
            node_idx = conn_info.port
            conn_node_name = conn_info.node_name
            conn_node_type = conn_info.node_type
            conn_node_idx = conn_info.peer_port
            if conn_node_name in child_node_name_lst:
                if conn_node_type == child_type_dict.get(conn_node_name):
                    conn_node = hou.node(
                        node.parent().path()
                        + paths.Paths.houdini_path_sep
                        + conn_node_name
                    )
                    node.setInput(int(node_idx), conn_node, int(conn_node_idx))


def set_node_output_connections(
    node: hou.Node | None = None, connection_lst: Any = None
) -> None:
    if node is None:
        return
    if connection_lst is None:
        return
    if not len(connection_lst):
        return
    child_type_dict = _get_child_type_by_name_dict(node)
    child_node_name_lst = list(child_type_dict.keys())
    with hou.undos.group(session.UNDO_NAME_IMPORT_IHDA):
        for conn_info in connection_lst:
            node_idx = conn_info.port
            conn_node_name = conn_info.node_name
            conn_node_type = conn_info.node_type
            conn_node_idx = conn_info.peer_port
            if conn_node_name in child_node_name_lst:
                if conn_node_type == child_type_dict.get(conn_node_name):
                    conn_node = hou.node(
                        node.parent().path()
                        + paths.Paths.houdini_path_sep
                        + conn_node_name
                    )
                    conn_node.setInput(int(conn_node_idx), node, int(node_idx))


def _get_child_type_by_name_dict(node: hou.Node) -> dict[str, Any]:
    parent_node = node.parent()
    d = {}
    for child in parent_node.children():
        d[child.name()] = child.type().name()
    return d


def _get_between_node_length(node1: hou.Node, node2: hou.Node) -> float:
    sub = node1.position() - node2.position()
    return math.sqrt(math.pow(sub.x(), 2) + math.pow(sub.y(), 2))


def is_valid_node(node: hou.Node | None = None) -> bool:
    if node is None:
        return False
    if _is_shop_network(node=node):
        if _is_sub_network_node(node):
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="subnet node is not supported in the SHOP network",
            )
            return False
    if _is_vop_network(node=node):
        node_descript = node_definition_description(node)
        node_type = node_type_name(node) or ""
        is_descript = node_descript in keys.InvalidNode.node_descript_list
        is_type = node_type in keys.InvalidNode.node_type_list
        if is_descript or is_type:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg=f'node "{node.name()}" cannot be registered because it is of type "{node_descript}"',
            )
            return False
    if hasattr(node, "inputs") and len(node.inputs()) >= 5:
        log_handler.LogHandler.log_msg(
            method=logging.error,
            msg=f'"{node.name()}" nodes have more than five inputs',
        )
        return False
    return True


def is_valid_node_name(node: hou.Node | None = None, verbose: bool = True) -> bool:
    """
    노드 이름이 유효한 이름인지
    :param node: Houdini Node Instance
    :param verbose: Display Error Message
    :return: Bool
    """
    if node is None:
        return False
    node_name = node.name()
    node_type = node_type_name(node) or ""
    if node_type.find(":") >= 0:
        node_type = node_type.split(":")[0].strip()
    if node_name == node_type:
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg=f'the name "{node_name}" is the same as the current node type',
            )
        return False
    wrong_name = f"{node_type}1"
    if node_name == wrong_name:
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg=f'"{node_name}" is a name that can cause errors in Houdini',
            )
        return False
    return True


def _hide_parms(node: hou.Node | None = None) -> None:
    if node is None:
        return
    group = node.parmTemplateGroup()
    for parm in group.entries():
        group.hideFolder(parm.label(), True)
    node.setParmTemplateGroup(group)


def set_node_comment(
    node: hou.Node | None = None,
    contents: str = "",
    show_comments: bool = False,
    is_unpack_subnet: bool = False,
) -> None:
    if node is None:
        return
    if not len(contents):
        return
    with hou.undos.disabler():
        if hasattr(node, "setComment") and hasattr(node, "setGenericFlag"):
            node.setComment(contents)
            node.setGenericFlag(hou.nodeFlag.DisplayComment, show_comments)
        if is_subnet_nodetype(node=node) and is_unpack_subnet:
            for child in node.children():
                if hasattr(child, "setComment") and hasattr(child, "setGenericFlag"):
                    child.setComment(contents)
                    child.setGenericFlag(hou.nodeFlag.DisplayComment, show_comments)


def get_node_comment(node: hou.Node | None = None) -> None | str:
    if node is None:
        return None
    if not hasattr(node, "comment"):
        return None
    comment = node.comment()
    if (not len(comment)) or (comment is None):
        return None
    return comment.strip()


def get_node_datetime(node: hou.Node | None = None) -> tuple[Any, Any]:
    if node is None:
        raise ValueError("A node is required")
    return node.creationTime(), node.modificationTime()


def create_sticky_note(
    node: hou.Node | None = None, contents: str = ""
) -> hou.StickyNote | None:
    if node is None:
        return None
    if not len(contents):
        return None
    with hou.undos.disabler():
        sticky = node.createStickyNote(keys.Name.hda_prefix_str)
        sticky.setText(contents)
        sticky.setTextSize(0.35)
        sticky.setTextColor(hou.Color(0.85, 0.85, 0.85))
        # sticky.resize(sticky.size())
        sticky.setColor(hou.Color(0.1, 0.8, 0.45))
        sticky.setDrawBackground(False)
        return sticky


def create_network_box(
    node: hou.Node | None = None, comment: str | None = "", items: Any = ()
) -> hou.NetworkBox | None:
    if node is None:
        return None
    with hou.undos.disabler():
        if len(items):
            net_box = node.createNetworkBox()
            for item in items:
                if isinstance(item, hou.SubnetIndirectInput):
                    continue
                net_box.addItem(item)
        else:
            items = node.allItems()
            net_box = node.createNetworkBox()
            for item in items:
                if isinstance(item, hou.SubnetIndirectInput):
                    continue
                net_box.addItem(item)
        net_box.setColor(hou.Color(0.3, 0.3, 0.3))
        net_box.fitAroundContents()
        padding = hou.Vector2(1, 1)
        bbox = hou.BoundingRect(
            net_box.position()[0] - padding[0],
            net_box.position()[1] - padding[1],
            net_box.position()[0] + net_box.size()[0] + padding[0],
            net_box.position()[1] + net_box.size()[1] + padding[1],
        )
        net_box.setBounds(bbox)
        net_box.setComment(comment)
        return net_box


def parse_ihda_comment(comment: str | None) -> None | dict[str, Any]:
    """The iHDA identity written into a node comment, or None.

    The panel writes three ``key: value`` lines; users may add anything else
    (notes with colons, blank lines). Only the three known keys are read, each
    from its first colon, so extra text never breaks the scan. A missing or
    non-numeric ID means the node is not an iHDA instance.
    """
    if not comment:
        return None
    wanted = {
        keys.Key.Comment.ihda_name,
        keys.Key.Comment.ihda_version,
        keys.Key.Comment.ihda_id,
    }
    found: dict[str, Any] = {}
    for line in comment.splitlines():
        key, separator, value = line.partition(":")
        key = key.strip()
        if separator and key in wanted and key not in found:
            found[key] = value.strip()
    if keys.Key.Comment.ihda_id not in found:
        return None
    try:
        found[keys.Key.Comment.ihda_id] = int(found[keys.Key.Comment.ihda_id])
    except ValueError:
        return None
    found.setdefault(keys.Key.Comment.ihda_name, "")
    found.setdefault(keys.Key.Comment.ihda_version, "")
    return found


def get_hda_info_by_selection_node(
    node: hou.Node | None = None,
) -> None | dict[str, Any]:
    return parse_ihda_comment(get_node_comment(node=node))
