"""The Find page: which iHDA instances the current HIP file holds.

One owner for the scan, the tree, the asset filter combobox, the count and the
empty state. The scan itself comes through a callable (the host scene port), so
the page is exercised in tests with a fake scene.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

from libs import keys, log_handler
from libs.qt_helpers import wildcard_expression
from libs.scene_scan import ScannedNode, count_marks, marked_nodes
from widgets.ui_tokens import ASSET_COMBO_ICON_SIZE

if TYPE_CHECKING:
    from libs.ihda_icons import IHDAIcons
    from model.ihda_inside_model import InsideModel
    from model.ihda_inside_proxy_model import InsideProxyModel
    from widgets.empty_state import EmptyState
    from widgets.panel.ports import PresentationPort


@dataclass(frozen=True, slots=True, kw_only=True)
class InsidePageBindings:
    scan_scene: Callable[[], Sequence[ScannedNode]]
    model: InsideModel
    proxy: InsideProxyModel
    view: QtWidgets.QTreeView
    empty: EmptyState
    combo: QtWidgets.QComboBox
    count_label: QtWidgets.QLabel
    connect_checkbox: QtWidgets.QCheckBox
    search_edit: QtWidgets.QLineEdit
    nav_button: QtWidgets.QAbstractButton
    icons: IHDAIcons
    selected_asset_id: Callable[[], int | None]
    go_to_node: Callable[[str | None], None]
    presentation: PresentationPort


class InsidePageController:
    """Scans lazily: imports and registrations mark the tree stale, the scan runs
    when the page is (or becomes) visible, and never before the models exist."""

    def __init__(self, bindings: InsidePageBindings) -> None:
        self.bindings = bindings
        self._stale = True
        self._ready = False
        bindings.empty.set_content(
            "Not scanned yet",
            "The current HIP file is scanned when this page opens.",
            "Scan now",
            self.refresh,
        )

    # --- lifecycle -----------------------------------------------------------

    def models_ready(self) -> None:
        """Bootstrap: the model exists; scan now if the page is already showing."""
        self._ready = True
        self._scan_if_showing()

    def mark_stale(self) -> None:
        self._stale = True
        self._scan_if_showing()

    def page_shown(self) -> None:
        self._scan_if_showing()

    def _scan_if_showing(self) -> None:
        if self._ready and self._stale and self.bindings.nav_button.isChecked():
            self.refresh()

    # --- scanning ------------------------------------------------------------

    @log_handler.log_elapsed("iHDA node search")
    def refresh(self) -> None:
        b = self.bindings
        try:
            nodes = tuple(b.scan_scene())
        except Exception as error:
            b.presentation.notify(
                f"Scanning the HIP file failed: {error}", level="error"
            )
            return
        self._stale = False
        b.model.make_node_tree(nodes)
        b.view.expandAll()
        self._update_count()
        b.empty.set_content(
            "No iHDA nodes in this HIP file",
            "Import an asset into the scene, then scan again.",
            "Scan again",
            self.refresh,
        )
        self._fill_combo(nodes)
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg=f"iHDA node scan: {count_marks(nodes)} instance(s) in the current HIP file",
        )

    # --- filters -------------------------------------------------------------

    def filter_by_combo(self, index: int) -> None:
        self.bindings.proxy.set_filter_attribute(
            hda_id=self.bindings.combo.itemData(index)
        )
        self._show_filtered()

    def connect_to_selection(self, *_: object) -> None:
        """Checkbox: follow the asset selected in the library instead of the combo."""
        b = self.bindings
        checked = b.connect_checkbox.isChecked()
        b.combo.setDisabled(checked)
        if checked:
            b.search_edit.clear()
            b.proxy.set_filter_attribute(hda_id=b.selected_asset_id())
            self._show_filtered()
        else:
            self.filter_by_combo(b.combo.currentIndex())

    def selection_changed(self) -> None:
        """The library selection moved; re-filter only when following it."""
        if self.bindings.connect_checkbox.isChecked():
            self.connect_to_selection()

    def search(self, text: str) -> None:
        self.bindings.proxy.setFilterRegularExpression(
            wildcard_expression(text.strip(), QtCore.Qt.CaseSensitivity.CaseInsensitive)
        )
        self._show_filtered()

    def double_clicked(self, index: QtCore.QModelIndex) -> None:
        """Any row is a Houdini node; the context menu's "Go To Node" agrees."""
        from model.ihda_inside_model import InsideModel

        if index is not None and index.isValid():
            self.bindings.go_to_node(index.data(InsideModel.node_path_role))

    # --- presentation --------------------------------------------------------

    def _show_filtered(self) -> None:
        self._update_count()
        self.bindings.view.expandAll()

    def _update_count(self) -> None:
        self.bindings.count_label.setText(str(self.bindings.proxy.get_row_count()))

    def _fill_combo(self, nodes: Sequence[ScannedNode]) -> None:
        """ALL plus one entry per distinct asset; icons from the caches or the scan."""
        b = self.bindings
        with QtCore.QSignalBlocker(b.combo):
            b.combo.clear()
            root = b.icons.pixmap_cate_data.get(keys.Name.Icons.root, QtGui.QPixmap())
            b.combo.addItem(QtGui.QIcon(self._scaled(root)), "ALL", -1)
            seen: set[int] = set()
            entries = []
            for node in marked_nodes(nodes):
                mark = node.mark
                if mark is None or mark.hda_id in seen:
                    continue
                seen.add(mark.hda_id)
                entries.append((mark.name, mark.hda_id, node.icon_paths))
            for name, hda_id, icon_paths in sorted(entries, key=lambda e: e[0]):
                pixmap = b.icons.pixmap_ihda_data.get(hda_id)
                if pixmap is None:
                    pixmap = b.icons.get_houdini_icon(icon_lst=list(icon_paths) or None)
                b.combo.addItem(QtGui.QIcon(self._scaled(pixmap)), name, hda_id)
            b.combo.setCurrentIndex(0)
        self.filter_by_combo(0)

    @staticmethod
    def _scaled(pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        if pixmap.isNull():
            return pixmap
        return pixmap.scaled(ASSET_COMBO_ICON_SIZE, ASSET_COMBO_ICON_SIZE)
