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
        assert (
            layout.lineEdit__data_dirpath.placeholderText()
            == "Choose a library directory"
        )
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


def test_every_referenced_icon_resolves(app: Any) -> None:
    """A wrong resource path renders as a blank icon, never as an error.

    Three menu entries shipped with `_18dp`/`_48dp` suffixes that exist in no
    .qrc, so they drew nothing. Only literal paths are checked; a few call sites
    build the name at runtime and cannot be swept this way.
    """
    import importlib
    import re
    from pathlib import Path

    from PySide6 import QtGui

    root = Path(__file__).resolve().parent.parent
    # Resources only exist once their generated module is imported, and four
    # .qrc files share the "main" prefix alone. Register every one of them, or
    # icons that are perfectly fine get reported as missing.
    for generated in sorted(root.rglob("*_rc.py")):
        if ".venv" in generated.parts:
            continue
        importlib.import_module(
            ".".join(generated.relative_to(root).with_suffix("").parts)
        )

    reference = re.compile(r'":(/[\w-]+/icons/[\w.@-]+)"')
    missing: dict[str, list[str]] = {}
    for source in sorted(root.rglob("*.py")):
        if source.name.endswith("_rc.py") or ".venv" in source.parts:
            continue
        for path in reference.findall(source.read_text(encoding="utf-8")):
            if QtGui.QPixmap(f":{path}").isNull():
                missing.setdefault(path, []).append(str(source.relative_to(root)))
    assert not missing, f"unresolved icon resources: {missing}"


def test_tag_action_buttons_share_one_icon_size(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The AI button is built in code, not in the .py layout, so it missed the
    explicit icon size its siblings set and rendered visibly smaller."""
    from main import IndividualHDA
    from widgets.ui_tokens import TOOLBAR_ICON_SIZE
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    panel = IndividualHDA()
    try:
        expected = panel.pushButton__tag_save.iconSize()
        assert expected.width() == TOOLBAR_ICON_SIZE
        assert panel.pushButton__ai_suggest.iconSize() == expected
    finally:
        panel.close()


def test_qobject_panel_features_do_not_shadow_qt_api() -> None:
    """A method named like a QObject member hides Qt's own and breaks wiring.

    PanelAIActions.connect() shadowed QObject.connect, which PySide6 calls with
    four arguments to hook up a signal: the panel failed to start in Houdini.
    Houdini ships PySide6 6.5.3 while the tests run on 6.11.2, which tolerates
    the shadowing -- so only a static check catches it. It lives here, not in
    test_architecture.py, because the core suite runs without PySide6 installed.
    """
    import ast

    from PySide6 import QtCore

    reserved = {name for name in dir(QtCore.QObject) if not name.startswith("__")}
    root = Path(__file__).resolve().parent.parent / "widgets" / "panel"
    offenders: dict[str, list[str]] = {}
    for source in sorted(root.glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            bases = {ast.unparse(base) for base in cls.bases}
            if not bases & {"QtCore.QObject", "QObject"}:
                continue
            clashes = sorted(
                node.name
                for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name in reserved
            )
            if clashes:
                offenders[f"{source.stem}.{cls.name}"] = clashes
    assert not offenders, f"these hide Qt's own members: {offenders}"


def test_observation_equality_survives_a_node_deleted_in_houdini() -> None:
    """A HOM node raises ObjectWasDeleted once the user deletes it.

    The observation list is scanned with `in` on every import, so one deleted
    node anywhere in it aborted the whole scene record with
    "Imported asset; scene record could not be queued". Here rather than in
    test_scene_repository.py: scene_usage imports Qt, the core suite has none.
    """
    from widgets.panel.scene_usage import SceneObservation

    class DeletedNode:
        def __eq__(self, other: object) -> bool:
            raise RuntimeError("Attempt to access an object that no longer exists")

        __hash__ = None  # type: ignore[assignment]

    def observation(session_id: int) -> SceneObservation:
        return SceneObservation(
            node=DeletedNode(),
            session_id=session_id,
            version_uuid="v1",
            namespace="tester",
        )

    observed = [observation(1)]
    assert observation(2) not in observed  # must not raise
    assert observation(1) in observed  # and dedup still works
