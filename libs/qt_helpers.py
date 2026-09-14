"""Qt 6 helpers shared by existing views."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


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
