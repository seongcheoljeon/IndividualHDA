"""Narrow host capabilities. Adapters run on the Houdini GUI thread."""

from __future__ import annotations

import pathlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import hou


class HostCallbacksPort(Protocol):
    def add_event_loop_callback(self, func: Callable[..., Any]) -> None: ...
    def add_selection_callback(self, func: Callable[..., Any]) -> None: ...
    def remove_event_loop_callback(self, func: Callable[..., Any]) -> None: ...
    def remove_selection_callback(self, func: Callable[..., Any]) -> None: ...
    def has_event_loop_callback(self, func: Callable[..., Any]) -> bool: ...
    def has_selection_callback(self, func: Callable[..., Any]) -> bool: ...
    def pane_tab_under_cursor(self) -> Any | None: ...
    def current_network_editor_type_name(
        self,
        network_editor: hou.NetworkEditor | None = None,
        not_have_null_node_context_lst: Any = None,
    ) -> str | None: ...
    def get_hda_info_by_selection_node(
        self, node: hou.Node | None = None
    ) -> None | dict[str, Any]: ...
    def execute_deferred(self, func: Callable[[], object]) -> None: ...


class HostCapturePort(Protocol):
    def create_hda_file(
        self,
        node: hou.Node | None = None,
        hda_dirpath: pathlib.Path | None = None,
        hda_filename: str | None = None,
        hda_version: str | None = None,
    ) -> bool: ...
    def create_thumbnail(self, output_filepath: pathlib.Path | None = None) -> bool: ...
    def create_preview(
        self,
        output_filepath: pathlib.Path | None = None,
        frame_info: tuple[float, float, float] | list[float] | None = None,
        resolution: tuple[int, int] | list[int] | None = None,
        is_beautypass_only: bool = False,
        is_init_sim: bool = False,
        is_motionblur: bool = False,
        is_crop_out_mask: bool = True,
    ) -> bool: ...


class HostScenePort(Protocol):
    def current_hipfile(self) -> pathlib.Path: ...
    def current_houdini_version(self) -> str: ...
    def import_individual_hda_into_houdini(
        self,
        node_filepath: pathlib.Path | None = None,
        parent_node: hou.Node | None = None,
        position: hou.Vector2 | None = None,
        node_name: str | None = None,
        node_type_name: str | None = None,
    ) -> hou.Node | None: ...
