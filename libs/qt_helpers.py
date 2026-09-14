"""Qt 6 helpers shared by existing views."""

from __future__ import annotations

from importlib import import_module

from PySide6 import QtCore


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
