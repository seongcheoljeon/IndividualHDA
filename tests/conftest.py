from __future__ import annotations

import gc
import os
import sys
import tempfile
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_test_config = tempfile.TemporaryDirectory(prefix="ihda-tests-")
os.environ["IHDA_CONFIG_DIR"] = _test_config.name
os.environ.setdefault("IHDA_USER", "tester")

import pytest  # noqa: E402  (env vars above must be set before Qt/app imports)

from tools.test_suites import includes, suite_for  # noqa: E402


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--suite", choices=("all", "core", "qt", "server", "postgres"), default="all"
    )


def pytest_configure(config: pytest.Config) -> None:
    for name in ("core", "qt", "server", "postgres"):
        config.addinivalue_line("markers", f"{name}: {name} verification boundary")
    if config.getoption("--suite") == "postgres" and not os.getenv(
        "IHDA_TEST_POSTGRES_URL"
    ):
        raise pytest.UsageError(
            "postgres suite requires IHDA_TEST_POSTGRES_URL pointing to a disposable test database"
        )


def pytest_ignore_collect(collection_path: Any, config: pytest.Config) -> bool | None:
    if collection_path.name.startswith("test_") and collection_path.suffix == ".py":
        return not includes(config.getoption("--suite"), collection_path.name)
    return None


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    selected, deselected = [], []
    suite = config.getoption("--suite")
    for item in items:
        group = suite_for(item.path.name)
        if (
            item.path.name == "test_team_library.py"
            and getattr(item, "callspec", None) is not None
        ):
            if item.callspec.params.get("backend") == "personal":
                group = "qt"
        if item.name == "test_personal_revision_observes_original_ui_writes":
            group = "qt"
        item.add_marker(getattr(pytest.mark, group))
        (selected if suite in ("all", "postgres", group) else deselected).append(item)
    items[:] = selected
    if deselected:
        config.hook.pytest_deselected(items=deselected)


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
    if "PySide6.QtWidgets" not in sys.modules:
        return
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
