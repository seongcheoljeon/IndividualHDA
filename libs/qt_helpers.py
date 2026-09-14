"""Qt 6 helpers shared by existing views."""

from __future__ import annotations

from PySide6 import QtCore
from importlib import import_module


def wildcard_expression(
    text: str, sensitivity: QtCore.Qt.CaseSensitivity
) -> QtCore.QRegularExpression:
    # Qt 5 wildcard searches were unanchored; Qt 6 conversion anchors by default.
    pattern = QtCore.QRegularExpression.wildcardToRegularExpression(
        text, QtCore.QRegularExpression.UnanchoredWildcardConversion
    )
    expression = QtCore.QRegularExpression(pattern)
    if sensitivity == QtCore.Qt.CaseInsensitive:
        expression.setPatternOptions(QtCore.QRegularExpression.CaseInsensitiveOption)
    return expression


def dark_stylesheet() -> str:
    # Resource registration is an intentional import side effect. Keep it here
    # so direct callers and first-time theme switches work without other imports.
    import_module("libs.darkstyle_rc")
    resource = QtCore.QFile(":/qdarkstyle/style.qss")
    if not resource.open(QtCore.QIODevice.ReadOnly):
        raise RuntimeError("Bundled dark stylesheet is unavailable")
    try:
        return bytes(resource.readAll()).decode("utf-8")
    finally:
        resource.close()
