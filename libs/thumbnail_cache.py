"""Bounded thumbnail cache: QImage decoding on Qt workers, QPixmap on GUI thread."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

from PySide6 import QtCore, QtGui


class ImageSignals(QtCore.QObject):
    ready = QtCore.Signal(object, int, QtGui.QImage)


class ImageRead(QtCore.QRunnable):
    def __init__(
        self,
        key: int,
        generation: int,
        path: Path,
        signals: ImageSignals,
        resolve: Callable[[], Path] | None = None,
    ) -> None:
        super().__init__()
        self.resolve = resolve
        self.key, self.generation, self.path, self.signals = (
            key,
            generation,
            path,
            signals,
        )

    def run(self) -> None:
        image = QtGui.QImage()
        try:
            path = self.resolve() if self.resolve is not None else self.path
            reader = QtGui.QImageReader(str(path))
            size = reader.size()
            if size.isValid() and max(size.width(), size.height()) > 1024:
                size.scale(1024, 1024, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                reader.setScaledSize(size)
            image = reader.read()
        except Exception:
            # A missing/offline preview must not interrupt asset browsing.
            image = QtGui.QImage()
        finally:
            self.signals.ready.emit(self.key, self.generation, image)


class ThumbnailCache(QtCore.QObject):
    changed = QtCore.Signal(int)

    def __init__(
        self,
        fallback: QtGui.QPixmap,
        capacity: int = 256,
        byte_limit: int = 64 * 1024 * 1024,
    ) -> None:
        super().__init__()
        if capacity < 1 or byte_limit < 1:
            raise ValueError("Thumbnail cache limits must be positive")
        self._closed = False
        self.fallback = fallback
        self.capacity = capacity
        self.byte_limit = byte_limit
        self._bytes = 0
        self._paths: dict[int, Path] = {}
        self._resolvers: dict[int, Callable[[], Path]] = {}
        self._versions: dict[int, int] = {}
        self._generation = 0
        self._cache: OrderedDict[int, QtGui.QPixmap] = OrderedDict()
        self._pending: dict[int, int] = {}
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(2)
        self._signals = ImageSignals(self)
        self._signals.ready.connect(
            self._receive, QtCore.Qt.ConnectionType.QueuedConnection
        )

    @property
    def decoded_count(self) -> int:
        return len(self._cache)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def __contains__(self, key: int) -> bool:
        return key in self._paths or key in self._cache

    def __delitem__(self, key: int) -> None:
        self._paths.pop(key, None)
        self._resolvers.pop(key, None)
        self._versions.pop(key, None)
        old = self._cache.pop(key, None)
        if old is not None:
            self._bytes -= self._cost(old)

    def clear(self) -> None:
        self._paths.clear()
        self._resolvers.clear()
        self._versions.clear()
        self._cache.clear()
        self._bytes = 0

    def set_path(
        self, key: int, path: Path | None, resolve: Callable[[], Path] | None = None
    ) -> None:
        self.__delitem__(key)
        self._generation += 1
        self._versions[key] = self._generation
        if path is not None:
            self._paths[key] = path
            if resolve is not None:
                self._resolvers[key] = resolve
        self.changed.emit(key)

    def get(self, key: int, default: QtGui.QPixmap | None = None) -> QtGui.QPixmap:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        path = self._paths.get(key)
        if (
            not self._closed
            and path is not None
            and key not in self._pending
            and len(self._pending) < 32
        ):
            generation = self._versions[key]
            self._pending[key] = generation
            self._pool.start(
                ImageRead(
                    key, generation, path, self._signals, self._resolvers.get(key)
                )
            )
        return self.fallback if default is None else default

    @staticmethod
    def _cost(pixmap: QtGui.QPixmap) -> int:
        return pixmap.width() * pixmap.height() * max(pixmap.depth(), 32) // 8

    @QtCore.Slot(object, int, QtGui.QImage)
    def _receive(self, key: int, generation: int, image: QtGui.QImage) -> None:
        if self._closed:
            return
        if self._pending.get(key) != generation:
            return
        self._pending.pop(key, None)
        if self._versions.get(key) != generation:
            self.changed.emit(key)
            return
        pixmap = self.fallback if image.isNull() else QtGui.QPixmap.fromImage(image)
        self._cache[key] = pixmap
        self._bytes += self._cost(pixmap)
        while len(self._cache) > self.capacity or (
            self._bytes > self.byte_limit and len(self._cache) > 1
        ):
            _, removed = self._cache.popitem(last=False)
            self._bytes -= self._cost(removed)
        self.changed.emit(key)

    def shutdown(self) -> None:
        self._closed = True
        self._pool.clear()
        self._pool.waitForDone()
        self._pending.clear()
