from __future__ import annotations

from pathlib import Path

import pytest
from support.personal import payload

from libs.asset_contracts import AssetIdentity, AssetName, HistoryCounts, HistoryData
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.repository import LibraryConflict, LibraryUnavailable
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def test_repository_roundtrip(tmp_path: Path) -> None:
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repo = SqliteLibraryRepository(database)
    repo.ensure_user("tester")
    repo.ensure_user("tester")  # idempotent
    first = repo.revision()

    result = repo.register_asset(payload(tmp_path, "Water"))
    asset = result.asset
    assert asset.hda_id == 1 and asset.hda_name == "Water" and asset.hda_tags == ()
    # The row says what happened; a blank comment made every history opaque.
    assert result.history.comment == "NODE (INSERT)" and result.history_id == 1
    assert result.thumb_filepath.is_file()
    assert repo.revision() >= first
    with pytest.raises(LibraryConflict):
        repo.register_asset(payload(tmp_path, "Water"))

    rows = repo.list_assets(owner="tester")
    assert [row.hda_name for row in rows] == ["Water"]
    assert (
        repo.list_assets(owner=None) == rows
    )  # local libraries ignore the owner filter
    assert repo.categories(owner="tester") == ["sop"]

    repo.set_tags(1, ["물", "smoke#fire"])
    repo.set_note(1, "note 1")
    repo.set_note(1, "note 2")
    assert repo.toggle_favorite(1) and repo.list_assets()[0].is_favorite_hda == 1
    assert repo.distinct_tags() == ["fire", "smoke", "물"]
    assert repo.search_asset_ids("tag:smoke note:2") == [1]
    assert repo.search_asset_ids("absent") == []

    second = repo.add_version(1, payload(tmp_path, "Water", "1.1"))
    assert second.asset.hda_version == "1.1"
    assert second.asset.hda_tags == (
        "물",
        "smoke",
        "fire",
    )
    assert second.asset.hda_note == "note 2"
    assert second.history.comment == "NODE (UPDATE)" and second.history_id == 2
    histories = repo.histories(1, owner="tester")
    assert [h.version for h in histories] == ["1.0", "1.1"] or len(histories) == 2
    assert repo.is_latest_history(1, 2) and not repo.is_latest_history(1, 1)
    with SQLite3DatabaseAPI(database) as db:
        assert db.is_ihda_lastest_version(hda_key_id=1, version="1.1")
        assert not db.is_ihda_lastest_version(hda_key_id=1, version="1.0")
    assert repo.history_videos(1) == []
    assert repo.video_matches_version(1, "1.1") is False

    # lookups the panel used to make on the facade directly
    assert repo.has_asset("tester", "sop", "Water") and not repo.has_asset(
        "tester", "sop", "x"
    )
    assert repo.asset_identity("tester", "sop", "Water") == AssetIdentity(
        asset_id=1, node_type="box", version="1.1"
    )
    assert repo.asset_identity("tester", "sop", "x") is None
    assert repo.asset_ids("tester") == [1] and repo.asset_names("tester") == [
        AssetName(asset_id=1, name="Water")
    ]
    assert repo.asset_filepath(1) == tmp_path / "sop" / "Water" / "Water.hda"
    assert repo.has_history(1)
    assert len(repo.note_history(1)) == 2
    assert repo.history_counts() == HistoryCounts(versions=2, notes=2)
    assert repo.latest_video(1, "1.1") is None
    assert repo.set_video(1, tmp_path, "v.mp4", "1.1") == "insert"
    assert repo.set_video(1, tmp_path, "v2.mp4", "1.1") == "update"
    assert repo.video_matches_version(1, "1.1") is True
    assert repo.set_thumbnail(1, tmp_path, "t2.jpg", "1.1") is True
    history_row = HistoryData(
        hda_id=1,
        comment="TEST",
        org_hda_name="Water",
        version="1.1",
        ihda_filename="Water.hda",
        ihda_dirpath=tmp_path,
        reg_time="2026-09-14 12:00:00",
        hou_version="21.0",
        hip_filename="scene.hip",
        hip_dirpath=tmp_path,
        hda_license="commercial",
        os="Linux",
        node_old_path="/obj/Water",
        node_def_desc="Box",
        node_type_name="box",
        node_category="sop",
        userid="tester",
        icon=["SOP", "box"],
        thumb_filename="t2.jpg",
        thumb_dirpath=tmp_path,
        video_filename="v2.mp4",
        video_dirpath=tmp_path,
    )
    assert repo.add_history_row(history_row) == 3
    assert repo.record_detail(1) is None
    with SQLite3DatabaseAPI(database) as db:
        db.delete_hda_note_history(1)
    assert repo.note_history(1) == []

    with pytest.raises(LibraryConflict):
        repo.delete_history(1, 2, [])
    repo.delete_history(1, 1, [])
    repo.delete_history(1, 3, [])
    assert len(repo.histories(1, owner="tester")) == 1

    repo.delete_asset(1, tmp_path / "sop" / "Water")
    assert repo.list_assets() == []
    assert (tmp_path / "sop" / "Water").exists()
    # Trash keeps the hda_key row, so the empty category must vanish by query,
    # not by the hard-delete trigger; restoring brings it back.
    assert repo.categories(owner="tester") == []
    from libs.library_management import LocalManagement

    LocalManagement(database).change({"asset_id": 1, "history_id": None}, "restore")
    assert repo.categories(owner="tester") == ["sop"]
    LocalManagement(database).change({"asset_id": 1, "history_id": None}, "delete")
    assert repo.categories(owner="tester") == []


def test_missing_database_is_reported(tmp_path: Path) -> None:
    repo = SqliteLibraryRepository(tmp_path / "missing.db")
    assert repo.list_assets() == [] and repo.categories("x") == []
    assert repo.search_asset_ids("a") == [] and repo.revision() == 0
    with pytest.raises(LibraryUnavailable):
        repo.set_note(1, "x")


def test_history_comment_keeps_the_kind_and_appends_the_description(
    tmp_path: Path,
) -> None:
    """A refactor swapped the INSERT/UPDATE marker for the optional description.

    The description is empty unless the user ticks "Add a change description",
    so every history row went blank and no longer said what it recorded.
    """
    from dataclasses import replace

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repo = SqliteLibraryRepository(database)
    repo.ensure_user("tester")

    added = repo.register_asset(payload(tmp_path, "Water"))
    assert added.history.comment == "NODE (INSERT)"

    updated = repo.add_version(
        added.asset.hda_id,
        replace(
            payload(tmp_path, "Water", "1.1"),
            description="reduced the substep count",
        ),
    )
    assert updated.history.comment == "NODE (UPDATE) reduced the substep count"


def test_activity_rows_come_from_audit_events_not_history(tmp_path: Path) -> None:
    from support.names import Names

    from libs.asset_rename import build_rename_plan

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repo = SqliteLibraryRepository(database)
    repo.ensure_user("tester")
    repo.register_asset(payload(tmp_path, "Water"))
    assert repo.activity("tester") == []

    video_dir = tmp_path / "sop" / "Water" / "video"
    video_dir.mkdir()
    assert repo.set_video(1, video_dir, "Water_v1.0.mp4", "1.0") == "insert"
    # Re-recording keeps the same path; the trigger is silent, the row is not.
    assert repo.set_video(1, video_dir, "Water_v1.0.mp4", "1.0") == "update"
    plan = build_rename_plan(repo.list_assets()[0], "Ocean", Names(), rename_video=True)
    repo.rename_asset(plan)

    rows = repo.activity("tester")
    assert [row.comment for row in rows] == [
        "VIDEO (INSERT)",
        "VIDEO (UPDATE)",
        "NAME (CHANGE) Water → Ocean",
    ]
    assert all(not row.is_version and row.hist_id == 0 for row in rows)
    assert {row.userid for row in rows} == {"tester"}
    assert {row.org_hda_name for row in rows} == {"Ocean"}
    # Activity never became a version.
    assert [row.comment for row in repo.histories(1, "tester")] == ["NODE (INSERT)"]
    assert repo.history_counts().versions == 1
    assert repo.activity("someone-else") == []


def test_trashed_assets_are_invisible_to_reads_but_keep_their_name(
    tmp_path: Path,
) -> None:
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repo = SqliteLibraryRepository(database)
    repo.ensure_user("tester")
    asset = repo.register_asset(payload(tmp_path, "Water")).asset
    repo.set_tags(asset.hda_id, ["fire"])
    assert repo.distinct_tags() == ["fire"]
    assert [row.asset_id for row in repo.asset_icons(owner="tester")] == [1]
    assert len(repo.history_thumbnails(owner="tester")) == 1

    repo.delete_asset(asset.hda_id, asset.hda_dirpath)

    # Every read that lists assets or their parts forgets the trashed one...
    assert repo.distinct_tags() == []
    assert repo.asset_icons(owner="tester") == []
    assert repo.history_thumbnails(owner="tester") == []
    assert repo.asset_names(owner="tester") == []
    assert repo.categories(owner="tester") == []
    with SQLite3DatabaseAPI(database) as db:
        assert db.get_hda_key_id(category="sop", name="Water", user_id="tester") is None
        assert db.get_count_hda_key(user_id="tester") == 0
    # ...but the name stays taken (UNIQUE survives until purge) and says why.
    assert repo.has_asset("tester", "sop", "Water")
    with pytest.raises(LibraryConflict, match="Trash"):
        repo.register_asset(payload(tmp_path, "Water"))


def test_import_helpers_and_usage_count(tmp_path: Path) -> None:
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repo = SqliteLibraryRepository(database)
    repo.ensure_user("tester")
    registered = payload(tmp_path, "Water")
    asset = repo.register_asset(registered).asset
    assert repo.asset_available(asset.hda_id) and not repo.asset_available(999)
    assert repo.import_note(asset.hda_id) is None
    repo.set_note(asset.hda_id, "how to use it")
    assert repo.import_note(asset.hda_id) == "how to use it"
    assert repo.import_license(asset.hda_id, "1.0", "tester") == registered.hou_license
    repo.record_use(asset.hda_id)
    repo.record_use(asset.hda_id)
    assert repo.list_assets()[0].hda_load_count == 2
    repo.record_use(999)  # unknown asset: logged, never raised
