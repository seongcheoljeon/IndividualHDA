"""Scene usage commits and identities are repository responsibilities."""

from dataclasses import replace
from pathlib import Path

import pytest
from support.personal import payload

from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.repository import LibraryError
from libs.scene_contracts import SceneRecordInput
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def test_scene_usage_update_returns_existing_identity_and_rolls_back_bad_version(
    tmp_path: Path,
) -> None:
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    request = payload(tmp_path, "Water")
    asset = repository.register_asset(request).asset
    usage = SceneRecordInput(
        hda_key_id=asset.hda_id,
        hip_filename="scene.hip",
        hip_dirpath=tmp_path,
        hda_filename=request.hda_filename,
        hda_dirpath=request.hda_dirpath,
        parent_node_path="/obj/geo1",
        node_type="sample",
        node_cate="sop",
        node_name="Water",
        node_ver="1.0",
        hou_version="21.0",
        hou_license="commercial",
        operating_sys="test",
        sf=1,
        ef=24,
        fps=24,
        version_uuid=None,
    )
    first = repository.record_scene_usage(usage)
    second = repository.record_scene_usage(replace(usage, node_name="Water2"))
    assert second != first
    assert repository.record_scene_usage(replace(usage, fps=30)) == first
    with pytest.raises(LibraryError):
        repository.record_scene_usage(replace(usage, version_uuid="missing", fps=60))
    with SQLite3DatabaseAPI(database) as connection:
        assert (
            connection._connect.execute(
                "SELECT fps FROM hda_node_location_record WHERE id=?", (first,)
            ).fetchone()[0]
            == 30
        )
    assert len(repository.scene_record_files("tester")) == 2
    assert repository.scene_records()


def test_local_scene_delivery_owns_transactions_and_does_not_resend(
    tmp_path: Path,
) -> None:
    from libs.database.tracking import deliver_local_scene_usage
    from libs.scene_outbox import SceneOutbox

    database = tmp_path / "library.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    asset = repository.register_asset(payload(tmp_path, "Water")).asset
    outbox = SceneOutbox(tmp_path / "outbox.db")
    outbox.enqueue(
        "local:" + str(database.resolve()),
        {
            "version_uuid": repository.version_identity(asset.hda_id),
            "scene_key": "shot.hip",
            "scene_path": str(tmp_path / "shot.hip"),
            "node_path": "/obj/Water",
            "houdini_version": "21",
            "os": "Linux",
        },
    )
    assert deliver_local_scene_usage(database, "tester", outbox) == 0
    assert deliver_local_scene_usage(database, "tester", outbox) == 0
    with SQLite3DatabaseAPI(database) as db:
        assert (
            db._connect.execute("SELECT COUNT(*) FROM scene_usages").fetchone()[0] == 1
        )
