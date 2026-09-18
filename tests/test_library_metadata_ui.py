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


def test_activity_lines_name_the_rename_and_the_video_change() -> None:
    import json

    from widgets.library_metadata.dialog import LibraryMetadataDialog

    line = LibraryMetadataDialog._activity
    team_rename = {
        "operation": "rename",
        "actor": "u1",
        "actor_name": "Kim",
        "occurred_at": "2026-09-17T05:57:11+00:00",
        "changes": {"name": {"before": "fire_presets1", "after": "preset_tmp"}},
    }
    assert line(team_rename).endswith('· Kim · Renamed "fire_presets1" → "preset_tmp"')
    personal_rename = {
        "operation": "hda_key.update",
        "actor": "tester",
        "occurred_at": "2026-09-17T05:57:11.123Z",
        "changes": json.dumps(
            {
                "before": {"name": "a", "category": "sop"},
                "after": {"name": "b", "category": "sop"},
            }
        ),
    }
    assert line(personal_rename).endswith('· tester · Renamed "a" → "b"')
    category_only = {
        **personal_rename,
        "changes": json.dumps(
            {
                "before": {"name": "a", "category": "sop"},
                "after": {"name": "a", "category": "obj"},
            }
        ),
    }
    assert line(category_only).endswith("· Name or category changed")
    assert line({**personal_rename, "operation": "video_info.insert"}).endswith(
        "· Video attached"
    )
    team_video = {
        "operation": "media",
        "actor": "0b3e6d7e-1d0e-4b7a-9d7d-2d2a7f1b6c11",
        "actor_name": None,
        "occurred_at": "2026-09-17T05:57:11+00:00",
        "changes": {"files": {"before": {"video": "v1"}, "after": {"video": "v2"}}},
    }
    assert line(team_video).endswith("· Former member · Video replaced")
