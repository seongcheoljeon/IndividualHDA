"""Application service depends on catalog and file ports, not FastAPI or SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from ihda_server.storage_lock import storage_lock
from libs.team.contracts import Command, NotFound, Page, Role


class CatalogStore(Protocol):
    def copy_check(
        self,
        project_id: str,
        user_id: str,
        name: str,
        category: str,
        library_uuid: str,
        asset_uuid: str,
    ) -> dict[str, Any]: ...

    def file_status(
        self, project_id: str, user_id: str, asset_id: int
    ) -> list[dict[str, Any]]: ...
    def trash(self, project_id: str, user_id: str) -> list[dict[str, Any]]: ...
    def events(
        self, project_id: str, user_id: str, asset_uuid: str
    ) -> list[dict[str, Any]]: ...
    def require_access(
        self, project_id: str, user_id: str, write: bool = False
    ) -> None: ...
    def projects(self, user_id: str) -> list[dict[str, Any]]: ...
    def create_project(self, user_id: str, name: str) -> dict[str, Any]: ...
    def members(self, project_id: str, user_id: str) -> list[dict[str, Any]]: ...
    def set_member(
        self, project_id: str, actor: str, user_id: str, role: Role | None
    ) -> None: ...
    def register_blob(
        self, project_id: str, user_id: str, digest: str, size: int
    ) -> None: ...
    def blob_size(self, project_id: str, user_id: str, digest: str) -> int: ...
    def list_assets(
        self,
        project_id: str,
        user_id: str,
        query: str = "",
        offset: int = 0,
        limit: int = 100,
    ) -> Page: ...
    def get_asset(
        self, project_id: str, user_id: str, asset_id: int
    ) -> dict[str, Any]: ...
    def histories(
        self, project_id: str, user_id: str, asset_id: int
    ) -> list[dict[str, Any]]: ...
    def execute(
        self, project_id: str, user_id: str, command: Command
    ) -> dict[str, Any]: ...


class BlobStore(Protocol):
    def put(self, chunks: Iterable[bytes]) -> tuple[str, int]: ...
    def path(self, digest: str) -> Path: ...


class Identity(Protocol):
    def authenticate(self, credential: str) -> str: ...


class LibraryService:
    def __init__(
        self, catalog: CatalogStore, storage: BlobStore, identity: Identity
    ) -> None:
        self.catalog, self.storage, self.identity = catalog, storage, identity

    def upload(
        self, project_id: str, user_id: str, chunks: Iterable[bytes]
    ) -> dict[str, Any]:
        self.catalog.require_access(project_id, user_id, write=True)
        with storage_lock(self.storage.path("0" * 64).parent.parent):
            digest, size = self.storage.put(chunks)
            self.catalog.register_blob(project_id, user_id, digest, size)
        return {"digest": digest, "size": size}

    def download(self, project_id: str, user_id: str, digest: str) -> Path:
        self.catalog.blob_size(project_id, user_id, digest)
        path = self.storage.path(digest)
        if not path.is_file():
            raise NotFound("Stored file is missing; contact the library administrator")
        return path
