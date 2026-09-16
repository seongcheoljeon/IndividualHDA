from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from ihda_server.backup_files import verify_bundle
from ihda_server.backup_service import BackupService
from ihda_server.database import SCHEMA_VERSION
from ihda_server.schema import metadata
from ihda_server.storage_lock import storage_lock
from libs.team.contracts import Blob, Command, Unavailable


class MemoryBackupDatabase:
    def __init__(self, content: bytes) -> None:
        self.restored = False
        self.state = {
            "schema_version": SCHEMA_VERSION,
            "tables": {
                name: {"rows": 0, "sha256": hashlib.sha256(b"").hexdigest()}
                for name in metadata.tables
            },
            "blobs": {hashlib.sha256(content).hexdigest(): len(content)},
        }

    @contextmanager
    def snapshot(self) -> Iterator[tuple[str, dict[str, Any]]]:
        yield "snapshot", self.state

    def dump(self, snapshot: str, output: Path) -> None:
        output.write_bytes(b"test database dump")

    @contextmanager
    def restore_target(self) -> Iterator[None]:
        if self.restored:
            raise ValueError("Target not empty")
        yield

    def restore(self, dump: Path) -> None:
        self.restored = True

    def inspect_restored(self) -> dict[str, Any]:
        return self.state


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[Path, MemoryBackupDatabase, Path]:
    content = b"HDA backup bytes"
    database = MemoryBackupDatabase(content)
    blobs = tmp_path / "source"
    digest = hashlib.sha256(content).hexdigest()
    path = blobs / digest[:2] / digest
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    target = tmp_path / "backup"
    BackupService(database).create(blobs, target)
    return target, database, blobs


def test_bundle_restore_and_non_overwrite(bundle: Any, tmp_path: Path) -> None:
    backup, database, source = bundle
    manifest = verify_bundle(backup)
    assert manifest["complete"]
    destination = tmp_path / "restored"
    result = BackupService(database).restore(backup, destination)
    assert result["status"] == "restore_verified"
    for digest in database.state["blobs"]:
        assert (destination / digest[:2] / digest).read_bytes() == (
            source / digest[:2] / digest
        ).read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        BackupService(database).create(source, backup)
    with pytest.raises(ValueError, match="new path"):
        BackupService(database).restore(backup, destination)


@pytest.mark.parametrize(
    "damage", ["missing", "corrupt", "omitted", "traversal", "incomplete", "extra"]
)
def test_rejects_damaged_bundles_before_restore(
    bundle: Any, tmp_path: Path, damage: str
) -> None:
    backup, database, _ = bundle
    manifest = json.loads((backup / "manifest.json").read_text())
    blob_name = next(name for name in manifest["files"] if name.startswith("blobs/"))
    if damage == "missing":
        (backup / blob_name).unlink()
    elif damage == "corrupt":
        (backup / blob_name).write_bytes(b"corrupt")
    elif damage == "omitted":
        del manifest["files"][blob_name]
    elif damage == "traversal":
        manifest["files"]["../outside"] = manifest["files"].pop(blob_name)
    elif damage == "incomplete":
        manifest["complete"] = False
    else:
        (backup / "extra").write_text("unexpected")
    (backup / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        BackupService(database).restore(backup, tmp_path / "restore")
    assert not database.restored
    assert not (tmp_path / "restore").exists()


def test_missing_source_and_failed_dump_never_publish(
    bundle: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    _, database, source = bundle
    digest = next(iter(database.state["blobs"]))
    (source / digest[:2] / digest).unlink()
    with pytest.raises(ValueError, match="Missing"):
        BackupService(database).create(source, tmp_path / "missing")
    assert not (tmp_path / "missing").exists()

    def fail(snapshot: str, output: Path) -> None:
        output.write_bytes(b"partial")
        raise RuntimeError("dump failed")

    monkeypatch.setattr(database, "dump", fail)
    with pytest.raises(RuntimeError, match="dump failed"):
        BackupService(database).create(source, tmp_path / "failed")
    assert not (tmp_path / "failed").exists()
    assert not list(tmp_path.glob(".backup-partial-*"))


def test_restore_validation_failure_does_not_publish(
    bundle: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    backup, database, _ = bundle
    monkeypatch.setattr(database, "inspect_restored", lambda: {})
    with pytest.raises(ValueError, match="differs"):
        BackupService(database).restore(backup, tmp_path / "bad-restore")
    assert database.restored  # isolated DB may remain; never silently drop it
    assert not (tmp_path / "bad-restore").exists()


def test_storage_lock_blocks_competing_operations(tmp_path: Path) -> None:
    with storage_lock(tmp_path), pytest.raises(Unavailable), storage_lock(tmp_path):
        pytest.fail("Competing storage operation acquired the lock")
    with storage_lock(tmp_path):
        pass


@pytest.fixture
def postgres_databases() -> Iterator[tuple[Any, Any, str, str]]:
    url = os.environ.get("IHDA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set IHDA_TEST_POSTGRES_URL for actual pg_dump/pg_restore tests")
    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    from ihda_server.database import make_engine

    source_name, target_name = "backup_" + uuid4().hex, "restore_" + uuid4().hex
    admin = make_engine(url).execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        for name in (source_name, target_name):
            connection.execute(
                text(f"CREATE DATABASE \"{name}\" TEMPLATE template0 ENCODING 'UTF8'")
            )
    source_url = (
        make_url(url).set(database=source_name).render_as_string(hide_password=False)
    )
    target_url = (
        make_url(url).set(database=target_name).render_as_string(hide_password=False)
    )
    source, target = make_engine(source_url), make_engine(target_url)
    try:
        yield source, target, source_url, target_url
    finally:
        source.dispose()
        target.dispose()
        with admin.connect() as connection:
            for name in (source_name, target_name):
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def test_actual_postgres_snapshot_restore_and_sequence(
    postgres_databases: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    from ihda_server.auth import TokenIdentity
    from ihda_server.backup_postgres import PostgresBackup
    from ihda_server.catalog import SqlCatalog
    from ihda_server.database import initialize
    from ihda_server.storage import FileBlobStore

    source, target, source_url, target_url = postgres_databases
    initialize(source)
    identities, catalog = TokenIdentity(source), SqlCatalog(source)
    owner = identities.create_user("backup-user")
    token = identities.issue(owner)
    project = catalog.create_project(owner, "Studio")
    storage = FileBlobStore(tmp_path / "blobs")
    digest, size = storage.put([b"houdini bytes"])
    catalog.register_blob(project["id"], owner, digest, size)
    values = {
        "name": "Water",
        "category": "sop",
        "version": "1",
        "note": "물 노트",
        "tags": ["water"],
        "files": {"asset": asdict(Blob(digest, size, "water.hda"))},
    }
    asset = catalog.execute(project["id"], owner, Command("create", values=values))
    catalog.execute(
        project["id"],
        owner,
        Command(
            "preference",
            asset_id=asset["id"],
            expected_revision=0,
            values={"favorite": True},
        ),
    )
    catalog.execute(
        project["id"],
        owner,
        Command("delete", asset_id=asset["id"], expected_revision=asset["revision"]),
    )
    binary = Path(os.environ["IHDA_PG_BIN"]) if os.environ.get("IHDA_PG_BIN") else None
    original = PostgresBackup(source, source_url, binary)
    dump = original.dump

    def concurrent_write(snapshot: str, path: Path) -> None:
        catalog.create_project(owner, "After snapshot")
        dump(snapshot, path)

    monkeypatch.setattr(original, "dump", concurrent_write)
    backup = tmp_path / "bundle"
    BackupService(original).create(storage.root, backup)
    restored = PostgresBackup(target, target_url, binary)
    destination = tmp_path / "restored-blobs"
    BackupService(restored).restore(backup, destination)
    restored_catalog = SqlCatalog(target)
    assert len(catalog.projects(owner)) == 2
    assert len(restored_catalog.projects(owner)) == 1
    assert TokenIdentity(target).authenticate(token) == owner
    trash = restored_catalog.trash(project["id"], owner)
    assert len(trash) == 1
    restored_asset = restored_catalog.execute(
        project["id"],
        owner,
        Command(
            "restore", asset_id=asset["id"], expected_revision=trash[0]["revision"]
        ),
    )
    assert restored_asset["favorite"] and restored_asset["note"] == "물 노트"
    assert FileBlobStore(destination).path(digest).read_bytes() == b"houdini bytes"
    next_asset = restored_catalog.execute(
        project["id"], owner, Command("create", values={**values, "name": "Fire"})
    )
    assert next_asset["id"] > asset["id"]
    with pytest.raises(ValueError, match="empty"):
        BackupService(restored).restore(backup, tmp_path / "second-restore")


def test_server_backup_cli_has_no_qt_dependency(bundle: Any) -> None:
    import subprocess
    import sys

    backup, _, source = bundle
    script = """
import importlib.abc
import sys
from pathlib import Path
class BlockHost(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'PySide6', 'hou'}:
            raise ImportError('Host dependency forbidden')
sys.meta_path.insert(0, BlockHost())
from ihda_server.storage_lock import storage_lock
from ihda_server.cli import main
with storage_lock(Path(sys.argv[1])):
    pass
sys.argv = ['ihda', 'verify-backup', sys.argv[2]]
main()
"""
    environment = dict(os.environ)
    environment.pop("IHDA_DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, "-c", script, str(source), str(backup)],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["status"] == "backup_verified"


def test_subprocess_credentials_are_not_command_arguments(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from ihda_server.backup_postgres import PostgresBackup
    from ihda_server.database import make_engine

    password = "test-only:password"
    url = "postgresql+psycopg://tester:test-only%3Apassword@localhost/backup_test"
    engine = make_engine(url)
    observed = []

    def process(arguments: list[str], **kwargs: Any) -> None:
        assert password not in repr(arguments)
        passfile = Path(kwargs["env"]["PGPASSFILE"])
        assert passfile.is_file()
        assert "test-only\\:password" in passfile.read_text()
        assert "PGPASSWORD" not in kwargs["env"]
        observed.append(passfile)

    monkeypatch.setattr("ihda_server.backup_postgres.subprocess.run", process)
    try:
        PostgresBackup(engine, url).dump("test-snapshot", tmp_path / "database.dump")
    except FileNotFoundError:
        pass  # fake subprocess intentionally did not create a dump
    finally:
        engine.dispose()
    assert observed and not observed[0].exists()


def test_backup_rejects_symlink_blob(bundle: Any, tmp_path: Path) -> None:
    backup, _, _ = bundle
    manifest = verify_bundle(backup)
    name = next(name for name in manifest["files"] if name.startswith("blobs/"))
    path = backup / name
    external = tmp_path / "external"
    external.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(external)
    except OSError:
        pytest.skip("Symlink creation unavailable on this platform")
    with pytest.raises(ValueError, match="unsafe"):
        verify_bundle(backup)
