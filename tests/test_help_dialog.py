"""Help lists the keys the panel really binds, and says what each tab is for."""

from __future__ import annotations

from typing import Any

from PySide6 import QtGui

from widgets import help_dialog
from widgets.help_dialog import HelpDialog, shortcut_rows


def test_key_names_follow_the_platform(app: Any) -> None:
    rows = dict(shortcut_rows())
    assert set(rows.values()) == {
        description for _, description in help_dialog.SHORTCUTS
    }
    # Native text, so macOS shows its own modifiers instead of "Ctrl".
    save = QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Save).toString(
        QtGui.QKeySequence.SequenceFormat.NativeText
    )
    assert save in rows and rows[save].startswith("Save")
    assert all(name for name in rows)


def test_dialog_opens_the_documentation(app: Any) -> None:
    opened: list[str] = []
    dialog = HelpDialog(None, open_url=opened.append)
    try:
        assert "ihda.db" in dialog.label__intro.text()
        dialog.pushButton__docs.click()
        dialog.pushButton__team.click()
        dialog.pushButton__ask.click()
        assert opened == [
            help_dialog.DOCS_URL,
            help_dialog.TEAM_DOCS_URL,
            help_dialog.ISSUES_URL,
        ]
    finally:
        dialog.deleteLater()
