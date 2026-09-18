"""Style setters shared by the Qt item models (font, padding)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from PySide6 import QtCore, QtGui

from libs import keys
from libs.model_columns import ViewColumn


class ModelStyleMixin:
    """Host must be a QAbstractItemModel with _font_style/_font_size/_padding fields."""

    def set_font(self, style: str | None = None, size: int | None = None) -> None:
        self.beginResetModel()  # type: ignore[attr-defined]
        if style is not None:
            self._font_style = style
        if size is not None:
            self._font_size = size
        self.endResetModel()  # type: ignore[attr-defined]

    def set_padding(self, val: Any) -> None:
        self.beginResetModel()  # type: ignore[attr-defined]
        self._padding = int(val)
        self.endResetModel()  # type: ignore[attr-defined]


UNHANDLED = object()


def header_data(
    labels: type[ViewColumn] | Sequence[str],
    section: int,
    orientation: QtCore.Qt.Orientation,
    role: int,
    *,
    row_prefix: str | None = None,
) -> Any:
    """Header text, font and (absent) decoration shared by every item model.

    Returns UNHANDLED for roles the caller decides itself, so the model can
    add its own (alignment, a Qt default) without repeating the common part.
    """
    if role == QtCore.Qt.ItemDataRole.DisplayRole:
        if orientation == QtCore.Qt.Orientation.Horizontal:
            if isinstance(labels, type):
                return labels(section).label
            return labels[section]
        if row_prefix is not None:
            return f"{row_prefix} {section + 1}"
        return UNHANDLED
    if role == QtCore.Qt.ItemDataRole.FontRole:
        font = QtGui.QFont()
        font.setPointSize(keys.UISetting.view_font_size)
        return font
    if role == QtCore.Qt.ItemDataRole.DecorationRole:
        return None
    return UNHANDLED
