"""About shows the environment a bug report needs and opens links, not a gradient."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtWidgets

from libs.app_metadata import DISPLAY_VERSION, SPONSORS_URL, SUPPORT_URL
from widgets import about_dialog
from widgets.about_dialog import AboutDialog, environment_facts, facts_text


def test_facts_name_the_host_and_fall_back_without_houdini() -> None:
    facts = dict(environment_facts("21.0.512", Path("/cfg")))
    assert facts["Version"] == DISPLAY_VERSION
    assert facts["Houdini"] == "21.0.512"
    assert facts["Settings"] == str(Path("/cfg"))
    assert set(facts) >= {"Qt", "Python", "System"}
    # Outside Houdini (the developer panel, tests) the row says so instead of lying.
    assert "not running" in dict(environment_facts(None, None))["Houdini"]
    assert "Settings" not in dict(environment_facts(None, None))
    assert facts_text([("A", "1"), ("B", "2")]) == "A: 1\nB: 2"


def test_dialog_copies_the_facts_opens_links_and_hides_the_licence(
    app: Any, monkeypatch: Any
) -> None:
    copied: list[str] = []
    opened: list[str] = []
    folders: list[Path] = []
    monkeypatch.setattr(about_dialog, "copy_to_clipboard", copied.append)
    dialog = AboutDialog(
        None,
        houdini_version="21.0.512",
        config_dir=Path("/cfg"),
        open_url=opened.append,
        open_folder=folders.append,
    )
    try:
        assert DISPLAY_VERSION in dialog.label__version.text()
        # The licence is one click away, not an always-open pane.
        assert dialog.plainTextEdit__license.isHidden()
        assert "MIT License" in dialog.plainTextEdit__license.toPlainText()
        assert "PySide6" in dialog.plainTextEdit__license.toPlainText()
        dialog.toolButton__license.setChecked(True)
        assert not dialog.plainTextEdit__license.isHidden()
        dialog.pushButton__copy_info.click()
        assert copied and "Houdini: 21.0.512" in copied[0]
        assert dialog.pushButton__copy_info.text() == "Copied"
        dialog.pushButton__book.click()
        dialog.pushButton__sponsor.click()
        dialog.pushButton__issues.click()
        assert opened == [SUPPORT_URL, SPONSORS_URL, about_dialog.ISSUES_URL]
        # The settings row is a link to the folder, not just text to read out.
        label = dialog.findChild(QtWidgets.QLabel, "label__settings_folder")
        assert label is not None
        label.linkActivated.emit("folder")
        assert folders == [Path("/cfg")]
    finally:
        dialog.deleteLater()
