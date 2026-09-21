"""Shared thumbnail presentation for asset and history models."""

from __future__ import annotations

from typing import Protocol

from PySide6 import QtCore, QtGui

from libs.thumbnail_cache import ThumbnailCache
from libs.ui_icons import Icon

_PLACEHOLDERS: dict[int, QtGui.QPixmap] = {}


class PixmapSource(Protocol):
    def get(
        self, key: int, default: QtGui.QPixmap | None = None
    ) -> QtGui.QPixmap | None: ...


def placeholder(size: int) -> QtGui.QPixmap:
    """The "no image" pixmap at ``size``; one instance per size."""
    pixmap = _PLACEHOLDERS.get(size)
    if pixmap is None:
        pixmap = QtGui.QPixmap(Icon.NO_IMG_AVAILABLE).scaled(
            QtCore.QSize(size, size), QtCore.Qt.AspectRatioMode.KeepAspectRatio
        )
        _PLACEHOLDERS[size] = pixmap
    return pixmap


def thumbnail(
    source: PixmapSource | dict[int, QtGui.QPixmap],
    identity: int | None,
    size: int,
) -> QtGui.QPixmap:
    """The item's thumbnail fitted to ``size``; never reads a file on this thread.

    Decoding belongs to ThumbnailCache's workers (set_path arms it, changed
    repaints the row). data() only ever hands back what is already in memory.
    """
    if identity is None:
        return placeholder(size)
    if isinstance(source, ThumbnailCache):
        return source.scaled(identity, size)
    pixmap = source.get(identity)
    if pixmap is None or pixmap.isNull():
        return placeholder(size)
    return pixmap.scaled(
        QtCore.QSize(size, size), QtCore.Qt.AspectRatioMode.KeepAspectRatio
    )
