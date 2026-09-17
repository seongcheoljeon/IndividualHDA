"""Style setters shared by the Qt item models (font, padding)."""

from __future__ import annotations

from typing import Any


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
