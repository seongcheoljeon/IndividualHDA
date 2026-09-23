from __future__ import annotations

import logging
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import public
from libs.log_handler import install_file_logging, uninstall_file_logging

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def fresh_file_logging() -> Any:
    """The file handler is process-wide on purpose; each test starts without one."""

    uninstall_file_logging()
    yield
    uninstall_file_logging()


def load_panel_script(
    monkeypatch: pytest.MonkeyPatch, panel_factory: Any
) -> dict[str, Any]:
    """Exec the Python Panel script with a fake hou and a fake main module."""
    script = (
        ET.parse(ROOT / "python_panels" / "individualHDA.pypanel").findtext(".//script")
        or ""
    )
    fake_hou = SimpleNamespace(
        getenv=lambda key: str(ROOT) if key == "IHDA_ROOT" else "",
        isUIAvailable=lambda: True,
        applicationVersion=lambda: (21, 0, 559),
    )
    monkeypatch.setitem(sys.modules, "hou", fake_hou)
    monkeypatch.setitem(
        sys.modules, "main", SimpleNamespace(IndividualHDA=panel_factory)
    )
    tab = SimpleNamespace(name=lambda: "panel1")
    namespace: dict[str, Any] = {"kwargs": {"paneTab": tab}, "__name__": "ihda_pypanel"}
    exec(compile(script, "individualHDA.pypanel", "exec"), namespace)
    return namespace


def test_file_logging_is_idempotent_and_plain(tmp_path: Path) -> None:
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        path = install_file_logging(tmp_path / "logs")
        assert install_file_logging(tmp_path / "logs") == path
        assert len(root.handlers) == len(before) + 1
        logging.getLogger("ihda.test").warning("<font color=red>보고</font> done")
        for handler in root.handlers:
            handler.flush()
        text = path.read_text(encoding="utf-8")
        assert "보고 done" in text and "<font" not in text
    finally:
        uninstall_file_logging()
    assert list(root.handlers) == before
    shutil.rmtree(tmp_path / "logs")  # closed: removable on Windows too


def test_panel_script_returns_fallback_widget_on_failure(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(public.Paths, "config_dirpath", tmp_path)

    def broken(*, embedded: bool) -> Any:
        raise RuntimeError("database is locked")

    ns = load_panel_script(monkeypatch, broken)
    widget = ns["onCreateInterface"]()
    labels = [w.text() for w in widget.findChildren(type(widget.children()[1]))]
    assert any("database is locked" in text for text in labels)
    log_text = (tmp_path / "logs" / "ihda.log").read_text(encoding="utf-8")
    assert "Individual HDA failed to start" in log_text and "RuntimeError" in log_text
    ns["onDestroyInterface"]()  # nothing registered: must not raise


def test_panel_script_tracks_one_panel_per_tab(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from PySide6 import QtWidgets

    monkeypatch.setattr(public.Paths, "config_dirpath", tmp_path)
    created: list[Any] = []

    class FakePanel(QtWidgets.QWidget):
        def __init__(self, *, embedded: bool) -> None:
            super().__init__()
            self.drained = False
            created.append(self)

        def shutdown_for_host(self) -> None:
            self.drained = True

    ns = load_panel_script(monkeypatch, FakePanel)
    first = ns["onCreateInterface"]()
    ns["kwargs"]["paneTab"] = SimpleNamespace(name=lambda: "panel2")
    second = ns["onCreateInterface"]()
    assert first is not second and set(ns["_panels"]) == {"panel1", "panel2"}
    ns["onDestroyInterface"]()  # current tab is panel2
    assert second.drained and not first.drained and set(ns["_panels"]) == {"panel1"}
    ns["kwargs"]["paneTab"] = SimpleNamespace(name=lambda: "unknown")
    ns["onDestroyInterface"]()  # falls back to the hidden survivor
    assert first.drained and not ns["_panels"]


def test_unreadable_database_becomes_library_unavailable(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from libs.repository import LibraryUnavailable
    from main import IndividualHDA
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    preference = Preference()
    preference.data_dirpath = str(tmp_path)
    preference._Preference__pref_settings.save_cfg_dict_to_file()
    preference.close()
    (tmp_path / "ihda.db").write_bytes(b"this is not a database")
    with pytest.raises(LibraryUnavailable):
        IndividualHDA()


def test_log_pane_colours_the_level_against_its_own_palette() -> None:
    """The old near-white info colour disappeared on a light host theme."""
    import logging as log

    from PySide6 import QtGui

    from libs.log_handler import level_html

    dark, light = QtGui.QPalette(), QtGui.QPalette()
    dark.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#2b2b2b"))
    light.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#ffffff"))
    # Ordinary lines carry no colour, so they use the pane's own text colour.
    assert level_html("saved", log.INFO, dark) == "saved"
    assert level_html("saved", log.INFO, light) == "saved"
    assert level_html("gone", log.ERROR, dark) != level_html("gone", log.ERROR, light)
    assert "<b>" in level_html("stop", log.CRITICAL, dark)
    # A path with a bracket is text, not markup.
    assert "&lt;unknown&gt;" in level_html("<unknown>", log.WARNING, dark)
