from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtGui
from support.names import Names

from libs.asset_commands import delete_history
from libs.asset_contracts import AssetData, HistoryData
from libs.asset_rename import build_rename_plan, rename_asset
from libs.database.rename_repository import SQLiteRenameRepository
from libs.operation_journal import durable_operation
from libs.record_codec import decode_record
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.thumbnail_cache import ThumbnailCache
from model.ihda_history_model import HistoryModel


def seed(db: SQLite3DatabaseAPI, directory: Path) -> AssetData:
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
                HistoryData(
                    hda_id=1,
                    comment="create",
                    org_hda_name="Old",
                    version=version + ".0",
                    ihda_filename=f"v{version}.hda",
                    ihda_dirpath=directory,
                    hou_version="21.0",
                    hip_filename="scene.hip",
                    hip_dirpath=directory,
                    hda_license="commercial",
                    os="Linux",
                    node_old_path="/obj/Old",
                    node_def_desc="Box",
                    node_type_name="box",
                    node_category="sop",
                    userid="user",
                    icon=["SOP", "box"],
                    thumb_filename=f"v{version}.png",
                    thumb_dirpath=directory / "thumbnail",
                    video_filename="v1.mp4",
                    video_dirpath=directory / "video",
                )
            )
            == 1
        )
    return decode_record(
        AssetData,
        {
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
        },
    )


def test_rename_preserves_old_media_versions_in_database_and_model(
    app: Any, tmp_path: Path
) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        data = seed(db, tmp_path / "Old")
        before = db.get_hda_history(user_id="user")
        model = HistoryModel(items=before)
        plan = build_rename_plan(data, "New", Names(), rename_video=False)
        rename_asset(SQLiteRenameRepository(db), plan, operations=durable_operation)
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
                assert (
                    getattr(record, directory) / getattr(record, filename)
                ).is_file()
                counterpart = next(
                    row for row in changed if row.hist_id == record.hist_id
                )
                assert getattr(counterpart, directory) == getattr(record, directory)
                assert getattr(counterpart, filename) == getattr(record, filename)
        assert {row.video_filename for row in after} == {"v1.mp4"}


def test_history_deletion_keeps_surviving_file_references(tmp_path: Path) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        data = seed(db, tmp_path / "Old")
        folder = data.hda_dirpath
        files = [
            folder / "v1.hda",
            folder / "thumbnail" / "v1.png",
            folder / "video" / "v1.mp4",
        ]
        delete_history(db, 1, 1)
        assert all(path.exists() for path in files)
        delete_history(db, 1, 2)
        assert (
            files[0].exists() and files[1].exists()
        )  # Trash retains every version file
        assert files[2].exists()  # still used by current video_info and latest history
        with pytest.raises(ValueError, match="most recent"):
            delete_history(db, 1, 3)
        assert (folder / "v2.hda").exists()


def test_external_media_path_is_not_renamed(tmp_path: Path) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        data = seed(db, tmp_path / "Old")
        external = tmp_path / "shared"
        external.mkdir()
        (external / "v2.png").write_text("shared thumbnail")
        data = replace(data, thumbnail_dirpath=external)
        plan = build_rename_plan(data, "New", Names(), rename_video=False)
        assert plan.thumbnail_directory == external
        assert plan.thumbnail_filename == "v2.png"
        assert all(not move.source.is_relative_to(external) for move in plan.moves)


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
    import libs.archive_transfer as module
    from libs.archive_transfer import ArchiveTransfer

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
    from widgets.panel.media_actions import PanelMediaActions

    store = AssetStore()
    store.reset(
        [
            decode_record(AssetData, {"hda_id": 1, "hda_name": "Encoded"}),
            decode_record(AssetData, {"hda_id": 2, "hda_name": "Selected"}),
        ]
    )
    selection = SelectionState()
    selection.asset.id, selection.asset.row = 2, 1
    selection.asset.data = store.rows[1]
    rows, history, stored = [], [], []
    # Every hda_history row becomes a version (v6 trigger), so a preview must not
    # write one; the only way to would be through this repository call.
    repository = SimpleNamespace(
        set_video=lambda *args: stored.append(args) or "insert",
        add_history_row=lambda row: history.append(row.hda_id),
    )

    class MediaOwner(PanelMediaActions, SimpleNamespace):
        pass

    owner = MediaOwner(
        _assets=store,
        _selection=selection,
        _repository=repository,
        _change_hda_data=lambda **kwargs: rows.append(kwargs["row"]),
        _remove_preview_dir=lambda **kwargs: True,
        _loading_close=lambda: None,
    )
    owner.bindings = SimpleNamespace(
        models=SimpleNamespace(assets=store),
        selection=SimpleNamespace(state=selection),
        session=SimpleNamespace(
            repository=repository, require_repository=lambda: repository
        ),
        queries=SimpleNamespace(_change_hda_data=owner._change_hda_data),
        presentation=SimpleNamespace(_loading_close=lambda: None),
    )
    PanelMediaActions._finish_video(
        owner, 1, "1.0", tmp_path, "encoded.mp4", tmp_path / "preview"
    )
    assert rows == [0, 0]
    assert history == []  # Preview changes do not create synthetic HDA versions.
    assert stored == [(1, tmp_path, "encoded.mp4", "1.0")]


def test_asset_row_lookup_uses_current_index_after_insertion() -> None:
    from types import SimpleNamespace

    from libs.asset_store import AssetStore
    from widgets.panel.library_queries import PanelLibraryQueries

    store = AssetStore()
    store.reset(
        [decode_record(AssetData, {"hda_id": 1, "hda_name": "Z", "item_row": 0})]
    )
    store.insert(decode_record(AssetData, {"hda_id": 2, "hda_name": "A"}))
    owner = PanelLibraryQueries()
    owner.bindings = SimpleNamespace(
        models=SimpleNamespace(assets=store),
        management=SimpleNamespace(_get_hda_id_row_map=lambda: store.id_rows),
    )
    assert PanelLibraryQueries._get_ihda_data_by_id(owner, 1, "item_row") == 1
