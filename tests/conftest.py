from __future__ import annotations

import gc
import os
import tempfile
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_test_config = tempfile.TemporaryDirectory(prefix="ihda-tests-")
os.environ["IHDA_CONFIG_DIR"] = _test_config.name
os.environ.setdefault("IHDA_USER", "tester")

import pytest  # noqa: E402  (env vars above must be set before Qt/app imports)


@pytest.fixture(scope="session")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application
    # Widgets a test left behind are deleted while the application still exists
    # (a QWebEnginePage outliving its profile, or a panel collected after
    # QApplication is gone, both segfault at interpreter exit). deleteLater only:
    # closeEvent overrides assume a finished __init__, and panels whose __init__
    # raised survive here through reference cycles.
    from PySide6.QtCore import QEvent

    deferred_delete = QEvent.Type.DeferredDelete
    for widget in application.topLevelWidgets():
        widget.deleteLater()
    # Deferred deletes posted outside an event loop are only delivered on request.
    application.sendPostedEvents(None, deferred_delete)
    application.processEvents()
    gc.collect()
    application.sendPostedEvents(None, deferred_delete)
    application.processEvents()


@pytest.fixture(autouse=True)
def collect_qt_objects_on_gui_thread() -> Any:
    """Do not leave unreachable WebEngine wrappers for a later HTTP worker's GC.

    Explicit test-owned workers must already be drained by their test/fixture.
    Retire the windows a finished test left behind before collecting their
    wrappers. The session QApplication remains alive.
    """
    yield
    from PySide6.QtCore import QCoreApplication, QEvent, QThread

    application = QCoreApplication.instance()
    if application is None:
        return
    assert QThread.currentThread() == application.thread()
    from PySide6.QtWidgets import QApplication

    if isinstance(application, QApplication):
        for widget in application.topLevelWidgets():
            widget.deleteLater()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()
    gc.collect()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete)
