from __future__ import annotations

from typing import Any

import pytest
from PySide6 import QtWidgets
from support.team import TestTransport
from support.team import server as server  # noqa: F401


def wait_idle(app: Any, dialog: Any) -> None:
    from test_qt import wait_until

    wait_until(app, lambda: not dialog._tasks.busy)


def test_members_dialog_lists_edits_and_confirms_removal(
    app: Any, monkeypatch: pytest.MonkeyPatch, server: Any
) -> None:
    from widgets.library_connection.members import COLUMNS, MembersDialog

    client, identities, catalog, owner, token, project_id, _ = server
    artist = identities.create_user("artist")
    catalog.set_member(project_id, owner, artist, "viewer")
    dialog = MembersDialog(
        TestTransport(client, token), {"id": project_id, "name": "Studio"}
    )
    try:
        wait_idle(app, dialog)
        table = dialog.tableWidget__members
        assert [
            table.horizontalHeaderItem(i).text() for i in range(table.columnCount())
        ] == list(COLUMNS)
        assert table.rowCount() == 2
        assert [table.item(r, 0).text() for r in range(2)] == ["artist", "owner"]
        assert table.item(0, 2).text() == "viewer"
        # Nothing selected yet: no ID, so Save stays off.
        assert not dialog.pushButton__save_member.isEnabled()
        table.setCurrentCell(0, 0)
        assert dialog.lineEdit__member_id.text() == artist
        assert dialog.comboBox__member_role.currentText() == "viewer"
        assert dialog.pushButton__save_member.isEnabled()
        # A partial ID is refused inline instead of after a round trip.
        dialog.lineEdit__member_id.setText("not-an-id")
        assert not dialog.pushButton__save_member.isEnabled()
        assert "full ID" in dialog.label__member_status.text()
        dialog.lineEdit__member_id.setText(artist)
        assert dialog.pushButton__save_member.isEnabled()
        dialog.comboBox__member_role.setCurrentText("editor")
        dialog.pushButton__save_member.click()
        wait_idle(app, dialog)
        assert {m["user_id"]: m["role"] for m in catalog.members(project_id, owner)}[
            artist
        ] == "editor"
        assert table.item(0, 2).text() == "editor"
        # Removing access asks first; No keeps the member.
        answers = [
            QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes,
        ]
        questions: list[str] = []

        def question(*args: Any, **kwargs: Any) -> Any:
            questions.append(args[2])
            return answers.pop(0)

        monkeypatch.setattr(QtWidgets.QMessageBox, "question", question)
        dialog.lineEdit__member_id.setText(artist)
        dialog.comboBox__member_role.setCurrentText("Remove access")
        dialog.pushButton__save_member.click()
        wait_idle(app, dialog)
        assert questions == ["Remove artist from Studio?"]
        assert len(catalog.members(project_id, owner)) == 2
        dialog.pushButton__save_member.click()
        wait_idle(app, dialog)
        assert len(questions) == 2
        assert [m["user_id"] for m in catalog.members(project_id, owner)] == [owner]
        assert table.rowCount() == 1
    finally:
        dialog.shutdown()
        dialog.deleteLater()
