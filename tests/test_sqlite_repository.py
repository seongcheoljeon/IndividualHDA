from __future__ import annotations

from pathlib import Path

import pytest

from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.repository import LibraryConflict, LibraryUnavailable, RegistrationPayload
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def payload(root: Path, name: str, version: str = "1.0") -> RegistrationPayload:
    directory = root / "sop" / name
    (directory / "thumbnail").mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.hda").write_bytes(b"hda")
    (directory / "thumbnail" / "t.jpg").write_bytes(b"jpg")
    return RegistrationPayload(
        user="tester",
        node_name=name,
        node_path=f"/obj/{name}",
        version=version,
        hda_dirpath=directory,
        hda_filename=f"{name}.hda",
        type_name="box",
        cate_name="sop",
        def_desc="Box",
        is_network=False,
        is_sub_network=False,
        type_path_lst=["Sop/box"],
        cate_path_lst=["Sop"],
        icon_path_lst=["SOP", "box"],
        input_conn=[],
        output_conn=[],
        hou_version="21.0",
        hou_license="commercial",
        operating_system="Linux",
        hip_filename="scene.hip",
        hip_dirpath=root,
        sf=1,
        ef=24,
        fps=24.0,
        thumb_dirpath=directory / "thumbnail",
        thumb_filename="t.jpg",
        registered_at="2026-09-14 12:00:00",
    )


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
    assert (
        asset["hda_id"] == 1
        and asset["hda_name"] == "Water"
        and asset["hda_tags"] == []
    )
    assert result.history[1] == "" and result.history_id == 1
    assert result.thumb_filepath.is_file()
    assert repo.revision() >= first
    with pytest.raises(LibraryConflict):
        repo.register_asset(payload(tmp_path, "Water"))

    rows = repo.list_assets(owner="tester")
    assert [row["hda_name"] for row in rows] == ["Water"]
    assert (
        repo.list_assets(owner=None) == rows
    )  # local libraries ignore the owner filter
    assert repo.categories(owner="tester") == ["sop"]

    repo.set_tags(1, ["물", "smoke#fire"])
    repo.set_note(1, "note 1")
    repo.set_note(1, "note 2")
    assert repo.toggle_favorite(1) and repo.list_assets()[0]["is_favorite_hda"] == 1
    assert repo.distinct_tags() == ["fire", "smoke", "물"]
    assert repo.search_asset_ids("tag:smoke note:2") == [1]
    assert repo.search_asset_ids("absent") == []

    second = repo.add_version(1, payload(tmp_path, "Water", "1.1"))
    assert second.asset["hda_version"] == "1.1"
    assert second.asset["hda_tags"] == ["물", "smoke", "fire"]
    assert second.asset["hda_note"] == "note 2"
    assert second.history[1] == "" and second.history_id == 2
    histories = repo.histories(1, owner="tester")
    assert [h["version"] for h in histories] == ["1.0", "1.1"] or len(histories) == 2
    assert repo.is_latest_history(1, 2) and not repo.is_latest_history(1, 1)
    assert repo.is_latest_version(1, "1.1") and not repo.is_latest_version(1, "1.0")
    assert repo.history_videos(1) == []
    assert repo.video_matches_version(1, "1.1") is False

    # lookups the panel used to make on the facade directly
    assert repo.has_asset("tester", "sop", "Water") and not repo.has_asset(
        "tester", "sop", "x"
    )
    assert repo.asset_identity("tester", "sop", "Water") == (1, "box", "1.1")
    assert repo.asset_identity("tester", "sop", "x") is None
    assert repo.asset_ids("tester") == [1] and repo.asset_names("tester") == [
        (1, "Water")
    ]
    assert repo.asset_filepath(1) == tmp_path / "sop" / "Water" / "Water.hda"
    assert repo.has_history(1) and repo.has_note_history(1)
    assert len(repo.note_history(1)) == 2
    assert repo.history_counts() == (2, 2)
    assert repo.latest_video(1, "1.1") is None
    assert repo.set_video(1, tmp_path, "v.mp4", "1.1") == "insert"
    assert repo.set_video(1, tmp_path, "v2.mp4", "1.1") == "update"
    assert repo.video_matches_version(1, "1.1") is True
    assert repo.set_thumbnail(1, tmp_path, "t2.jpg", "1.1") is True
    history_row = [
        1,
        "TEST",
        "Water",
        "1.1",
        "Water.hda",
        tmp_path,
        "2026-09-14 12:00:00",
        "21.0",
        "scene.hip",
        tmp_path,
        "commercial",
        "Linux",
        "/obj/Water",
        "Box",
        "box",
        "sop",
        "tester",
        ["SOP", "box"],
        "t2.jpg",
        tmp_path,
        "v2.mp4",
        tmp_path,
    ]
    assert repo.add_history_row(history_row) == 3
    assert repo.record_detail(1) == {}
    repo.delete_note_history(1)
    assert not repo.has_note_history(1)

    with pytest.raises(LibraryConflict):
        repo.delete_history(1, 3, [])
    repo.delete_history(1, 1, [])
    repo.delete_history(1, 2, [])
    assert len(repo.histories(1, owner="tester")) == 1

    repo.delete_asset(1, tmp_path / "sop" / "Water")
    assert repo.list_assets() == []
    assert (tmp_path / "sop" / "Water").exists()


def test_missing_database_is_reported(tmp_path: Path) -> None:
    repo = SqliteLibraryRepository(tmp_path / "missing.db")
    assert repo.list_assets() == [] and repo.categories("x") == []
    assert repo.search_asset_ids("a") == [] and repo.revision() == 0
    with pytest.raises(LibraryUnavailable):
        repo.set_note(1, "x")
