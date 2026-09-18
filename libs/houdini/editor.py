"""Network editor access: panes, cursor, selection, navigation.

Only libs.houdini_api and this package import hou.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any

from libs.host import IS_HOUDINI

with suppress(ImportError):
    import hou

try:
    import hdefereval
except ImportError:  # not hosted by Houdini
    hdefereval = None


def pane_tab_under_cursor() -> Any | None:
    if not IS_HOUDINI:
        return None
    return hou.ui.curDesktop().paneTabUnderCursor()


def network_editor() -> Any | None:
    if not IS_HOUDINI:
        return None
    return hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)


def add_selection_callback(func: Callable[..., Any]) -> None:
    if IS_HOUDINI and func not in hou.ui.selectionCallbacks():
        hou.ui.addSelectionCallback(func)


def remove_selection_callback(func: Callable[..., Any]) -> None:
    if IS_HOUDINI and func in hou.ui.selectionCallbacks():
        hou.ui.removeSelectionCallback(func)


def has_selection_callback(func: Callable[..., Any]) -> bool:
    return bool(IS_HOUDINI and func in hou.ui.selectionCallbacks())


def items_position(items: Any = ()) -> hou.Vector2:
    pos = hou.Vector2(0, 0)
    num = 0
    for item in items:
        if isinstance(item, hou.SubnetIndirectInput):
            continue
        pos += item.position()
        num += 1
    if num:
        pos /= num
    return pos + hou.Vector2(-5, 0)


def current_network_editor_type_name(
    network_editor: hou.NetworkEditor | None = None,
    not_have_null_node_context_lst: Any = None,
) -> str | None:
    """Read the network category without creating temporary scene nodes."""
    if network_editor is None or isinstance(network_editor, hou.PythonPanel):
        return None
    try:
        category = network_editor.pwd().childTypeCategory()
        return category.typeName().lower() if category is not None else None
    except (AttributeError, hou.ObjectWasDeleted, hou.OperationFailed):
        return None


def find_network_editor() -> hou.NetworkEditor | None:
    for pane_tab in hou.ui.currentPaneTabs():
        if hou.paneTabType.NetworkEditor != pane_tab.type():
            continue
        try:
            node = pane_tab.currentNode()
            if node.isSelected():
                return pane_tab
        except AttributeError:
            pass
    return hou.ui.curDesktop().paneTabOfType(hou.paneTabType.NetworkEditor)


def find_network_editor_by_cursor() -> hou.NetworkEditor | None:
    desk = hou.ui.curDesktop()
    cur_pane_tab = desk.paneTabUnderCursor()
    try:
        if hou.paneTabType.NetworkEditor != cur_pane_tab.type():
            return None
    except AttributeError:
        return None
    return cur_pane_tab


def get_cursor_pos(
    network_editor: hou.NetworkEditor | None = None,
) -> hou.Vector2 | None:
    if network_editor is None:
        return None
    return network_editor.cursorPosition()


def get_selected_nodes() -> tuple[hou.Node, ...] | None:
    nodes = hou.selectedNodes()
    if len(nodes):
        return nodes
    return None


def all_clear_selected(node: hou.Node | None = None) -> None:
    if node is None:
        return
    node.setSelected(False, clear_all_selected=True)


def go_to_node(node: hou.Node | None = None) -> None:
    if node is None:
        return
    node.setSelected(True, clear_all_selected=True)
    network_editor = find_network_editor()
    if network_editor is None:
        return
    network_editor.setIsCurrentTab()
    network_editor.setPwd(node.parent())
    network_editor.homeToSelection()
