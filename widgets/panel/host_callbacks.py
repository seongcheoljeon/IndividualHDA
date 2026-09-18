"""Host callbacks for the Houdini panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore

from libs import keys, log_handler
from libs.host_ports import HostCallbacksPort

if TYPE_CHECKING:
    import hou

    from widgets.panel.ports import SelectionPort


from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.state import PanelStatus


@dataclass(frozen=True, slots=True)
class PanelHostCallbacksBindings:
    host: HostCallbacksPort
    enabled: bool
    contexts_without_null: list[str]
    selection: SelectionPort
    status: PanelStatus
    ui: MainWindowLayout


class PanelHostCallbacks:
    bindings: PanelHostCallbacksBindings

    def add_event_loop_callback(self, event_func: Callable[..., Any]) -> None:
        self.bindings.host.add_event_loop_callback(event_func)

    def _add_selection_callback(self, event_func: Callable[..., Any]) -> None:
        self.bindings.host.add_selection_callback(event_func)

    def remove_event_loop_callback(self, event_func: Callable[..., Any]) -> None:
        self.bindings.host.remove_event_loop_callback(event_func)

    def _remove_selection_callback(self, event_func: Callable[..., Any]) -> None:
        self.bindings.host.remove_selection_callback(event_func)

    def _slot_stackedwidget_whole_curt_changed(self, index: QtCore.QModelIndex) -> None:
        # 만약 iHDA 뷰가 아닌데 category synchronize가 활성화 상태면, 이벤트 콜백 삭제
        if (
            index
            != self.bindings.ui.stackedWidget__whole.indexOf(
                self.bindings.ui.page__ihda
            )
        ) and (self.bindings.ui.actionCategory_Synchronization.isChecked()):
            self.remove_event_loop_callback(self._wrapper_current_panetab)
        else:
            if self.bindings.ui.actionCategory_Synchronization.isChecked():
                self.add_event_loop_callback(self._wrapper_current_panetab)

    def _slot_sync_hou_net_cate(self) -> None:
        if not self.bindings.enabled:
            return
        if self.bindings.ui.actionCategory_Synchronization.isChecked():
            if (
                self.bindings.ui.stackedWidget__whole.currentIndex()
                == self.bindings.ui.stackedWidget__whole.indexOf(
                    self.bindings.ui.page__ihda
                )
            ):
                self.add_event_loop_callback(self._wrapper_current_panetab)
            log_handler.LogHandler.log_msg(
                method=logging.debug, msg="enable category synchronization"
            )
        else:
            self.remove_event_loop_callback(self._wrapper_current_panetab)
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="disable category synchronization"
            )

    def _slot_selection_node_sync(self) -> None:
        if not self.bindings.enabled:
            return
        if self.bindings.ui.actionNode_Synchronization.isChecked():
            self._add_selection_callback(self._wrapper_selection_callback_item_by_ihda)
            log_handler.LogHandler.log_msg(
                method=logging.debug, msg="enable selection node synchronization"
            )
        else:
            self._remove_selection_callback(
                self._wrapper_selection_callback_item_by_ihda
            )
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="disable selection node synchronization"
            )

    def _wrapper_current_panetab(self) -> None:
        self.wrapper_execute_deferred(self._set_current_panetab)

    def _set_current_panetab(self) -> None:
        panetab = self.bindings.host.pane_tab_under_cursor()
        self.current_panetab = panetab
        if self.current_panetab is None:
            return
        net_type_name = self.bindings.host.current_network_editor_type_name(
            network_editor=self.current_panetab,
            not_have_null_node_context_lst=self.bindings.contexts_without_null,
        )
        if net_type_name is None:
            return
        self.bindings.selection.select_category(category=net_type_name)

    def _wrapper_selection_callback_item_by_ihda(self, selection: Any) -> None:
        # 굳이 execute deferred함수를 쓸 이유가 없다. 오히려 이 함수를 쓰게되면 딜레이가 생긴다.
        # self.wrapper_execute_deferred(lambda: self._set_selection_callback_item_by_ihda(selection))
        self._set_selection_callback_item_by_ihda(selection)

    def _set_selection_callback_item_by_ihda(self, selection: Any) -> None:
        if not len(selection):
            return
        node = selection[0]
        find_hda_info = self.bindings.host.get_hda_info_by_selection_node(node=node)
        if find_hda_info is None:
            return
        self.bindings.selection.select_model_item_by_hda_id(
            hda_id=find_hda_info.get(keys.Key.Comment.ihda_id)
        )

    def is_valid_network_category(
        self,
        network_editor: hou.NetworkEditor | None = None,
        category: str | None = None,
        hda_name: str | None = None,
    ) -> bool:
        net_category = self.bindings.host.current_network_editor_type_name(
            network_editor, self.bindings.contexts_without_null
        )
        if net_category == category:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning,
            msg=f"current network category: {net_category}",
        )
        log_handler.LogHandler.log_msg(
            method=logging.warning,
            msg=f'"{hda_name}" iHDA node category: {category}',
        )
        return False

    def wrapper_execute_deferred(self, func: Callable[[], object]) -> None:
        def invoke() -> None:
            if (
                not self.bindings.status.closing
                and not self.bindings.status.host_destroying
            ):
                func()

        self.bindings.host.execute_deferred(invoke)
