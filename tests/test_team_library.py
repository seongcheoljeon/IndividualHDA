from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
from support.names import Names
from support.team import TestTransport, create_asset
from support.team import backend as backend
from support.team import server as server

from libs.team.client import BlobCache, HttpCatalog
from libs.team.contracts import (
    Blob,
    Command,
    Conflict,
    Forbidden,
    NotFound,
    TeamError,
    Unauthorized,
)


def test_backend_contract_roundtrip_and_conflicts(backend: Any, tmp_path: Path) -> None:
    command, asset = create_asset(backend, tmp_path)
    assert backend.execute(command) == asset
    assert backend.list_assets().total == 1
    assert backend.list_assets("wat").items[0]["id"] == asset["id"]
    assert backend.list_assets("missing").total == 0
    with pytest.raises(Conflict):
        backend.execute(replace(command, values={**command.values, "name": "Fire"}))
    write = Command(
        "metadata",
        asset_id=asset["id"],
        expected_revision=asset["revision"],
        values={"note": "new note", "tags": ["Water", "water", "한글"]},
    )
    saved = backend.execute(write)
    assert saved["note"] == "new note" and saved["tags"] == ["Water", "한글"]
    assert backend.execute(write) == saved
    with pytest.raises(Conflict):
        backend.execute(replace(write, request_id=Command("create").request_id))
    renamed = backend.execute(
        Command(
            "rename",
            asset_id=asset["id"],
            expected_revision=saved["revision"],
            values={"name": "Fire"},
        )
    )
    assert renamed["name"] == "Fire"
    assert backend.get_asset(asset["id"])["name"] == "Fire"
    blob = Blob(**renamed["files"]["asset"])
    assert backend.download(blob).read_bytes() == b"Houdini asset bytes"
    version = backend.execute(
        Command(
            "version",
            asset_id=asset["id"],
            expected_revision=renamed["revision"],
            values={
                "version": "1.1",
                "files": renamed["files"],
                "metadata": {"node_type_name": "box"},
            },
        )
    )
    histories = backend.histories(asset["id"])
    assert {row["version"] for row in histories} == {"1.0", "1.1"}
    latest = next(row for row in histories if row["version"] == "1.1")
    with pytest.raises(Conflict):
        backend.execute(
            Command(
                "delete_history",
                asset_id=asset["id"],
                expected_revision=version["revision"],
                values={"history_id": latest["id"]},
            )
        )
    removed = backend.execute(
        Command(
            "delete",
            asset_id=asset["id"],
            expected_revision=version["revision"],
            values={},
        )
    )
    assert removed["deleted"] and backend.list_assets().total == 0
    with pytest.raises(NotFound):
        backend.get_asset(asset["id"])


def test_personal_revision_observes_original_ui_writes(tmp_path: Path) -> None:
    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
    from libs.team.personal import PersonalCatalog

    database = tmp_path / "personal.db"
    with SQLite3DatabaseAPI(database):
        pass
    backend = PersonalCatalog(database, tmp_path / "assets", "tester", Names)
    _, asset = create_asset(backend, tmp_path)
    SqliteLibraryRepository(database).set_note(asset["id"], "changed in original UI")
    with pytest.raises(Conflict):
        backend.execute(
            Command(
                "metadata",
                asset_id=asset["id"],
                expected_revision=asset["revision"],
                values={"note": "stale"},
            )
        )
    assert backend.get_asset(asset["id"])["note"] == "changed in original UI"


def test_project_isolation_roles_revocation_and_last_owner(
    server: Any, tmp_path: Path
) -> None:
    client, identity, catalog, owner, token, project, _ = server
    owner_backend = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path, "owner")
    )
    _, asset = create_asset(owner_backend, tmp_path)
    viewer = identity.create_user("viewer")
    viewer_token = identity.issue(viewer)
    transport = TestTransport(client, viewer_token)
    with pytest.raises(Forbidden):
        transport.request("GET", f"/v2/projects/{project}/assets")
    catalog.set_member(project, owner, viewer, "viewer")
    assert transport.request("GET", f"/v2/projects/{project}/assets")["total"] == 1
    viewer_backend = HttpCatalog(transport, project, BlobCache(tmp_path, "viewer"))
    with pytest.raises(Forbidden):
        viewer_backend.execute(
            Command("delete", asset_id=asset["id"], expected_revision=asset["revision"])
        )
    with pytest.raises(Forbidden):
        viewer_backend.upload(tmp_path / "water.ihda")
    with pytest.raises(Forbidden):
        transport.request(
            "PUT", f"/v2/projects/{project}/members/{viewer}", {"role": "owner"}
        )
    other = catalog.create_project(viewer, "Other")
    with pytest.raises(NotFound):
        transport.request("GET", f"/v2/projects/{other['id']}/assets/{asset['id']}")
    response = client.get(
        f"/v2/projects/{other['id']}/blobs/{asset['files']['asset']['digest']}",
        headers=transport.headers,
    )
    assert response.status_code == 404
    with pytest.raises(Conflict):
        catalog.set_member(project, owner, owner, None)
    identity.revoke_user(viewer)
    with pytest.raises(Unauthorized):
        transport.request("GET", "/v2/me")
    assert client.get("/v2/me").status_code == 401


def test_upload_validation_and_unowned_blob(server: Any, tmp_path: Path) -> None:
    client, _, _, _, token, project, storage = server
    transport = TestTransport(client, token)
    path = tmp_path / "too-large.hda"
    path.write_bytes(b"x" * 4097)
    with pytest.raises(TeamError):
        transport.upload(f"/v2/projects/{project}/blobs", path)
    assert not list(storage.root.glob("upload-*"))
    command = Command(
        "create",
        values={
            "name": "Water",
            "category": "sop",
            "version": "1.0",
            "files": {
                "asset": {"digest": "a" * 64, "size": 1, "filename": "asset.hda"}
            },
        },
    )
    with pytest.raises(TeamError, match="uploaded"):
        transport.request("POST", f"/v2/projects/{project}/commands", asdict(command))
    malformed = asdict(command)
    malformed["values"]["files"]["asset"]["filename"] = "../escape"
    with pytest.raises(TeamError):
        transport.request("POST", f"/v2/projects/{project}/commands", malformed)
    assert (
        client.post(
            f"/v2/projects/{project}/commands",
            headers=transport.headers,
            content=b"x" * (301 * 1024),
        ).status_code
        == 413
    )


def test_cache_verifies_download_and_repairs_corruption(tmp_path: Path) -> None:
    cache = BlobCache(tmp_path, "one project")
    data = b"verified bytes"
    blob = Blob(hashlib.sha256(data).hexdigest(), len(data), "water.hda")
    with pytest.raises(TeamError):
        cache.fetch(blob, lambda: iter([b"corrupt"]))
    assert not list(cache.root.rglob(".download-*"))
    path = cache.fetch(blob, lambda: iter([data]))
    path.write_bytes(b"x" * len(data))
    assert cache.fetch(blob, lambda: iter([data])).read_bytes() == data
    with pytest.raises(TeamError):
        cache.fetch(Blob(blob.digest, blob.size, "../escape"), lambda: iter([data]))


def test_server_idempotency_and_revisions_are_atomic_under_concurrency(
    server: Any, tmp_path: Path
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    _, _, catalog, owner, _, project, storage = server
    digest, size = storage.put([b"asset"])
    catalog.register_blob(project, owner, digest, size)
    command = Command(
        "create",
        values={
            "name": "Water",
            "category": "sop",
            "version": "1",
            "files": {
                "asset": {"digest": digest, "size": size, "filename": "water.hda"}
            },
        },
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(
            pool.map(lambda _: catalog.execute(project, owner, command), range(4))
        )
    assert all(value == values[0] for value in values)
    assert catalog.list_assets(project, owner).total == 1
    asset = values[0]

    def write(note: str) -> str:
        try:
            catalog.execute(
                project,
                owner,
                Command(
                    "metadata",
                    asset_id=asset["id"],
                    expected_revision=asset["revision"],
                    values={"note": note},
                ),
            )
            return "saved"
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, ["first", "second"])) == ["conflict", "saved"]


@pytest.mark.parametrize(
    "filename", ["CON.hda", "asset. ", "what?.hda", "../x", "a:b", "NUL"]
)
def test_blob_names_are_portable(filename: str) -> None:
    with pytest.raises(TeamError):
        Blob("a" * 64, 1, filename).validate()


def test_command_rejects_non_json_metadata() -> None:
    with pytest.raises(TeamError, match="finite JSON"):
        Command(
            "metadata", asset_id=1, expected_revision=1, values={"note": float("nan")}
        ).validate()


def test_backend_media_and_old_history_deletion(backend: Any, tmp_path: Path) -> None:
    _, asset = create_asset(backend, tmp_path)
    old = backend.histories(asset["id"])[0]
    path = tmp_path / "preview.mp4"
    path.write_bytes(b"preview bytes")
    media = asdict(backend.upload(path))
    asset = backend.execute(
        Command(
            "media",
            asset_id=asset["id"],
            expected_revision=asset["revision"],
            values={"kind": "video", "file": media},
        )
    )
    assert (
        backend.download(Blob(**asset["files"]["video"])).read_bytes()
        == b"preview bytes"
    )
    version = Command(
        "version",
        asset_id=asset["id"],
        expected_revision=asset["revision"],
        values={"version": "2.0", "files": asset["files"]},
    )
    asset = backend.execute(version)
    with pytest.raises(Conflict):
        backend.execute(
            replace(
                version,
                request_id=Command("create").request_id,
                expected_revision=asset["revision"],
            )
        )
    asset = backend.execute(
        Command(
            "delete_history",
            asset_id=asset["id"],
            expected_revision=asset["revision"],
            values={"history_id": old["id"]},
        )
    )
    assert [row["version"] for row in backend.histories(asset["id"])] == ["2.0"]
    asset = backend.execute(
        Command(
            "metadata",
            asset_id=asset["id"],
            expected_revision=asset["revision"],
            values={"tags": []},
        )
    )
    asset = backend.execute(
        Command(
            "preference",
            asset_id=asset["id"],
            expected_revision=asset["preference_revision"],
            values={"favorite": True},
        )
    )
    assert asset["tags"] == [] and asset["favorite"] is True


def test_real_http_transport_upload_download_and_retry(
    server: Any, tmp_path: Path
) -> None:
    import json
    import subprocess
    import sys
    import time

    from libs.team.client import HttpTransport

    _, _, catalog, _, token, project, storage = server
    ready_file = tmp_path / "http-ready.json"
    engine = catalog._engine
    configuration = {
        "url": engine.url.render_as_string(hide_password=False),
        "schema": engine.get_execution_options()
        .get("schema_translate_map", {})
        .get(None),
        "storage": str(storage.root),
        "ready": str(ready_file),
    }
    # Production runs outside Houdini. Keep server allocation/GC out of Qt's
    # process too: WebEngine objects must be destroyed on the GUI thread.
    environment = {**os.environ, "IHDA_HTTP_TEST_CONFIG": json.dumps(configuration)}
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("http_server_fixture.py"))],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 15
        while not ready_file.exists() and time.monotonic() < deadline:
            assert process.poll() is None, "HTTP test server exited during startup"
            time.sleep(0.01)
        assert ready_file.exists()
        port = json.loads(ready_file.read_text())["port"]
        transport = HttpTransport(f"http://127.0.0.1:{port}", lambda: token, timeout=5)
        # The socket is listening before readiness is published; requests can
        # queue while Uvicorn finishes initializing its loop.
        backend = HttpCatalog(
            transport, project, BlobCache(tmp_path / "http-cache", project)
        )
        command, asset = create_asset(backend, tmp_path)
        revision = backend.list_assets().revision
        assert backend.execute(command) == asset
        assert backend.list_assets().revision == revision
        assert (
            backend.download(Blob(**asset["files"]["asset"])).read_bytes()
            == b"Houdini asset bytes"
        )
        with pytest.raises(Unauthorized):
            HttpTransport(
                f"http://127.0.0.1:{port}", lambda: "invalid", timeout=5
            ).request("GET", "/v2/me")
    finally:
        process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_events_page_with_offset_and_limit(backend: Any, tmp_path: Path) -> None:
    from libs.team.contracts import TeamError

    command, asset = create_asset(backend, tmp_path)
    backend.execute(command)
    for note in ("first", "second"):
        current = backend.get_asset(asset["id"])
        backend.execute(
            Command(
                "metadata",
                asset_id=asset["id"],
                expected_revision=current["revision"],
                values={"note": note, "tags": []},
            )
        )
    everything = backend.events(asset["asset_uuid"])
    assert len(everything) >= 3
    assert backend.events(asset["asset_uuid"], offset=1, limit=1) == [everything[1]]
    assert backend.events(asset["asset_uuid"], offset=len(everything), limit=5) == []
    with pytest.raises(TeamError):
        backend.events(asset["asset_uuid"], limit=0)
