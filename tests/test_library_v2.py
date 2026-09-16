from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from test_team_library import backend as backend  # noqa: F401
from test_team_library import create_asset
from test_team_library import server as server  # noqa: F401

from libs.team.contracts import Command, Conflict, Forbidden, NotFound


def test_preferences_usage_and_identity_are_independent(
    backend: Any, tmp_path: Path
) -> None:
    _, asset = create_asset(backend, tmp_path)
    UUID(asset["asset_uuid"])
    UUID(asset["version_uuid"])
    favorite = Command(
        "preference",
        asset_id=asset["id"],
        expected_revision=asset["preference_revision"],
        values={"favorite": True},
    )
    updated = backend.execute(favorite)
    assert updated["favorite"] and updated["revision"] == asset["revision"]
    assert backend.execute(favorite) == updated
    with pytest.raises(Conflict):
        backend.execute(
            Command(
                "preference",
                asset_id=asset["id"],
                expected_revision=asset["preference_revision"],
                values={"favorite": False},
            )
        )
    usage = Command("usage", asset_id=asset["id"], expected_revision=0)
    used = backend.execute(usage)
    assert backend.execute(usage) == used
    assert used["use_count"] == 1 and used["last_used_at"]
    assert used["revision"] == asset["revision"]


def test_trash_restore_and_permanent_delete_keep_audit(
    backend: Any, tmp_path: Path
) -> None:
    _, asset = create_asset(backend, tmp_path)
    blob = asset["files"]["asset"]
    deleted = backend.execute(
        Command("delete", asset_id=asset["id"], expected_revision=asset["revision"])
    )
    assert deleted["deleted"]
    assert backend.list_assets().total == 0
    with pytest.raises(NotFound):
        backend.get_asset(asset["id"])
    item = backend.trash()[0]
    restored = backend.execute(
        Command("restore", asset_id=asset["id"], expected_revision=item["revision"])
    )
    assert restored["asset_uuid"] == asset["asset_uuid"]
    assert restored["files"]["asset"] == blob
    backend.execute(
        Command("delete", asset_id=asset["id"], expected_revision=restored["revision"])
    )
    item = backend.trash()[0]
    backend.execute(
        Command("purge", asset_id=asset["id"], expected_revision=item["revision"])
    )
    assert backend.trash() == []
    assert any(
        row["operation"] == "purge" for row in backend.events(asset["asset_uuid"])
    )


def test_version_trash_survives_asset_restore(backend: Any, tmp_path: Path) -> None:
    _, asset = create_asset(backend, tmp_path)
    old = backend.histories(asset["id"])[0]
    asset = backend.execute(
        Command(
            "version",
            asset_id=asset["id"],
            expected_revision=asset["revision"],
            values={
                "version": "2",
                "files": asset["files"],
                "description": "New version",
            },
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
    backend.execute(
        Command("delete", asset_id=asset["id"], expected_revision=asset["revision"])
    )
    trash = next(row for row in backend.trash() if row["history_id"] is None)
    asset = backend.execute(
        Command("restore", asset_id=asset["id"], expected_revision=trash["revision"])
    )
    assert len(backend.histories(asset["id"])) == 1
    trash = backend.trash()[0]
    backend.execute(
        Command(
            "restore_history",
            asset_id=asset["id"],
            expected_revision=trash["revision"],
            values={"history_id": old["id"]},
        )
    )
    assert len(backend.histories(asset["id"])) == 2


def test_team_viewer_has_private_favorites_and_no_purge(
    server: Any, tmp_path: Path
) -> None:
    client, identities, catalog, owner, token, project, storage = server
    from test_team_library import TestTransport

    from libs.team.client import BlobCache, HttpCatalog

    remote = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    _, asset = create_asset(remote, tmp_path)
    viewer = identities.create_user("viewer2")
    catalog.set_member(project, owner, viewer, "viewer")
    result = catalog.execute(
        project,
        viewer,
        Command(
            "preference",
            asset_id=asset["id"],
            expected_revision=0,
            values={"favorite": True},
        ),
    )
    assert result["favorite"]
    assert not catalog.get_asset(project, owner, asset["id"])["favorite"]
    with pytest.raises(Forbidden):
        catalog.execute(
            project,
            viewer,
            Command(
                "delete", asset_id=asset["id"], expected_revision=asset["revision"]
            ),
        )
    assert client.get("/v1/me").status_code == 426


def test_media_preserves_version_snapshot(server: Any, tmp_path: Path) -> None:
    client, _, _, _, token, project, _ = server
    from test_team_library import TestTransport

    from libs.team.client import BlobCache, HttpCatalog

    remote = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    _, asset = create_asset(remote, tmp_path)
    original = remote.histories(asset["id"])[0]["document"]
    renamed = remote.execute(
        Command(
            "rename",
            asset_id=asset["id"],
            expected_revision=asset["revision"],
            values={"name": "Renamed"},
        )
    )
    path = tmp_path / "thumb.png"
    path.write_bytes(b"preview")
    remote.execute(
        Command(
            "media",
            asset_id=asset["id"],
            expected_revision=renamed["revision"],
            values={"kind": "thumbnail", "file": asdict(remote.upload(path))},
        )
    )
    snapshot = remote.histories(asset["id"])[0]["document"]
    assert snapshot["name"] == original["name"]
    assert snapshot["metadata"] == original["metadata"]
    assert snapshot["version_uuid"] == original["version_uuid"]


def test_cleanup_preserves_shared_and_trashed_versions(
    server: Any, tmp_path: Path
) -> None:
    client, _, catalog, _, token, project, storage = server
    from test_team_library import TestTransport

    from ihda_server.file_maintenance import cleanup
    from libs.team.client import BlobCache, HttpCatalog

    remote = HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )
    _, first = create_asset(remote, tmp_path)
    _, second = create_asset(remote, tmp_path, "Other")
    for asset in (first, second):
        remote.execute(
            Command("delete", asset_id=asset["id"], expected_revision=asset["revision"])
        )
    assert cleanup(catalog._engine, storage) == []
    for item in remote.trash():
        remote.execute(
            Command(
                "purge", asset_id=item["asset_id"], expected_revision=item["revision"]
            )
        )
    assert len(cleanup(catalog._engine, storage)) == 1
    cleanup(catalog._engine, storage, apply=True)
    assert not storage.path(first["files"]["asset"]["digest"]).exists()
