"""Small Qt property helpers shared by the maintained Python layouts."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy, QWidget


def make_font(
    point_size: int | None = None, families: list[str] | None = None
) -> QFont:
    font = QFont()
    if point_size is not None:
        font.setPointSize(point_size)
    if families is not None:
        font.setFamilies(families)
    return font


def size_policy(
    widget: QWidget, horizontal: QSizePolicy.Policy, vertical: QSizePolicy.Policy
) -> QSizePolicy:
    policy = QSizePolicy(horizontal, vertical)
    policy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
    return policy


def main_window_text(text: str) -> str:
    """Translatable text in the main window's context."""
    return QCoreApplication.translate("MainWindow__individualHDA", text)


def preference_text(text: str) -> str:
    """Translatable text in the preference dialog's context."""
    return QCoreApplication.translate("Dialog__preference", text)
