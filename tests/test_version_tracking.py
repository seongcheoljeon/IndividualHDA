from __future__ import annotations

import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from support.personal import payload
from support.team import TestTransport, create_asset
from support.team import server as server  # noqa: F401

from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.database.tracking import local_tracking
from libs.library_management import LocalManagement
from libs.library_metadata import new_identity, utc_now
from libs.scene_outbox import SceneOutbox
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.team.client import BlobCache, HttpCatalog
from libs.team.contracts import Command, Forbidden, TeamError


@pytest.fixture
def personal(tmp_path: Path) -> tuple[Path, SqliteLibraryRepository, Any, Any]:
    database = tmp_path / "library.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    first = repository.register_asset(payload(tmp_path, "Water"))
    other = repository.register_asset(payload(tmp_path, "Foam"))
    return database, repository, first, other


def check(version: str) -> dict[str, Any]:
    return {
        "request_id": new_identity(),
        "operation": "check",
        "values": {
            "version_uuid": version,
            "houdini_version": "21.0",
            "os": "Linux",
            "scope": "Instantiate and cook",
            "result": "passed",
            "notes": "Manual smoke test",
            "checked_at": utc_now(),
        },
    }


def test_manual_checks_append_corrections_and_replay(personal: Any) -> None:
    database, repository, asset, other = personal
    uuid = repository.version_identity(asset.asset.hda_id)
    gateway = LocalManagement(database)
    request = check(uuid)
    gateway.record_check(asset.asset.hda_id, request)
    gateway.record_check(asset.asset.hda_id, request)
    correction = check(uuid)
    correction["values"].update(result="failed", supersedes=request["request_id"])
    gateway.record_check(asset.asset.hda_id, correction)
    details = gateway.details(asset.asset.hda_id)
    reports = details["tracking"]["checks"]
    assert len(reports) == 2
    assert reports[0]["document"]["supersedes"] == request["request_id"]
    assert (
        len(
            [
                event
                for event in details["events"]
                if event["operation"] == "manual_check"
            ]
        )
        == 2
    )
    changed = deepcopy(request)
    changed["values"]["notes"] = "different"
    with pytest.raises(ValueError, match="different content"):
        gateway.record_check(asset.asset.hda_id, changed)
    with pytest.raises(ValueError, match="different asset"):
        gateway.record_check(other.asset.hda_id, request)
    foreign_correction = check(repository.version_identity(other.asset.hda_id))
    foreign_correction["values"]["supersedes"] = request["request_id"]
    with pytest.raises(ValueError, match="Correction"):
        gateway.record_check(other.asset.hda_id, foreign_correction)


def test_dependencies_survive_old_client_save_and_target_purge(personal: Any) -> None:
    database, repository, asset, other = personal
    gateway = LocalManagement(database)
    other_id = other.asset.hda_id
    version = gateway.details(other_id)["versions"][0]
    dependency = {
        "kind": "asset",
        "target": "Water",
        "version": "1.0",
        "source": "manual",
    }
    gateway.save_details(other_id, version, {"dependencies": [dependency]})
    with SQLite3DatabaseAPI(database) as db, db.transaction():
        tracking = local_tracking(db._connect)
        target = repository.version_identity(asset.asset.hda_id)
        source = repository.version_identity(other_id)
        assert tracking.dependencies(source)[0]["version_uuid"] == target
        db._connect.execute(
            "UPDATE hda_key SET name='Renamed' WHERE id=?", (asset.asset.hda_id,)
        )
        tracking.replace_dependencies(source, [dependency])
        assert tracking.dependencies(source)[0]["version_uuid"] == target
    assert gateway.dependents({"asset_id": asset.asset.hda_id})
    gateway.change({"asset_id": asset.asset.hda_id}, "delete")
    gateway.change({"asset_id": asset.asset.hda_id}, "purge")
    document = gateway.details(other_id)["versions"][0]["document"]
    assert document["dependencies"][0]["resolution"] == "missing"
    assert document["dependencies"][0]["target"] == "Water"


def test_current_pointer_rejects_cross_asset_and_trashed_version(personal: Any) -> None:
    database, repository, asset, other = personal
    uuid = repository.version_identity(other.asset.hda_id)
    with SQLite3DatabaseAPI(database) as db:
        with pytest.raises(sqlite3.IntegrityError, match="belong"), db.transaction():
            db._connect.execute(
                "UPDATE asset_identity SET current_version_uuid=? WHERE asset_id=?",
                (uuid, asset.asset.hda_id),
            )
        with pytest.raises(sqlite3.IntegrityError, match="current"), db.transaction():
            db._connect.execute(
                "UPDATE version_identity SET deleted_at=? WHERE uuid=?",
                (utc_now(), uuid),
            )


def test_scene_outbox_is_durable_scoped_and_idempotent(
    personal: Any, tmp_path: Path
) -> None:
    database, repository, asset, _ = personal
    uuid = repository.version_identity(asset.asset.hda_id)
    path = tmp_path / "outbox.db"
    outbox = SceneOutbox(path)
    outbox.enqueue("another-account", {"version_uuid": uuid})
    values = {
        "version_uuid": uuid,
        "scene_key": "unsaved:session",
        "node_path": "/obj/water",
        "houdini_version": "21",
        "os": "Linux",
    }
    outbox.enqueue("local", values)
    delivered = []

    def send(body: dict[str, Any]) -> None:
        with SQLite3DatabaseAPI(database) as db, db.transaction():
            delivered.append(
                local_tracking(db._connect).execute(
                    "tester", body["request_id"], "scene", body["values"]
                )
            )

    def lost_response(body: dict[str, Any]) -> None:
        send(body)
        raise OSError("Connection lost after commit")

    assert outbox.flush("local", lost_response) == 1
    assert SceneOutbox(path).flush("local", send) == 0
    assert delivered[0] == delivered[1]
    first = LocalManagement(database).details(asset.asset.hda_id)["tracking"]["scenes"][
        0
    ]
    outbox.enqueue(
        "local",
        {
            **values,
            "scene_key": "/show/shot.hip",
            "scene_path": "/show/shot.hip",
            "previous_scene_key": "unsaved:session",
        },
    )
    outbox.flush("local", send)
    scenes = LocalManagement(database).details(asset.asset.hda_id)["tracking"]["scenes"]
    assert len(scenes) == 1 and scenes[0]["first_seen"] == first["first_seen"]
    assert scenes[0]["document"]["scene_path"] == "/show/shot.hip"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT namespace FROM pending").fetchall() == [
            ("another-account",)
        ]


def test_server_tracking_permissions_scope_receipts_and_pages(
    server: Any, tmp_path: Path
) -> None:
    client, identity, catalog, owner, token, project, _ = server
    backend = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    _, asset = create_asset(backend, tmp_path)
    assert backend.tracking_supported()
    request = check(asset["version_uuid"])
    receipt = backend.tracking_execute(request)
    assert backend.tracking_execute(request) == receipt
    assert len(backend.tracking_read("checks", asset["asset_uuid"])) == 1
    viewer = identity.create_user("observer")
    catalog.set_member(project, owner, viewer, "viewer")
    with pytest.raises(Forbidden):
        catalog.tracking_execute(project, viewer, check(asset["version_uuid"]))
    scene = {
        "request_id": new_identity(),
        "operation": "scene",
        "values": {
            "version_uuid": asset["version_uuid"],
            "client_id": new_identity(),
            "scene_key": "/show/a.hip",
            "scene_path": "/show/a.hip",
            "node_path": "/obj/water",
            "houdini_version": "21",
            "os": "Windows",
        },
    }
    catalog.tracking_execute(project, viewer, scene)
    assert (
        catalog.tracking_read(project, owner, "scenes", asset["asset_uuid"])[0]["actor"]
        == viewer
    )
    another = catalog.create_project(owner, "Other")["id"]
    assert catalog.tracking_read(another, owner, "checks", asset["asset_uuid"]) == []
    with pytest.raises(TeamError, match="unavailable"):
        catalog.tracking_execute(another, owner, check(asset["version_uuid"]))
    for _ in range(3):
        backend.tracking_execute(check(asset["version_uuid"]))
    pages = [
        catalog.tracking_read(
            project, owner, "checks", asset["asset_uuid"], offset=offset, limit=2
        )
        for offset in (0, 2)
    ]
    assert len({row["id"] for page in pages for row in page}) == 4


def test_copy_checks_keep_provenance_and_remap_internal_dependencies(
    personal: Any, server: Any, tmp_path: Path
) -> None:
    from libs.team.copy_source import PersonalCopySource
    from libs.team.copy_transfer import CopyJobStore, CopyTransfer, HttpCopyDestination

    database, repository, asset, _ = personal
    second = repository.add_version(
        asset.asset.hda_id, payload(tmp_path, "Water", "2.0")
    )
    gateway = LocalManagement(database)
    versions = gateway.details(asset.asset.hda_id)["versions"]
    gateway.save_details(
        asset.asset.hda_id,
        versions[0],
        {"dependencies": [{"kind": "asset", "target": "Water", "version": "1.0"}]},
    )
    original_check = check(
        repository.version_identity(asset.asset.hda_id, second.history_id)
    )
    gateway.record_check(asset.asset.hda_id, original_check)
    client, _, _, _, token, project, _ = server
    backend = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    target = HttpCopyDestination(backend)
    source = PersonalCopySource(database, asset.asset.hda_id)
    transfer = CopyTransfer(
        target, CopyJobStore(tmp_path / "jobs", target.identity, source.identity())
    )
    copied = transfer.run(source.preview())
    report = backend.tracking_read("checks", copied["asset_uuid"])[0]
    assert report["document"]["method"] == "imported_manual"
    assert report["document"]["provenance"]["check_id"] == original_check["request_id"]
    history = backend.histories(copied["id"])
    dependency = history[0]["document"]["dependencies"][0]
    assert dependency["library_uuid"] == project
    assert dependency["version_uuid"] == history[1]["document"]["version_uuid"]
    assert dependency["resolution"] == "resolved"


def test_team_registration_recovery_replays_lost_reply(
    server: Any, tmp_path: Path
) -> None:
    from libs.team.pending import PendingCommand
    from libs.team.registration_recovery import TeamRegistrationRecovery

    client, _, _, _, token, project, _ = server
    backend = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    recovery = TeamRegistrationRecovery(tmp_path / "registrations", backend.namespace)
    path = tmp_path / "asset.hda"
    path.write_bytes(b"asset bytes")
    identity = recovery.prepare(path, "Water", "sop", "1.0", {}, None, None, "")
    pending = PendingCommand(tmp_path / "pending.json")

    class LostReply:
        upload = backend.upload

        def execute(self, command: Command) -> Any:
            backend.execute(command)
            raise OSError("lost reply")

    with pytest.raises(OSError):
        recovery.retry(identity, LostReply(), pending)
    assert pending.load().request_id == identity
    with pytest.raises(TeamError, match="Submitted"):
        recovery.discard(identity)
    result = recovery.retry(identity, backend, pending)
    assert recovery.retry(identity, backend, pending) == result
    assert pending.load() is None
    assert len(backend.histories(result["id"])) == 1
    assert path.exists()  # External files never belong to the capture journal.


def test_personal_receipt_content_and_cleanup_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from test_registration_workflow import Capture, setup

    from libs.asset_lifecycle import LocalAssetLifecycle
    from libs.repository import LibraryConflict, LibraryError

    repository, request, service = setup(tmp_path)
    request = replace(request, operation_id=new_identity())
    with monkeypatch.context() as patch:
        patch.setattr(
            repository,
            "_register_asset",
            lambda *args: (_ for _ in ()).throw(LibraryError("interrupted")),
        )
        with pytest.raises(LibraryError):
            service.register(request, Capture())
    recovery = repository.registration_recovery()
    with pytest.raises(LibraryConflict, match="different content"):
        service.register(replace(request, description="different"), Capture())
    result = recovery.retry(
        request.operation_id, LocalAssetLifecycle(repository, SimpleNamespace())
    )
    assert service.register(request, Capture()).history_id == result.history_id
    with pytest.raises(ValueError, match="committed"):
        recovery.discard(request.operation_id)
    assert (request.hda_dirpath / request.hda_filename).is_file()


def test_v5_migration_preserves_ambiguous_scene_links(personal: Any) -> None:
    from libs.database_migrations import migrate
    from libs.database_migrations_v4 import migrate as migrate_v4
    from libs.database_v5 import install as install_v5

    database, repository, first, second = personal
    # Extract the actual v5 trigger definition from a v5 database.
    with sqlite3.connect(":memory:") as template:
        migrate_v4(template, Path(":memory:"))
        install_v5(template)
        trigger = template.execute(
            "SELECT sql FROM sqlite_master WHERE name='v5_version_identity'"
        ).fetchone()[0]
    with SQLite3DatabaseAPI(database) as db:
        for item in (first, second):
            data = item.asset
            db.insert_hda_node_location_record(
                hda_key_id=data.hda_id,
                hip_filename="shot.hip",
                hip_dirpath=Path("/show"),
                hda_filename=data.hda_filename,
                hda_dirpath=data.hda_dirpath,
                parent_node_path="/obj",
                node_type="box",
                node_cate="sop",
                node_name=data.hda_name,
                node_ver="1.0",
                hou_version="21",
                hou_license="commercial",
                operating_sys="Linux",
                sf=1.0,
                ef=24.0,
                fps=24.0,
            )
    with sqlite3.connect(database) as connection:
        for (name,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'v6_%'"
        ).fetchall():
            connection.execute(f'DROP TRIGGER "{name}"')
        connection.execute(trigger)
        for name in (
            "version_dependencies",
            "version_checks",
            "scene_usages",
            "tracking_requests",
            "registration_jobs",
        ):
            connection.execute(f'DROP TABLE "{name}"')
        connection.execute("DROP INDEX idx_scene_record_version")
        for name in ("library_uuid", "asset_uuid", "version_uuid", "link_status"):
            connection.execute(
                f'ALTER TABLE hda_node_location_record DROP COLUMN "{name}"'
            )
        # Duplicate the first history exactly; matching by version/file must not guess.
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(hda_history)")
            if row[1] != "id"
        ]
        names = ",".join(columns)
        connection.execute(
            f"INSERT INTO hda_history ({names}) SELECT {names} FROM hda_history WHERE id=?",
            (first.history_id,),
        )
        connection.execute("PRAGMA user_version=5")
        connection.commit()
        migrate(connection, database)
        rows = connection.execute(
            "SELECT node_name,version_uuid,link_status FROM hda_node_location_record ORDER BY id"
        ).fetchall()
        assert rows[0] == ("Water", None, "unresolved")
        assert rows[1][0] == "Foam" and rows[1][1] and rows[1][2] == "resolved"
        migrate(connection, database)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
    assert repository.record_detail(2).version_uuid == rows[1][1]
    assert len(list(database.parent.glob("*.pre-v6-*.bak"))) == 1


def test_server_v2_migration_backfills_dependencies(
    server: Any, tmp_path: Path
) -> None:
    from sqlalchemy import select, update

    from ihda_server import lifecycle_schema as state
    from ihda_server import schema as tables
    from ihda_server.migrations import upgrade
    from ihda_server.tracking import ServerTrackingConnection
    from ihda_server.tracking_schema import TABLES

    client, _, catalog, _, token, project, _ = server
    backend = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    _, asset = create_asset(backend, tmp_path)
    with catalog._engine.begin() as connection:
        ServerTrackingConnection(connection)
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "ALTER TABLE team_asset_state DROP CONSTRAINT fk_current_version"
            )
        for table in reversed(TABLES):
            table.drop(connection)
        details = {
            "dependencies": [{"kind": "asset", "target": "Water", "version": "1.0"}]
        }
        connection.execute(update(state.version_state).values(details=details))
        connection.execute(update(tables.versions).values(version=2))
    upgrade(catalog._engine)
    upgrade(catalog._engine)
    assert (
        backend.histories(asset["id"])[0]["document"]["dependencies"][0]["version_uuid"]
        == asset["version_uuid"]
    )
    with catalog._engine.connect() as connection:
        assert connection.execute(select(tables.versions.c.version)).scalar_one() == 3


def test_tracking_form_and_recovery_dialog(app: Any, personal: Any) -> None:
    import time

    from PySide6 import QtWidgets
    from test_library_metadata_ui import wait_idle

    from widgets.library_metadata.dialog import LibraryMetadataDialog
    from widgets.library_metadata.recovery import RegistrationRecoveryDialog

    database, _, first, _ = personal
    parent = QtWidgets.QWidget()
    gateway = LocalManagement(database)
    dialog = LibraryMetadataDialog(gateway, parent, asset_id=first.asset.hda_id)
    wait_idle(app, dialog)
    form = dialog._tracking
    form.lineEdit__houdini_version.setText("21.0")
    form.lineEdit__os.setText("Linux")
    form.lineEdit__scope.setText("Cook test")
    form._record()
    wait_idle(app, dialog)
    assert len(form.pages["checks"]) == 1 and form.pending is None
    dialog.shutdown()
    dialog.close()
    retried = []
    identity = new_identity()
    recovery = RegistrationRecoveryDialog(
        lambda: [{"id": identity, "phase": "published", "error": "Lost response"}],
        retried.append,
        lambda identity: None,
        parent,
    )
    deadline = time.monotonic() + 5
    while recovery._tasks.busy:
        app.processEvents()
        assert time.monotonic() < deadline
        time.sleep(0.005)
    recovery.listWidget__jobs.setCurrentRow(0)
    recovery.retry()
    while recovery._tasks.busy or recovery._reload:
        app.processEvents()
        assert time.monotonic() < deadline
        time.sleep(0.005)
    assert retried == [identity]
    recovery.shutdown()
    recovery.close()
    parent.close()


def test_scene_record_updates_only_the_matching_version(
    personal: Any, tmp_path: Path
) -> None:
    database, repository, first, _ = personal
    second = repository.add_version(
        first.asset.hda_id, payload(tmp_path, "Water", "2.0")
    )
    with SQLite3DatabaseAPI(database) as db:
        for item in (first, second, first):
            data = item.asset
            db.insert_hda_node_location_record(
                hda_key_id=data.hda_id,
                hip_filename="shot.hip",
                hip_dirpath=Path("/show"),
                hda_filename=data.hda_filename,
                hda_dirpath=data.hda_dirpath,
                parent_node_path="/obj",
                node_type="box",
                node_cate="sop",
                node_name="Water",
                node_ver=data.hda_version,
                hou_version="21",
                hou_license="commercial",
                operating_sys="Linux",
                sf=1.0,
                ef=24.0,
                fps=24.0,
                version_uuid=repository.version_identity(data.hda_id, item.history_id),
            )
        rows = db._connect.execute(
            "SELECT node_version,version_uuid FROM hda_node_location_record ORDER BY id"
        ).fetchall()
        assert rows == [
            ("1.0", repository.version_identity(1, first.history_id)),
            ("2.0", repository.version_identity(1, second.history_id)),
        ]


def test_scene_queue_keeps_invalid_record_without_blocking_newer_ones(
    tmp_path: Path,
) -> None:
    outbox = SceneOutbox(tmp_path / "queue.db")
    invalid = outbox.enqueue("team", {"version_uuid": "removed"})
    outbox.enqueue("team", {"version_uuid": "active"})
    delivered = []

    def send(body: dict[str, Any]) -> None:
        if body["request_id"] == invalid:
            raise ValueError("Version removed")
        delivered.append(body)

    assert outbox.flush("team", send) == 1
    assert len(delivered) == 1


def test_activity_history_does_not_choose_an_unresolved_current_version(
    personal: Any,
) -> None:
    database, repository, first, _ = personal
    with SQLite3DatabaseAPI(database) as db, db.transaction():
        db._connect.execute(
            "UPDATE asset_identity SET current_version_uuid=NULL WHERE asset_id=?",
            (first.asset.hda_id,),
        )
    repository.add_history_row(first.history)
    assert repository.version_identity(first.asset.hda_id) is None


def test_discard_preserves_a_replaced_dangling_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_registration_workflow import Capture, setup

    from libs.repository import LibraryError

    repository, request, service = setup(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(
            repository,
            "_register_asset",
            lambda *args: (_ for _ in ()).throw(LibraryError("interrupted")),
        )
        with pytest.raises(LibraryError):
            service.register(request, Capture())
    path = request.hda_dirpath / request.hda_filename
    path.unlink()
    path.symlink_to(tmp_path / "missing-competitor")
    recovery = repository.registration_recovery()
    with pytest.raises(ValueError, match="symbolic link"):
        recovery.discard(recovery.jobs()[0]["id"])
    assert path.is_symlink()


def test_copy_rejects_incomplete_check_before_writing(personal: Any) -> None:
    from libs.team.copy_source import PersonalCopySource

    database, repository, first, _ = personal
    LocalManagement(database).record_check(
        first.asset.hda_id, check(repository.version_identity(first.asset.hda_id))
    )
    values = PersonalCopySource(database, first.asset.hda_id).preview()["values"]
    del values["versions"][0]["checks"][0]["actor"]
    with pytest.raises(TeamError, match="actor"):
        Command("copy_asset", values=values).validate()


def test_copy_omits_empty_tracking_fields_for_an_older_server(
    personal: Any, server: Any, tmp_path: Path
) -> None:
    from libs.team.copy_source import PersonalCopySource
    from libs.team.copy_transfer import CopyJobStore, CopyTransfer, HttpCopyDestination

    database, _, first, _ = personal
    client, _, _, _, token, project, _ = server

    class LegacyTransport(TestTransport):
        def request(self, method: str, path: str, payload: Any = None) -> Any:
            if path == "/health":
                return {"api_version": 2, "capabilities": ["asset_copy"]}
            if payload and payload.get("operation") == "copy_asset":
                assert all(
                    set(version) == {"origin", "values"}
                    for version in payload["values"]["versions"]
                )
            return super().request(method, path, payload)

    backend = HttpCatalog(
        LegacyTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    target = HttpCopyDestination(backend)
    source = PersonalCopySource(database, first.asset.hda_id)
    transfer = CopyTransfer(
        target, CopyJobStore(tmp_path / "jobs", target.identity, source.identity())
    )
    result = transfer.run(source.preview())
    assert result["name"] == "Water"


def test_personal_catalog_returns_current_uuid_after_activity(
    personal: Any, tmp_path: Path
) -> None:
    from support.names import Names

    from libs.team.personal import PersonalCatalog

    database, repository, first, _ = personal
    uuid = repository.version_identity(first.asset.hda_id)
    repository.add_history_row(first.history)
    backend = PersonalCatalog(database, tmp_path / "assets", "tester", Names)
    assert backend.get_asset(first.asset.hda_id)["version_uuid"] == uuid
