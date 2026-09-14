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
