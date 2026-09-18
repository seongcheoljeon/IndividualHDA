"""Shared thumbnail presentation for asset and history models."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6 import QtCore, QtGui

from libs.item_paths import item_path
from libs.ui_icons import Icon


class PixmapSource(Protocol):
    def get(
        self, key: int, default: QtGui.QPixmap | None = None
    ) -> QtGui.QPixmap | None: ...


def thumbnail(
    source: PixmapSource | dict[int, QtGui.QPixmap],
    identity: int | None,
    directory: Path | None,
    filename: str | None,
    size: int,
) -> QtGui.QPixmap:
    pixmap = source.get(identity) if identity is not None else None
    if pixmap is not None and pixmap.isNull():
        path = item_path(directory, filename)
        pixmap = (
            QtGui.QPixmap(str(path)) if path is not None and path.is_file() else None
        )
        if pixmap is not None and isinstance(source, dict) and identity is not None:
            source[identity] = pixmap
    if pixmap is None or pixmap.isNull():
        pixmap = QtGui.QPixmap(Icon.NO_IMG_AVAILABLE)
    return pixmap.scaled(
        QtCore.QSize(size, size), QtCore.Qt.AspectRatioMode.KeepAspectRatio
    )
