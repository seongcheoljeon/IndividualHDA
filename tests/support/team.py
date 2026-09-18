"""Shared fixtures without importing test modules."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from libs.team.client import BlobCache, HttpCatalog
from libs.team.contracts import (
    Command,
    Conflict,
    Forbidden,
    NotFound,
    TeamError,
    Unauthorized,
)


class TestTransport:
    __test__ = False

    def __init__(self, client: Any, token: str) -> None:
        self.client = client
        self.headers = {"Authorization": "Bearer " + token}

    def _decode(self, response: Any) -> Any:
        if response.status_code >= 400:
            error_type = {
                401: Unauthorized,
                403: Forbidden,
                404: NotFound,
                409: Conflict,
            }.get(response.status_code, TeamError)
            raise error_type(response.json().get("message", str(response.status_code)))
        return response.json()

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        return self._decode(
            self.client.request(method, path, json=payload, headers=self.headers)
        )

    def upload(self, path: str, file: Path) -> dict[str, Any]:
        return self._decode(
            self.client.post(path, content=file.read_bytes(), headers=self.headers)
        )

    def download(self, path: str) -> Iterator[bytes]:
        response = self.client.get(path, headers=self.headers)
        if response.status_code >= 400:
            self._decode(response)
        yield response.content


@pytest.fixture
def server(tmp_path: Path) -> Iterator[Any]:
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")
    from fastapi.testclient import TestClient

    from ihda_server.app import make_app
    from ihda_server.auth import TokenIdentity
    from ihda_server.catalog import SqlCatalog
    from ihda_server.database import initialize, make_engine
    from ihda_server.service import LibraryService
    from ihda_server.storage import FileBlobStore

    url = os.environ.get(
        "IHDA_TEST_POSTGRES_URL", "sqlite:///" + str(tmp_path / "server.db")
    )
    engine = make_engine(url)
    schema_name = None
    if engine.dialect.name == "postgresql":
        from uuid import uuid4

        from sqlalchemy import text

        schema_name = "test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        engine = engine.execution_options(schema_translate_map={None: schema_name})
    initialize(engine)
    identities, catalog = TokenIdentity(engine), SqlCatalog(engine)
    owner = identities.create_user("owner")
    token = identities.issue(owner)
    project = catalog.create_project(owner, "Studio")
    storage = FileBlobStore(tmp_path / "server-blobs", max_size=4096)
    with TestClient(
        make_app(LibraryService(catalog, storage, identities), max_upload=4096)
    ) as client:
        yield client, identities, catalog, owner, token, project["id"], storage
    if schema_name is not None:
        from sqlalchemy import text

        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
    engine.dispose()


@pytest.fixture(params=["server"])
def backend(request: Any, tmp_path: Path) -> Any:
    client, _, _, _, token, project, _ = request.getfixturevalue("server")
    return HttpCatalog(
        TestTransport(client, token), project, BlobCache(tmp_path / "cache", project)
    )


def create_asset(
    backend: Any, tmp_path: Path, name: str = "Water"
) -> tuple[Command, dict[str, Any]]:
    path = tmp_path / "water.ihda"
    path.write_bytes(b"Houdini asset bytes")
    command = Command(
        "create",
        values={
            "name": name,
            "category": "sop",
            "version": "1.0",
            "files": {"asset": asdict(backend.upload(path))},
            "metadata": {"node_type_name": "box"},
        },
    )
    return command, backend.execute(command)
