"""Runtime contracts for maintained Python layouts; no Designer/compiler needed."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore, QtTest, QtWidgets

LAYOUTS = [
    ("panel", "MainWindowLayout", QtWidgets.QMainWindow, "Individual HDA"),
    ("detail_view", "DetailViewLayout", QtWidgets.QDialog, "iHDA Detail View"),
    ("make_video_info", "VideoInfoLayout", QtWidgets.QDialog, "Make Video Information"),
    ("preference", "PreferenceLayout", QtWidgets.QDialog, "iHDA Preference"),
    ("rename_ihda", "RenameLayout", QtWidgets.QDialog, "iHDA Rename"),
    ("video_player", "VideoPlayerLayout", QtWidgets.QWidget, "iHDA Video Player"),
    ("web_view", "WebViewLayout", QtWidgets.QWidget, "iHDA Web View"),
]


@pytest.mark.parametrize("package,class_name,window_type,title", LAYOUTS)
def test_python_layout_builds_and_dialog_buttons_work(
    app: Any, package: str, class_name: str, window_type: Any, title: str
) -> None:
    if package == "web_view":
        pytest.importorskip("PySide6.QtWebEngineWidgets")
    module = importlib.import_module(f"widgets.{package}.layout")
    layout = getattr(module, class_name)()
    window = window_type()
    try:
        layout.build_ui(window)
        assert window.windowTitle() == title
        assert window.layout() is not None
        if hasattr(layout, "buttonBox__confirm"):
            accepted = QtTest.QSignalSpy(window.accepted)
            rejected = QtTest.QSignalSpy(window.rejected)
            layout.buttonBox__confirm.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).click()
            assert accepted.count() == 1
            layout.buttonBox__confirm.button(
                QtWidgets.QDialogButtonBox.StandardButton.Cancel
            ).click()
            assert rejected.count() == 1
    finally:
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_main_navigation_and_embedding_hosts(app: Any) -> None:
    from widgets.panel.layout import MainWindowLayout

    window = QtWidgets.QMainWindow()
    layout = MainWindowLayout()
    layout.build_ui(window)
    try:
        assert layout.stackedWidget__whole.count() == 4
        assert layout.stackedWidget__whole.widget(0) is layout.page__ihda
        assert layout.stackedWidget__whole.widget(3) is layout.page__history
        assert layout.stackedWidget__hda_infos.count() == 3
        assert layout.textEdit__note.parentWidget() is layout.widget__note_editor
        assert layout.textEdit__tag.parentWidget() is layout.widget__tag_editor
        assert (
            layout.widget__asset_browser_host.parentWidget()
            is layout.widget__asset_panel
        )
        assert layout.actionPreference in layout.menuTools.actions()
        actions = layout.toolBar.actions()
        assert actions.index(layout.actioniHDA) < actions.index(layout.actionHistory)
        assert layout.actionCategory_Synchronization in actions
    finally:
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_preference_tabs_and_persisted_control_contract(app: Any) -> None:
    from widgets.preference.layout import PreferenceLayout

    window = QtWidgets.QDialog()
    layout = PreferenceLayout()
    layout.build_ui(window)
    try:
        tabs = layout.tabWidget__view_settings
        assert [tabs.tabText(i) for i in range(tabs.count())] == [
            "Icon / Thumbnail",
            "Padding",
            "Text",
        ]
        assert layout.lineEdit__data_dirpath.placeholderText() == "d:/library"
        assert layout.lineEdit__result.isReadOnly()
        assert layout.spinBox__default_main_icon_size.minimum() > 0
        assert layout.doubleSpinBox__default_list_item_padding.suffix() == "px"
        assert (
            layout.fontComboBox__note_font_style.parentWidget() is layout.groupBox__note
        )
    finally:
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_application_has_no_designer_sources_or_generated_layouts() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = [
        *root.glob("*.ui"),
        *root.glob("*_ui.py"),
        *root.joinpath("widgets").rglob("*.ui"),
        *root.joinpath("widgets").rglob("*_ui.py"),
    ]
    assert not sources, (
        "Edit the maintained layout.py modules instead of adding Designer files"
    )
