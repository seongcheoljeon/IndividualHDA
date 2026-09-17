from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from support.personal import payload


def wait_idle(app: Any, dialog: Any) -> None:
    deadline = time.monotonic() + 8
    while dialog._tasks.busy or dialog._reload_pending:
        app.processEvents()
        if time.monotonic() > deadline:
            raise AssertionError("Dialog worker did not finish")
        time.sleep(0.005)
    app.processEvents()


def test_metadata_and_trash_use_existing_local_data(app: Any, tmp_path: Path) -> None:
    from PySide6 import QtWidgets

    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.library_management import LocalManagement
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
    from widgets.library_metadata.dialog import LibraryMetadataDialog

    database = tmp_path / "library.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    asset = repository.register_asset(payload(tmp_path, "Water"))
    gateway = LocalManagement(database)
    parent = QtWidgets.QWidget()
    dialog = LibraryMetadataDialog(gateway, parent, asset_id=asset.asset.hda_id)
    dialog.show()
    wait_idle(app, dialog)
    assert dialog.comboBox__version.count() == 1
    dialog.textEdit__description.setPlainText("Improved water surface")
    dialog._save()
    wait_idle(app, dialog)
    assert dialog.textEdit__description.toPlainText() == "Improved water surface"
    assert (
        gateway.details(asset.asset.hda_id)["versions"][0]["document"]["description"]
        == "Improved water surface"
    )
    dialog.close()
    repository.delete_asset(asset.asset.hda_id, asset.asset.hda_dirpath)
    trash = LibraryMetadataDialog(gateway, parent)
    trash.show()
    wait_idle(app, trash)
    assert trash.tableWidget__items.rowCount() == 1
    trash.tableWidget__items.selectRow(0)
    trash._change("restore")
    wait_idle(app, trash)
    assert trash.tableWidget__items.rowCount() == 0
    assert repository.list_assets()
    trash.close()
    parent.close()
