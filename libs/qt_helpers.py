"""Qt 6 helpers shared by existing views.

The panel runs inside Houdini's QApplication, so the bundled font is applied to
the panel widget, never with QApplication.setFont() -- that would restyle the
whole host.
"""

from __future__ import annotations

import logging
from functools import cache
from importlib import import_module
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

FONT_DIRPATH = Path(__file__).resolve().parent.parent / "resource" / "fonts"


def wildcard_expression(
    text: str, sensitivity: QtCore.Qt.CaseSensitivity
) -> QtCore.QRegularExpression:
    # Qt 5 wildcard searches were unanchored; Qt 6 conversion anchors by default.
    pattern = QtCore.QRegularExpression.wildcardToRegularExpression(
        text,
        QtCore.QRegularExpression.WildcardConversionOption.UnanchoredWildcardConversion,
    )
    expression = QtCore.QRegularExpression(pattern)
    if sensitivity == QtCore.Qt.CaseSensitivity.CaseInsensitive:
        expression.setPatternOptions(
            QtCore.QRegularExpression.PatternOption.CaseInsensitiveOption
        )
    return expression


def center_on_screen(widget: QtWidgets.QWidget) -> None:
    """Move a top-level widget to the middle of the primary screen."""
    screen = QtGui.QGuiApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    widget.move(
        (area.width() // 2) - (widget.frameSize().width() // 2),
        (area.height() // 2) - (widget.frameSize().height() // 2),
    )


def startup_fallback(error: BaseException, log_dir: Path) -> QtWidgets.QWidget:
    """What Houdini shows instead of a traceback when the panel cannot start."""
    from libs.ihda_system import IHDASystem

    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    title = QtWidgets.QLabel("<b>Individual HDA could not start</b>")
    message = QtWidgets.QLabel(f"{type(error).__name__}: {error}")
    message.setWordWrap(True)
    message.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    hint = QtWidgets.QLabel(
        "Details are in the log folder. Fix the cause (Preferences data folder, a "
        "locked library database, a broken settings file) and reopen the panel tab."
    )
    hint.setWordWrap(True)
    button = QtWidgets.QPushButton("Open log folder")
    button.clicked.connect(lambda: IHDASystem.open_folder(dirpath=log_dir))
    for item in (title, message, hint):
        layout.addWidget(item)
    layout.addWidget(button, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    layout.addStretch(1)
    return widget


def dark_stylesheet() -> str:
    # Resource registration is an intentional import side effect. Keep it here
    # so direct callers and first-time theme switches work without other imports.
    import_module("libs.darkstyle_rc")
    resource = QtCore.QFile(":/qdarkstyle/style.qss")
    if not resource.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError("Bundled dark stylesheet is unavailable")
    try:
        return bytes(resource.readAll().data()).decode("utf-8")
    finally:
        resource.close()


def install_bundled_fonts() -> frozenset[str]:
    """Register resource/fonts with Qt once per process; return the families found.

    Qt's font database segfaults without a live QGuiApplication, so an early
    call is a caller bug and is reported as one. Per-file failures only degrade
    to Qt's fallback family; they never break the panel.
    """
    if QtGui.QGuiApplication.instance() is None:
        raise RuntimeError("Install the bundled fonts after the host application")
    return _register_bundled_fonts()


@cache
def _register_bundled_fonts() -> frozenset[str]:
    families: set[str] = set()
    for filepath in sorted(FONT_DIRPATH.glob("*.[ot]tf")):
        identifier = QtGui.QFontDatabase.addApplicationFont(str(filepath))
        if identifier == -1:
            logging.warning("Could not load bundled font %s", filepath.name)
            continue
        families.update(QtGui.QFontDatabase.applicationFontFamilies(identifier))
    if not families:
        logging.warning("No bundled font was loaded from %s", FONT_DIRPATH)
    return frozenset(families)


class _WindowFontPropagation(QtCore.QObject):
    """Lets every window a subtree opens inherit that subtree's font.

    QWidget.setFont() stops at top-level children: Qt merges font and palette
    into a window only when it carries Qt::WA_WindowPropagation, so dialogs,
    message boxes and combo box popups otherwise fall back to the host
    application font. Watching ChildAdded also covers windows opened later and
    nested ones, because the filter follows each new widget down the tree.

    A style sheet would reach the same windows but overrules setFont(), which
    would silently disable the font choices in Preferences.
    """

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ChildAdded:
            child = event.child()
            if child is not None and child.isWidgetType():
                child.setAttribute(QtCore.Qt.WidgetAttribute.WA_WindowPropagation, True)
                child.installEventFilter(self)
        return False


def apply_panel_font(widget: QtWidgets.QWidget, family: str) -> None:
    """Give a widget subtree the bundled family, windows it opens included.

    Only the family is set, so the font's resolve mask leaves every child's own
    point size -- and any explicit setFont() -- untouched. The host application
    font is never changed, so Houdini's own widgets keep their look.
    """
    installed = install_bundled_fonts()
    if family not in installed:
        logging.warning(
            "Font family %r is not among the bundled families %s; Qt will substitute",
            family,
            sorted(installed),
        )
    font = QtGui.QFont()
    font.setFamily(family)
    widget.setFont(font)
    widget.installEventFilter(_WindowFontPropagation(widget))


def sized_font(font: QtGui.QFont, point_size: int) -> QtGui.QFont:
    """A copy of an inherited widget font at a painter-specific size.

    QPainter.setFont() takes no font from the widget hierarchy, so overlays that
    paint text must pass their own widget font along instead of naming a family.
    """
    font = QtGui.QFont(font)
    font.setPointSize(point_size)
    return font
