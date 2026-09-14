from __future__ import annotations
from pathlib import Path
from typing import Any
import pytest
from PySide6 import QtGui
from libs.asset_commands import delete_history
from libs.asset_rename import build_rename_plan, rename_asset
from libs.database.rename_repository import SQLiteRenameRepository
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.thumbnail_cache import ThumbnailCache
from model.ihda_history_model import HistoryModel
from test_solid_contracts import Names


def seed(db: SQLite3DatabaseAPI, directory: Path) -> dict[str, Any]:
    (directory / "thumbnail").mkdir(parents=True)
    (directory / "video").mkdir()
    for file in (
        "v1.hda",
        "v2.hda",
        "thumbnail/v1.png",
        "thumbnail/v2.png",
        "video/v1.mp4",
    ):
        (directory / file).write_text(file)
    db.insert_users("user", "user@example.com")
    db.insert_hda_category("sop", "user")
    db.insert_hda_key("Old", "sop", "user")
    db.insert_hda_info(1, "2.0", filename="v2.hda", dirpath=directory)
    db.insert_thumbnail_info(1, directory / "thumbnail", "v2.png", "2.0")
    db.insert_video_info(1, directory / "video", "v1.mp4", "1.0")
    for version in ("1", "1", "2"):
        assert (
            db.insert_hda_history(
                [
                    1,
                    "create",
                    "Old",
                    version + ".0",
                    f"v{version}.hda",
                    directory,
                    None,
                    "21.0",
                    "scene.hip",
                    directory,
                    "commercial",
                    "Linux",
                    "/obj/Old",
                    "Box",
                    "box",
                    "sop",
                    "user",
                    ["SOP", "box"],
                    f"v{version}.png",
                    directory / "thumbnail",
                    "v1.mp4",
                    directory / "video",
                ]
            )
            == 1
        )
    return {
        "hda_id": 1,
        "hda_name": "Old",
        "hda_version": "2.0",
        "hda_dirpath": directory,
        "hda_filename": "v2.hda",
        "node_old_path": "/obj/Old",
        "thumbnail_dirpath": directory / "thumbnail",
        "thumbnail_filename": "v2.png",
        "video_dirpath": directory / "video",
        "video_filename": "v1.mp4",
    }


def test_rename_preserves_old_media_versions_in_database_and_model(
    app: Any, tmp_path: Path
) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        data = seed(db, tmp_path / "Old")
        before = db.get_hda_history(user_id="user")
        model = HistoryModel(items=before)
        plan = build_rename_plan(data, "New", Names(), rename_video=False)
        rename_asset(SQLiteRenameRepository(db), plan)
        changed = model.relocate_asset_paths(1, plan.moves)
        after = db.get_hda_history(user_id="user")
        assert plan.video_directory == tmp_path / "New" / "video"
        assert plan.video_filename == "v1.mp4"
        assert db.get_video_info(1) == plan.video_directory / plan.video_filename
        for record in after:
            for directory, filename in (
                ("ihda_dirpath", "ihda_filename"),
                ("thumb_dirpath", "thumb_filename"),
                ("video_dirpath", "video_filename"),
            ):
                assert (record[directory] / record[filename]).is_file()
                counterpart = next(
                    row for row in changed if row["hist_id"] == record["hist_id"]
                )
                assert counterpart[directory] == record[directory]
                assert counterpart[filename] == record[filename]
        assert {row["video_filename"] for row in after} == {"v1.mp4"}


def test_history_deletion_keeps_surviving_file_references(tmp_path: Path) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        data = seed(db, tmp_path / "Old")
        folder = data["hda_dirpath"]
        files = [
            folder / "v1.hda",
            folder / "thumbnail" / "v1.png",
            folder / "video" / "v1.mp4",
        ]
        delete_history(db, 1, 1, files)
        assert all(path.exists() for path in files)
        delete_history(db, 1, 2, files)
        assert not files[0].exists() and not files[1].exists()
        assert files[2].exists()  # still used by current video_info and latest history
        with pytest.raises(ValueError, match="most recent"):
            delete_history(db, 1, 3, [folder / "v2.hda"])
        assert (folder / "v2.hda").exists()


def test_external_media_path_is_not_renamed(tmp_path: Path) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        data = seed(db, tmp_path / "Old")
        external = tmp_path / "shared"
        external.mkdir()
        (external / "v2.png").write_text("shared thumbnail")
        data["thumbnail_dirpath"] = external
        plan = build_rename_plan(data, "New", Names(), rename_video=False)
        assert plan.thumbnail_directory == external
        assert plan.thumbnail_filename == "v2.png"
        assert all(not source.is_relative_to(external) for source, _ in plan.moves)


def test_thumbnail_shutdown_drops_queued_results_and_new_requests(
    app: Any, tmp_path: Path
) -> None:
    path = tmp_path / "thumb.png"
    image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGB32)
    image.fill(0)
    image.save(str(path))
    cache = ThumbnailCache(QtGui.QPixmap(8, 8))
    cache.set_path(1, path)
    cache.get(1)
    cache.shutdown()
    events = []
    cache.changed.connect(events.append)
    app.processEvents()
    assert not events and cache.decoded_count == 0
    cache.get(1)
    assert cache.pending_count == 0


@pytest.mark.parametrize("capacity,limit", [(0, 64), (-1, 64), (1, 0)])
def test_thumbnail_cache_rejects_invalid_limits(
    app: Any, capacity: int, limit: int
) -> None:
    with pytest.raises(ValueError):
        ThumbnailCache(QtGui.QPixmap(8, 8), capacity=capacity, byte_limit=limit)


def test_failed_staging_cleanup_keeps_recovery_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.archive_transfer import ArchiveTransfer
    import libs.archive_transfer as module

    service = ArchiveTransfer(tmp_path / "assets", tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    service.stage = stage

    def blocked(path: Path) -> None:
        raise PermissionError("file is in use")

    monkeypatch.setattr(module.shutil, "rmtree", blocked)
    with pytest.raises(PermissionError):
        service.discard_import()
    assert service.stage == stage
    assert stage.exists()


def test_video_completion_uses_encoded_asset_when_selection_changes(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace
    from libs.asset_store import AssetStore
    from libs.domain import SelectionState
    from widgets.panel.media_actions import MediaActionsMixin

    store = AssetStore()
    store.reset(
        [{"hda_id": 1, "hda_name": "Encoded"}, {"hda_id": 2, "hda_name": "Selected"}]
    )
    selection = SelectionState()
    selection.asset.id, selection.asset.row = 2, 1
    selection.asset.data = store.rows[1]
    rows, history, closed = [], [], []
    database = SimpleNamespace(
        get_video_info=lambda **kwargs: None,
        insert_video_info=lambda **kwargs: 1,
        close=lambda: closed.append(True),
    )
    owner = SimpleNamespace(
        _assets=store,
        _selection=selection,
        _db_filepath=tmp_path / "ihda.db",
        _db_api_wrap=lambda path: database,
        _change_hda_data=lambda **kwargs: rows.append(kwargs["row"]),
        _insert_hist_db_from_curt_hist_data=lambda **kwargs: history.append(
            kwargs["data"]["hda_id"]
        ),
        _remove_preview_dir=lambda **kwargs: True,
        _loading_close=lambda: None,
    )
    MediaActionsMixin._finish_video(
        owner, 1, "1.0", tmp_path, "encoded.mp4", tmp_path / "preview"
    )
    assert rows == [0, 0]
    assert history == [1]
    assert closed == [True]


def test_asset_row_lookup_uses_current_index_after_insertion() -> None:
    from types import SimpleNamespace
    from libs.asset_store import AssetStore
    from widgets.panel.library_queries import LibraryQueriesMixin

    store = AssetStore()
    store.reset([{"hda_id": 1, "hda_name": "Z", "item_row": 0}])
    store.insert({"hda_id": 2, "hda_name": "A"})
    owner = SimpleNamespace(_assets=store, _get_hda_id_row_map=lambda: store.id_rows)
    assert LibraryQueriesMixin._get_ihda_data_by_id(owner, 1, "item_row") == 1
