"""Bundled font registration and panel-scoped application."""

from __future__ import annotations

import pytest
from PySide6 import QtGui, QtWidgets

from libs.keys import UISetting
from libs.qt_helpers import (
    FONT_DIRPATH,
    apply_panel_font,
    install_bundled_fonts,
    sized_font,
)


def test_bundled_files_cover_the_configured_family(
    app: QtWidgets.QApplication,
) -> None:
    assert list(FONT_DIRPATH.glob("*.[ot]tf")), f"no font shipped in {FONT_DIRPATH}"
    assert UISetting.dft_font_style in install_bundled_fonts()


def test_panel_font_leaves_the_host_application_untouched(
    app: QtWidgets.QApplication,
) -> None:
    """Houdini owns the QApplication; only the panel subtree may change family."""
    app.setFont(QtGui.QFont("Arial", 9))
    panel = QtWidgets.QWidget()
    apply_panel_font(panel, UISetting.dft_font_style)
    child = QtWidgets.QLabel(panel)
    sized = child.font()
    sized.setPointSize(11)
    child.setFont(sized)

    assert app.font().family() == "Arial"
    assert panel.font().family() == UISetting.dft_font_style
    # Family propagates, the child's own point size survives.
    assert child.font().family() == UISetting.dft_font_style
    assert child.font().pointSize() == 11
    assert sized_font(child.font(), 30).pointSize() == 30
    assert sized_font(child.font(), 30).family() == UISetting.dft_font_style


def test_windows_the_panel_opens_inherit_the_panel_font(
    app: QtWidgets.QApplication,
) -> None:
    """Qt skips font propagation into windows without WA_WindowPropagation.

    The detail view and the library-source combo popup are separate windows, so
    they kept Houdini's font until the panel started propagating into them.
    """
    app.setFont(QtGui.QFont("Arial", 9))
    panel = QtWidgets.QWidget()
    apply_panel_font(panel, UISetting.dft_font_style)

    dialog = QtWidgets.QDialog(panel)
    nested = QtWidgets.QDialog(dialog)
    message = QtWidgets.QMessageBox(panel)
    combo = QtWidgets.QComboBox(panel)
    combo.addItem("Personal")
    popup = combo.view().window()

    for window in (dialog, nested, message, popup):
        window.ensurePolished()
        assert window.isWindow(), window
        assert window.font().family() == UISetting.dft_font_style, window


def test_propagation_never_overrules_an_explicit_font(
    app: QtWidgets.QApplication,
) -> None:
    """Preferences applies the user's font with setFont(); it has to win.

    A panel-wide style sheet would reach the same windows but overrule this,
    silently disabling the font choices in Preferences.
    """
    app.setFont(QtGui.QFont("Arial", 9))
    panel = QtWidgets.QWidget()
    apply_panel_font(panel, UISetting.dft_font_style)

    editor = QtWidgets.QTextEdit(QtWidgets.QDialog(panel))
    chosen = QtGui.QFont()
    chosen.setFamily("Verdana")
    chosen.setPointSize(14)
    editor.setFont(chosen)
    editor.ensurePolished()

    assert editor.font().family() == "Verdana"
    assert editor.font().pointSize() == 14


def test_installing_before_the_host_application_is_a_caller_error() -> None:
    """A bare addApplicationFont() call segfaults instead of raising."""
    if QtGui.QGuiApplication.instance() is not None:
        pytest.skip("the session QApplication is already running")
    with pytest.raises(RuntimeError, match="host application"):
        install_bundled_fonts()
