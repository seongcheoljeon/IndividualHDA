"""Host callbacks for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

import public
from libs import houdini_api, log_handler

try:
    import hdefereval
    import hou
except ImportError:
    pass


class HostCallbacksMixin:
    @staticmethod
    def _add_event_loop_callback(event_func: Callable[..., Any]) -> None:
        if not public.IS_HOUDINI:
            return
        if not HostCallbacksMixin._is_exist_event_callbacks(event_func):
            hou.ui.addEventLoopCallback(event_func)

    @staticmethod
    def _add_selection_callback(event_func: Callable[..., Any]) -> None:
        if not public.IS_HOUDINI:
            return
        if not HostCallbacksMixin._is_exist_selection_callbacks(event_func):
            hou.ui.addSelectionCallback(event_func)

    @staticmethod
    def _remove_event_loop_callback(event_func: Callable[..., Any]) -> None:
        if not public.IS_HOUDINI:
            return
        if HostCallbacksMixin._is_exist_event_callbacks(event_func):
            hou.ui.removeEventLoopCallback(event_func)

    @staticmethod
    def _remove_selection_callback(event_func: Callable[..., Any]) -> None:
        if not public.IS_HOUDINI:
            return
        if HostCallbacksMixin._is_exist_selection_callbacks(event_func):
            hou.ui.removeSelectionCallback(event_func)

    @staticmethod
    def _is_exist_event_callbacks(event_func: Callable[..., Any]) -> None | bool:
        if not public.IS_HOUDINI:
            return
        return event_func in hou.ui.eventLoopCallbacks()

    @staticmethod
    def _is_exist_selection_callbacks(event_func: Callable[..., Any]) -> None | bool:
        if not public.IS_HOUDINI:
            return
        return event_func in hou.ui.selectionCallbacks()

    def _slot_stackedwidget_whole_curt_changed(self, index: QtCore.QModelIndex) -> None:
        # 만약 iHDA 뷰가 아닌데 category synchronize가 활성화 상태면, 이벤트 콜백 삭제
        if (index != self._ihda_view_idx) and (
            self.actionCategory_Synchronization.isChecked()
        ):
            self._remove_event_loop_callback(self._wrapper_current_panetab)
        else:
            if self.actionCategory_Synchronization.isChecked():
                self._add_event_loop_callback(self._wrapper_current_panetab)

    def _slot_sync_hou_net_cate(self) -> None:
        if not public.IS_HOUDINI:
            return
        if self.actionCategory_Synchronization.isChecked():
            if self.stackedWidget__whole.currentIndex() == self._ihda_view_idx:
                self._add_event_loop_callback(self._wrapper_current_panetab)
            log_handler.LogHandler.log_msg(
                method=logging.debug, msg="enable category synchronization"
            )
        else:
            self._remove_event_loop_callback(self._wrapper_current_panetab)
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="disable category synchronization"
            )

    def _slot_selection_node_sync(self) -> None:
        if not public.IS_HOUDINI:
            return
        if self.actionNode_Synchronization.isChecked():
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
        self._wrapper_execute_deferred(self._set_current_panetab)

    def _set_current_panetab(self) -> None:
        desk = hou.ui.curDesktop()
        panetab = desk.paneTabUnderCursor()
        self._current_panetab = panetab
        if self._current_panetab is None:
            return
        net_type_name = houdini_api.HoudiniAPI.current_network_editor_type_name(
            network_editor=self._current_panetab,
            not_have_null_node_context_lst=self._not_have_null_node_context_lst,
        )
        if net_type_name is None:
            return
        self._select_category(category=net_type_name)

    def _wrapper_selection_callback_item_by_ihda(self, selection: Any) -> None:
        # 굳이 execute deferred함수를 쓸 이유가 없다. 오히려 이 함수를 쓰게되면 딜레이가 생긴다.
        # self._wrapper_execute_deferred(lambda: self._set_selection_callback_item_by_ihda(selection))
        self._set_selection_callback_item_by_ihda(selection)

    def _set_selection_callback_item_by_ihda(self, selection: Any) -> None:
        if not len(selection):
            return
        node = selection[0]
        find_hda_info = houdini_api.HoudiniAPI.get_hda_info_by_selection_node(node=node)
        if find_hda_info is None:
            return
        self._select_model_item_by_hda_id(
            hda_id=find_hda_info.get(public.Key.Comment.ihda_id)
        )

    def _is_valid_network_category(
        self,
        network_editor: hou.NetworkEditor | None = None,
        category: str | None = None,
        hda_name: str | None = None,
    ) -> bool:
        net_category = houdini_api.HoudiniAPI.current_network_editor_type_name(
            network_editor, self._not_have_null_node_context_lst
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

    def _wrapper_execute_deferred(self, func: Callable[[], object]) -> None:
        def invoke() -> None:
            if not self._closing and not self._host_destroying:
                func()

        hdefereval.executeDeferred(invoke)
