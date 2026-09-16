from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore, QtGui

from libs.asset_store import AssetStore
from libs.domain import SelectionState
from libs.thumbnail_cache import ThumbnailCache


def test_asset_index_stays_consistent_and_ids_are_immutable() -> None:
    store = AssetStore()
    store.reset([{"hda_id": 3, "hda_name": "C"}])
    store.insert({"hda_id": 1, "hda_name": "A"})
    assert store.id_rows == {1: 0, 3: 1}
    with pytest.raises(ValueError):
        store.update(0, {"hda_id": 3})
    store.remove(0)
    assert store.id_rows == {3: 0}
    state = SelectionState()
    state.asset.data = store.rows[0]
    state.clear_asset()
    assert state.asset.data is None and store.rows[0]["hda_id"] == 3


def test_async_thumbnail_cache_is_bounded_and_rejects_stale_images(
    app: Any, tmp_path: Path
) -> None:
    image = QtGui.QImage(32, 32, QtGui.QImage.Format_RGB32)
    image.fill(QtCore.Qt.red)
    path = tmp_path / "한글.png"
    assert image.save(str(path))
    cache = ThumbnailCache(QtGui.QPixmap(8, 8), capacity=2)
    received = []
    cache.changed.connect(
        lambda key: received.append((key, QtCore.QThread.currentThread()))
    )
    for key in range(3):
        cache.set_path(key, path)
        cache.get(key)
    deadline = time.monotonic() + 5
    while cache.pending_count and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert cache.pending_count == 0
    assert cache.decoded_count == 2
    assert all(thread == app.thread() for _, thread in received)
    cache.set_path(10, path)
    cache.get(10)
    del cache[10]
    cache.shutdown()
    app.processEvents()
    assert 10 not in cache
    assert cache.decoded_count <= 2


def test_thumbnail_resolver_is_lazy_and_runs_outside_gui_thread(
    app: Any, tmp_path: Path
) -> None:
    from PySide6 import QtCore, QtGui, QtTest

    from libs.thumbnail_cache import ThumbnailCache

    path = tmp_path / "downloaded.png"
    image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtCore.Qt.GlobalColor.blue)
    image.save(str(path))
    calls = []

    def resolve() -> Path:
        calls.append(QtCore.QThread.currentThread())
        return path

    cache = ThumbnailCache(QtGui.QPixmap(2, 2))
    try:
        cache.set_path(1, tmp_path / "not-downloaded.png", resolve=resolve)
        assert calls == []
        cache.get(1)
        for _ in range(500):
            app.processEvents()
            if cache.pending_count == 0:
                break
            QtTest.QTest.qWait(10)
        assert calls and all(thread != app.thread() for thread in calls)
        assert cache.get(1).size() == QtCore.QSize(8, 8)
    finally:
        cache.shutdown()
