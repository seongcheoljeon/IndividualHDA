from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from support.team import create_asset
from support.team import server as server  # noqa: F401

from libs.database_migrations import migrate
from libs.database_migrations_v4 import migrate as migrate_v4


def test_personal_v4_upgrade_is_additive_and_retryable(tmp_path: Path) -> None:
    database = tmp_path / "old.db"
    with sqlite3.connect(database) as connection:
        migrate_v4(connection, database)
        connection.execute("INSERT INTO users VALUES('old','old@local','2020-01-01')")
        connection.execute("INSERT INTO hda_category VALUES('sop','old')")
        connection.execute("INSERT INTO hda_key VALUES(12,'Water','sop','old')")
        connection.execute(
            "INSERT INTO hda_info VALUES(1,12,'1',1,9,'missing.hda','/missing','2020-01-01','2020-01-02')"
        )
        connection.commit()
        migrate(connection, database)
        identity = connection.execute(
            "SELECT uuid FROM asset_identity WHERE asset_id=12"
        ).fetchone()[0]
        UUID(identity)
        assert connection.execute(
            "SELECT favorite,use_count FROM asset_user_preferences"
        ).fetchone() == (1, 9)
        assert (
            connection.execute(
                "SELECT initial_registration_datetime FROM hda_info"
            ).fetchone()[0]
            == "2020-01-01"
        )
        assert connection.execute("SELECT message FROM migration_reports").fetchall()
        migrate(connection, database)
        assert (
            connection.execute(
                "SELECT uuid FROM asset_identity WHERE asset_id=12"
            ).fetchone()[0]
            == identity
        )
        assert len(list(tmp_path.glob("*.pre-v6-*.bak"))) == 1


def test_personal_failed_upgrade_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import libs.database_migrations as migrations

    database = tmp_path / "old.db"
    with sqlite3.connect(database) as connection:
        migrate_v4(connection, database)
        original = migrations.install_v5

        def fail(connection: sqlite3.Connection) -> None:
            original(connection)
            raise RuntimeError("injected")

        monkeypatch.setattr(migrations, "install_v5", fail)
        with pytest.raises(RuntimeError, match="injected"):
            migrate(connection, database)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='asset_identity'"
        ).fetchone()
        monkeypatch.setattr(migrations, "install_v5", original)
        migrate(connection, database)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6


def test_server_v1_upgrade_preserves_documents_and_seeds_members(
    server: Any, tmp_path: Path
) -> None:
    from sqlalchemy import select, update
    from support.team import TestTransport

    from ihda_server import lifecycle_schema as state
    from ihda_server import schema as tables
    from ihda_server.migrations import upgrade
    from libs.team.client import BlobCache, HttpCatalog

    client, identity, catalog, owner, token, project, _ = server
    backend = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    _, asset = create_asset(backend, tmp_path)
    viewer = identity.create_user("member")
    catalog.set_member(project, owner, viewer, "viewer")
    with catalog._engine.begin() as connection:
        # The old lifecycle/tracking tables did not exist in schema v1.
        if connection.dialect.name == "postgresql":
            from ihda_server.tracking import ServerTrackingConnection

            ServerTrackingConnection(connection)
            connection.exec_driver_sql(
                "ALTER TABLE team_asset_state DROP CONSTRAINT fk_current_version"
            )
        from ihda_server.tracking_schema import TABLES

        for table in reversed(TABLES):
            table.drop(connection)
        for table in (
            state.file_refs,
            state.preferences,
            state.audit,
            state.version_state,
            state.asset_state,
        ):
            table.drop(connection)
        document = {
            key: value
            for key, value in asset.items()
            if key
            not in {
                "asset_uuid",
                "version_uuid",
                "preference_revision",
                "use_count",
                "last_used_at",
            }
        }
        document.update(favorite=True, metadata={"custom": {"unknown": "retained"}})
        connection.execute(update(tables.assets).values(document=document))
        connection.execute(update(tables.history).values(document=document))
        connection.execute(update(tables.versions).values(version=1))
    upgrade(catalog._engine)
    upgraded = backend.get_asset(asset["id"])
    UUID(upgraded["asset_uuid"])
    assert upgraded["metadata"] == {"custom": {"unknown": "retained"}}
    assert (
        upgraded["favorite"]
        and catalog.get_asset(project, viewer, asset["id"])["favorite"]
    )
    assert (
        catalog.histories(project, owner, asset["id"])[0]["document"]["version_uuid"]
        == upgraded["version_uuid"]
    )
    upgrade(catalog._engine)
    assert backend.get_asset(asset["id"]) == upgraded
    from sqlalchemy import inspect

    from ihda_server.database import SCHEMA_VERSION

    with catalog._engine.connect() as connection:
        assert (
            connection.execute(select(tables.versions.c.version)).scalar_one()
            == SCHEMA_VERSION
        )
        # v4 indexes are created by the upgrade, not by create_all on old tables.
        # The PostgreSQL fixture works in a per-test schema; ask the inspector there.
        schema = (
            connection.get_execution_options().get("schema_translate_map", {}).get(None)
        )
        names = {
            index["name"]
            for index in inspect(connection).get_indexes("team_assets", schema=schema)
        }
        assert "ix_team_assets_order" in names
        names = {
            index["name"]
            for index in inspect(connection).get_indexes(
                "team_audit_events", schema=schema
            )
        }
        assert "ix_team_audit_lookup" in names


def test_legacy_pending_requires_review_and_keeps_file(tmp_path: Path) -> None:
    from libs.team.contracts import TeamError
    from libs.team.pending import PendingCommand

    path = tmp_path / "pending.json"
    payload = {"operation": "metadata", "asset_id": 1, "values": {"note": "old draft"}}
    path.write_text(json.dumps(payload))
    pending = PendingCommand(path)
    with pytest.raises(TeamError, match="pre-upgrade"):
        pending.load()
    assert pending.legacy() == payload and path.exists()
    pending.archive_legacy()
    assert pending.load() is None
    assert json.loads(next(tmp_path.glob("*.pre-v2-*.json")).read_text()) == payload


def test_trash_is_retained_and_relocatable_in_backup(tmp_path: Path) -> None:
    from support.personal import payload

    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.library_backups import create_backup, validate_backup
    from libs.library_management import LocalManagement
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    first = repository.register_asset(payload(tmp_path, "Water"))
    repository.add_version(first.asset.hda_id, payload(tmp_path, "Water", "1.1"))
    management = LocalManagement(database)
    management.change(
        {"asset_id": first.asset.hda_id, "history_id": first.history_id}, "delete"
    )
    management.change({"asset_id": first.asset.hda_id, "history_id": None}, "delete")
    backup = create_backup(database, tmp_path / "sop", "Trash retained")
    assert "verified" in validate_backup(backup)
    assert first.thumb_filepath.exists()
    assert len(management.trash()) == 1


def test_file_integrity_survives_description_changes(tmp_path: Path) -> None:
    from support.personal import payload

    from libs.database.lifecycle import PersonalLifecycle, inspect_files
    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    first = repository.register_asset(payload(tmp_path, "Water"))
    with SQLite3DatabaseAPI(database) as db:
        inspect_files(db._connect)
        digest = db._connect.execute(
            "SELECT digest FROM version_files WHERE kind='asset'"
        ).fetchone()[0]
        with db.transaction():
            PersonalLifecycle(db._connect).details(
                first.history_id, {"description": "Only documentation changed"}
            )
        assert (
            db._connect.execute(
                "SELECT digest FROM version_files WHERE kind='asset'"
            ).fetchone()[0]
            == digest
        )
        (first.asset.hda_dirpath / first.asset.hda_filename).write_bytes(b"corruption")
        inspect_files(db._connect)
        assert (
            db._connect.execute(
                "SELECT status FROM version_files WHERE kind='asset'"
            ).fetchone()[0]
            == "mismatch"
        )
