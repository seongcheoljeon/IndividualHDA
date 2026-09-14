from __future__ import annotations

import threading
from typing import Any

from PySide6 import QtTest

from libs.asset_search import AssetSearch


def test_superseded_search_results_are_dropped(app: Any) -> None:
    gate = threading.Event()
    received: list[frozenset[int]] = []
    search = AssetSearch(app)  # parented: outlives queued thread signals
    search.results.connect(received.append)

    def slow(query: str, cancel: threading.Event) -> list[int]:
        gate.wait(2)
        return [1]

    def fast(query: str, cancel: threading.Event) -> list[int]:
        return [2]

    search.submit("a", slow)
    search.submit("b", fast)
    gate.set()
    for _ in range(100):
        app.processEvents()
        QtTest.QTest.qWait(10)
        if not search.busy and received:
            break
    search.drain()
    app.processEvents()
    assert received == [frozenset({2})]
    search.deleteLater()
    app.processEvents()


def test_rewrite_hook_and_failure(app: Any) -> None:
    seen: list[str] = []
    errors: list[object] = []
    search = AssetSearch(app, rewrite=lambda text: text.upper())
    search.results.connect(lambda ids: seen.append("ok"))
    search.failed.connect(errors.append)

    def record(query: str, cancel: threading.Event) -> list[int]:
        seen.append(query)
        raise RuntimeError("boom")

    search.submit("smoke", record)
    for _ in range(100):
        app.processEvents()
        QtTest.QTest.qWait(10)
        if errors:
            break
    search.drain()
    app.processEvents()
    assert seen == ["SMOKE"] and len(errors) == 1
    search.deleteLater()
    app.processEvents()
