from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from test_sqlite_repository import payload
from test_team_library import TestTransport
from test_team_library import server as server  # noqa: F401

from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.library_maintenance import Cancelled
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.team.client import BlobCache, HttpCatalog
from libs.team.contracts import Command, Conflict, Forbidden, TeamError, Unavailable
from libs.team.copy_source import PersonalCopySource
from libs.team.copy_transfer import CopyJobStore, CopyTransfer, HttpCopyDestination


@pytest.fixture
def source(tmp_path: Path) -> PersonalCopySource:
    database = tmp_path / "personal.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    repository.register_asset(payload(tmp_path, "Water"))
    repository.set_note(1, "Shared water note")
    repository.set_tags(1, ["water", "물"])
    repository.toggle_favorite(1)
    repository.add_version(1, payload(tmp_path, "Water", "2.0"))
    return PersonalCopySource(database, 1)


def destination(server: Any, tmp_path: Path) -> HttpCopyDestination:
    client, _, _, _, token, project, _ = server
    return HttpCopyDestination(
        HttpCatalog(
            TestTransport(client, token),
            project,
            BlobCache(tmp_path / "cache", project),
        )
    )


def transfer(
    target: HttpCopyDestination, source: PersonalCopySource, tmp_path: Path
) -> CopyTransfer:
    return CopyTransfer(
        target, CopyJobStore(tmp_path / "jobs", target.identity, source.identity())
    )


def test_copy_preserves_versions_metadata_files_and_originals(
    server: Any, source: PersonalCopySource, tmp_path: Path
) -> None:
    target = destination(server, tmp_path)
    before = source.database.read_bytes()
    plan = source.preview()
    job = transfer(target, source, tmp_path)
    result = job.run(plan)
    assert source.database.read_bytes() == before
    assert not result["favorite"] and result["use_count"] == 0
    assert result["note"] == "Shared water note"
    assert set(result["tags"]) == {"water", "물"}
    assert result["asset_uuid"] != plan["values"]["origin"]["asset_uuid"]
    assert result["version"] == "2.0"
    histories = target.catalog.histories(result["id"])
    assert len(histories) == 2
    for history in histories:
        document = history["document"]
        assert (
            document["version_uuid"]
            != document["provenance"]["source_version"]["version_uuid"]
        )
        assert document["metadata"]["hou_version"] == "21.0"
        assert set(document["files"]) == {"asset", "thumbnail"}
    assert job.run(plan) == result
    with pytest.raises(Conflict, match="already been copied"):
        target.execute(Command("copy_asset", values=plan["values"]))
    assert target.catalog.list_assets().total == 1
    journal = job.store.path.read_text()
    assert "Bearer" not in journal
    assert "copy_asset" in journal


def test_lost_commit_response_replays_without_source_files(
    server: Any, source: PersonalCopySource, tmp_path: Path, monkeypatch: Any
) -> None:
    target = destination(server, tmp_path)
    plan = source.preview()
    job = transfer(target, source, tmp_path)
    execute = target.execute

    def lost(command: Command) -> dict[str, Any]:
        execute(command)
        raise Unavailable("Lost response")

    monkeypatch.setattr(target, "execute", lost)
    with pytest.raises(Unavailable):
        job.run(plan)
    assert target.catalog.list_assets().total == 1
    for candidates in plan["paths"].values():
        Path(candidates[0]).unlink(missing_ok=True)
    monkeypatch.setattr(target, "execute", execute)
    assert job.run(plan)["name"] == "Water"
    assert target.catalog.list_assets().total == 1


def test_partial_upload_resumes_and_changed_file_blocks(
    server: Any, source: PersonalCopySource, tmp_path: Path, monkeypatch: Any
) -> None:
    target = destination(server, tmp_path)
    plan = source.preview()
    job = transfer(target, source, tmp_path)
    upload, count = target.upload, 0

    def fail_second(path: Path) -> Any:
        nonlocal count
        count += 1
        if count == 2:
            raise Unavailable("Disconnected")
        return upload(path)

    monkeypatch.setattr(target, "upload", fail_second)
    with pytest.raises(Unavailable):
        job.run(plan)
    assert target.catalog.list_assets().total == 0
    second = Path(list(plan["paths"].values())[1][0])
    original = second.read_bytes()
    second.write_bytes(b"changed")
    with pytest.raises(TeamError, match="changed"):
        job.run(plan)
    second.write_bytes(original)
    assert job.run(plan)["version"] == "2.0"
    assert count == 3  # first upload was reused


def test_missing_optional_files_current_only_and_cancel(
    source: PersonalCopySource,
) -> None:
    plan = source.preview()
    thumbnail = next(
        blob
        for version in plan["values"]["versions"]
        for kind, blob in version["values"]["files"].items()
        if kind == "thumbnail"
    )
    Path(plan["paths"][thumbnail["digest"]][0]).unlink()
    preview = source.preview(all_versions=False)
    assert len(preview["values"]["versions"]) == 1
    assert preview["warnings"]
    assert not source.preview(previews=False)["warnings"]
    cancel = Event()
    cancel.set()
    with pytest.raises(Cancelled):
        source.preview(cancel=cancel)
    asset = preview["values"]["versions"][0]["values"]["files"]["asset"]
    Path(preview["paths"][asset["digest"]][0]).unlink()
    with pytest.raises(TeamError, match="Missing HDA"):
        source.preview()


def test_atomic_rollback_and_validation(
    server: Any, source: PersonalCopySource, tmp_path: Path
) -> None:
    target = destination(server, tmp_path)
    plan = source.preview()
    for candidates in plan["paths"].values():
        target.upload(Path(candidates[0]))
    values = deepcopy(plan["values"])
    values["versions"][1]["values"]["files"]["asset"]["digest"] = "a" * 64
    with pytest.raises(TeamError, match="uploaded"):
        target.execute(Command("copy_asset", values=values))
    assert target.catalog.list_assets().total == 0
    values = deepcopy(plan["values"])
    values["versions"][1]["values"]["version"] = "1.0"
    with pytest.raises(TeamError, match="unique"):
        target.execute(Command("copy_asset", values=values))
    assert (
        target.execute(Command("copy_asset", values=plan["values"]))["version"] == "2.0"
    )


def test_permissions_and_trash_name_conflicts(
    server: Any, source: PersonalCopySource, tmp_path: Path
) -> None:
    target = destination(server, tmp_path)
    result = transfer(target, source, tmp_path).run(source.preview())
    target.execute(
        Command("delete", asset_id=result["id"], expected_revision=result["revision"])
    )
    check = target.check(source.preview()["values"])
    assert check["source_match"]["deleted_at"] and check["name_conflict"]
    client, identities, catalog, owner, _, project, _ = server
    viewer = identities.create_user("viewer")
    catalog.set_member(project, owner, viewer, "viewer")
    backend = HttpCatalog(
        TestTransport(client, identities.issue(viewer)),
        project,
        BlobCache(tmp_path / "viewer", project),
    )
    with pytest.raises(Forbidden):
        HttpCopyDestination(backend)
    with pytest.raises(Forbidden):
        backend.execute(Command("copy_asset", values=source.preview()["values"]))


def test_dialog_preview_copy_and_resume(
    app: Any, server: Any, source: PersonalCopySource, tmp_path: Path
) -> None:
    import time

    from widgets.asset_copy.dialog import CopyAssetDialog

    target = destination(server, tmp_path)
    dialog = CopyAssetDialog(source, tmp_path / "ui")
    dialog.show()
    dialog._connected(target.catalog, {"name": "Studio"})

    def idle() -> None:
        deadline = time.monotonic() + 10
        while dialog._tasks.busy:
            app.processEvents()
            assert time.monotonic() < deadline
            time.sleep(0.005)
        app.processEvents()

    dialog._preview()
    idle()
    assert dialog.tableWidget__versions.rowCount() == 2, (
        dialog.label__copy_status.text()
    )
    assert dialog.pushButton__copy.isEnabled()
    dialog.tableWidget__versions.item(1, 1).setText("2.1")
    dialog._copy()
    idle()
    assert "Copied Water" in dialog.label__copy_status.text()
    assert not dialog.pushButton__copy.isEnabled()
    assert target.catalog.list_assets().items[0]["version"] == "2.1"
    dialog.shutdown()


def test_duplicate_legacy_labels_get_reviewable_unique_names(
    source: PersonalCopySource,
) -> None:
    import sqlite3

    with sqlite3.connect(source.database) as connection:
        connection.execute("UPDATE hda_history SET version='2.0' WHERE id=1")
    plan = source.preview()
    assert [version["values"]["version"] for version in plan["values"]["versions"]] == [
        "2.0",
        "2.0-2",
    ]
    assert plan["warnings"]
    assert [version["origin"]["version"] for version in plan["values"]["versions"]] == [
        "2.0",
        "2.0",
    ]


def test_cancel_upload_then_change_selection(
    server: Any, source: PersonalCopySource, tmp_path: Path, monkeypatch: Any
) -> None:
    target = destination(server, tmp_path)
    job = transfer(target, source, tmp_path)
    cancel = Event()
    upload = target.upload

    def upload_then_cancel(path: Path) -> Any:
        result = upload(path)
        cancel.set()
        return result

    monkeypatch.setattr(target, "upload", upload_then_cancel)
    with pytest.raises(Cancelled):
        job.run(source.preview(), cancel)
    assert target.catalog.list_assets().total == 0
    job.store.discard_unsubmitted()
    assert job.store.load() is None
    cancel.clear()
    monkeypatch.setattr(target, "upload", upload)
    result = job.run(source.preview(all_versions=False, previews=False), cancel)
    assert len(target.catalog.histories(result["id"])) == 1
    with pytest.raises(TeamError, match="Resume first"):
        job.store.discard_unsubmitted()


def test_blob_removed_before_commit_can_be_uploaded_again(
    server: Any, source: PersonalCopySource, tmp_path: Path, monkeypatch: Any
) -> None:
    from sqlalchemy import delete

    from ihda_server import schema as tables

    target = destination(server, tmp_path)
    job = transfer(target, source, tmp_path)
    execute = target.execute

    def cleaned(command: Command) -> dict[str, Any]:
        catalog = server[2]
        with catalog._engine.begin() as connection:
            connection.execute(delete(tables.blobs))
        return execute(command)

    monkeypatch.setattr(target, "execute", cleaned)
    with pytest.raises(TeamError, match="uploaded"):
        job.run(source.preview())
    assert not job.store.load()["submitted"]
    monkeypatch.setattr(target, "execute", execute)
    assert job.run(source.preview())["name"] == "Water"


def test_concurrent_copies_by_different_users_do_not_duplicate(
    server: Any, source: PersonalCopySource, tmp_path: Path
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    target = destination(server, tmp_path)
    plan = source.preview()
    for paths in plan["paths"].values():
        target.upload(Path(paths[0]))
    _, identities, catalog, owner, _, project, _ = server
    editor = identities.create_user("editor")
    catalog.set_member(project, owner, editor, "editor")

    def copy(user: str) -> Any:
        try:
            return catalog.execute(
                project, user, Command("copy_asset", values=plan["values"])
            )
        except Conflict as error:
            return error

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(copy, [owner, editor]))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert sum(isinstance(result, Conflict) for result in results) == 1
    assert target.catalog.list_assets().total == 1


def test_closing_dialog_drains_upload_and_leaves_resume_journal(
    app: Any, server: Any, source: PersonalCopySource, tmp_path: Path, monkeypatch: Any
) -> None:
    import time

    from widgets.asset_copy.dialog import CopyAssetDialog

    target = destination(server, tmp_path)
    dialog = CopyAssetDialog(source, tmp_path / "closing")
    dialog._connected(target.catalog, {"name": "Studio"})
    dialog._preview()
    deadline = time.monotonic() + 10
    while dialog._tasks.busy:
        app.processEvents()
        assert time.monotonic() < deadline
        time.sleep(0.005)
    prepared = dialog._prepared
    started, release = Event(), Event()
    original = prepared["transfer"].destination.upload

    def slow_upload(path: Path) -> Any:
        started.set()
        assert release.wait(5)
        return original(path)

    monkeypatch.setattr(prepared["transfer"].destination, "upload", slow_upload)
    dialog._copy()
    assert started.wait(5)
    dialog.reject()
    assert dialog._tasks.busy
    release.set()
    dialog.shutdown()
    assert not dialog._tasks.busy
    assert target.catalog.list_assets().total == 0
    assert prepared["transfer"].store.load() is not None
