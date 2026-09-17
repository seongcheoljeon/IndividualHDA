from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from widgets.panel.lifetime import PanelLifetime
from widgets.panel.state import PanelStatus


def test_lifetime_stops_at_failed_worker_and_retries_remaining_resources() -> None:
    lifetime = PanelLifetime()
    calls: list[str] = []
    worker = Mock(side_effect=[RuntimeError("busy"), None])
    lifetime.add("view", lambda: calls.append("view"), 20)
    lifetime.add("timer", lambda: calls.append("timer"), 0)
    lifetime.add("worker", worker, 10)
    errors = lifetime.close()
    assert errors[0][0] == "worker"
    assert calls == ["timer"]
    assert lifetime.close() == []
    assert calls == ["timer", "view"]
    assert lifetime.close() == []
    assert worker.call_count == 2


def test_lifetime_rejects_duplicate_ownership() -> None:
    lifetime = PanelLifetime()
    lifetime.add("worker", Mock(), 0)
    with pytest.raises(ValueError, match="already owned"):
        lifetime.add("worker", Mock(), 1)


@pytest.mark.parametrize("failed_phase", [1, 2, 3, 4])
def test_startup_failure_closes_only_acquired_resources(
    monkeypatch: pytest.MonkeyPatch, failed_phase: int
) -> None:
    from widgets.panel.composition import PanelComposition
    from widgets.panel.services import PanelServices

    window = SimpleNamespace(status=PanelStatus())
    composition = PanelComposition(window, PanelServices(), False)
    closed: list[int] = []
    failure = RuntimeError("startup failure")

    def phase(index: int) -> Any:
        def build() -> None:
            if index == failed_phase:
                raise failure
            composition.lifetime.add(str(index), lambda: closed.append(index), index)

        return build

    for index, name in enumerate(
        (
            "_create_features",
            "_create_session_and_widgets",
            "_initialize_models_and_state",
            "_bind_features",
            "_connect_features",
        )
    ):
        monkeypatch.setattr(composition, name, phase(index))
    with pytest.raises(RuntimeError) as caught:
        composition.build()
    assert caught.value is failure
    assert window.status.closing
    assert closed == list(range(failed_phase))


def test_import_close_retry_does_not_restart_or_redrain_services(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    from main import IndividualHDA
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", Mock())
    panel = IndividualHDA()
    shutdown = Mock(wraps=panel._preference.shutdown)
    monkeypatch.setattr(panel._preference, "shutdown", shutdown)
    stream = SimpleNamespace(commit_import=Mock(side_effect=[OSError("locked"), None]))
    panel._archives.stream = stream
    panel._archives.imported = True
    assert not panel.close()
    assert panel.status.closing
    assert not panel.centralwidget.isEnabled()
    assert not panel._library_sync.timer.isActive()
    assert shutdown.call_count == 1
    assert panel.close()
    assert panel.close()
    assert shutdown.call_count == 1
    assert stream.commit_import.call_count == 2
    assert not panel._archives.imported


def test_extracted_features_are_not_panel_bases() -> None:
    from main import IndividualHDA

    bases = {base.__name__ for base in IndividualHDA.__mro__}
    assert not bases.intersection(
        {"BootstrapMixin", "ArchiveActionsMixin", "AIActionsMixin", "LibrarySyncMixin"}
    )


def test_dialog_cleanup_does_not_revisit_a_deleted_dialog(app: Any) -> None:
    from PySide6 import QtCore, QtWidgets

    from widgets.panel.shutdown import PanelShutdown

    class ClosingDialog(QtWidgets.QDialog):
        def shutdown(self) -> None:
            self.reject()
            self.deleteLater()

    class MetadataDialog(QtWidgets.QDialog):
        def shutdown(self) -> None:
            # A worker drain can deliver deferred deletion from an earlier dialog.
            app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    metadata = MetadataDialog()
    metadata.show()
    window = SimpleNamespace(
        status=PanelStatus(),
        _library_sync=SimpleNamespace(presenter=SimpleNamespace(close=Mock())),
        _history_search_debounce=SimpleNamespace(timer=QtCore.QTimer()),
        tools=SimpleNamespace(
            copy_dialog=ClosingDialog(),
            metadata_dialog=metadata,
            library_manager=ClosingDialog(),
        ),
    )
    lifetime = PanelLifetime()
    shutdown = PanelShutdown(window, lifetime)
    shutdown._prepare()
    assert lifetime.close() == []
    assert not metadata.isVisible()


def test_close_reentry_during_worker_drain_is_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from widgets.panel import shutdown as shutdown_module

    monkeypatch.setattr(shutdown_module, "IS_HOUDINI", False)
    window = SimpleNamespace(
        _archives=SimpleNamespace(commit_import=Mock()),
    )
    lifetime = PanelLifetime()
    shutdown = shutdown_module.PanelShutdown(window, lifetime)
    monkeypatch.setattr(shutdown, "_prepare", Mock())
    monkeypatch.setattr(shutdown, "_save_settings", Mock())
    nested: list[bool] = []
    lifetime.add("worker", lambda: nested.append(shutdown.close()), 0)
    assert shutdown.close()
    assert nested == [False]
    assert shutdown.close()
    window._archives.commit_import.assert_called_once()
