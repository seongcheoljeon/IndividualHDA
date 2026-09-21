"""Keyboard shortcuts of the panel.

The panel lives inside a Houdini Python Panel, so nothing here may be a
window-wide shortcut: Ctrl+S or F5 at window scope would steal Houdini's own
keys. Everything is scoped to the panel (WidgetWithChildrenShortcut) or to one
widget (WidgetShortcut), and only fires while the focus is there.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from main import IndividualHDA

PANEL = QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut
WIDGET = QtCore.Qt.ShortcutContext.WidgetShortcut


def _shortcut(
    key: QtGui.QKeySequence | QtGui.QKeySequence.StandardKey | QtCore.Qt.Key,
    parent: QtCore.QObject,
    slot: Callable[[], None],
    context: QtCore.Qt.ShortcutContext,
) -> QtGui.QShortcut:
    shortcut = QtGui.QShortcut(QtGui.QKeySequence(key), parent)
    shortcut.setContext(context)
    shortcut.activated.connect(slot)
    return shortcut


def install_shortcuts(window: IndividualHDA) -> dict[str, QtGui.QShortcut]:
    """Bind the panel's keys; returns them by name so tests can fire them."""
    # F5 on the existing Reload action: the toolbar shows the key in its tooltip.
    window.actionReload.setShortcut(QtGui.QKeySequence.StandardKey.Refresh)
    window.actionReload.setShortcutContext(PANEL)
    window.addAction(window.actionReload)

    def focus_search() -> None:
        window.lineEdit__search_hda.setFocus()
        window.lineEdit__search_hda.selectAll()

    def remove_selected() -> None:
        if not window.selection.bindings.library().remove_selected():
            window.menus.remove_selected_assets()

    shortcuts = {
        "save": _shortcut(
            QtGui.QKeySequence.StandardKey.Save,
            window,
            window.notes._slot_save_metadata,
            PANEL,
        ),
        "find": _shortcut(
            QtGui.QKeySequence.StandardKey.Find, window, focus_search, PANEL
        ),
        "clear_search": _shortcut(
            QtCore.Qt.Key.Key_Escape,
            window.lineEdit__search_hda,
            window.lineEdit__search_hda.clear,
            WIDGET,
        ),
    }
    # Delete and Enter act on the asset views only, never while typing a note.
    views: dict[str, QtWidgets.QAbstractItemView] = {
        "list": window.views.assets_list,
        "table": window.views.assets_table,
        "history": window.views.history,
    }
    for name in ("list", "table"):
        shortcuts[f"remove_{name}"] = _shortcut(
            QtCore.Qt.Key.Key_Delete, views[name], remove_selected, WIDGET
        )
    for name, view in views.items():
        shortcuts[f"import_{name}"] = _shortcut(
            QtCore.Qt.Key.Key_Return, view, window.selection.import_current, WIDGET
        )
        shortcuts[f"import_{name}_enter"] = _shortcut(
            QtCore.Qt.Key.Key_Enter, view, window.selection.import_current, WIDGET
        )
    return shortcuts
