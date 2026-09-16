"""Versioned HTTP routes. Inject services in tests; production uses create_app()."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from ihda_server.auth import TokenIdentity
from ihda_server.catalog import SqlCatalog
from ihda_server.database import make_engine, verify_schema
from ihda_server.service import LibraryService
from ihda_server.storage import FileBlobStore
from libs.file_integrity import FILE_READ_CHUNK_BYTES
from libs.team.contracts import (
    API_PREFIX,
    API_VERSION,
    Command,
    Operation,
    Role,
    TeamError,
    Unauthorized,
)
from libs.team.limits import DEFAULT_MAX_UPLOAD_BYTES, MAX_METADATA_BODY_BYTES


class CommandBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Operation
    request_id: str
    asset_id: int | None = None
    expected_revision: int | None = None
    values: dict[str, Any] = Field(default_factory=dict)


class ProjectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)


class MemberBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["viewer", "editor", "owner"] | None


def make_app(
    service: LibraryService, *, max_upload: int = DEFAULT_MAX_UPLOAD_BYTES
) -> FastAPI:
    application = FastAPI(title="Individual HDA Team Library", version="2.0.0")

    @application.exception_handler(TeamError)
    async def team_error(request: Request, error: TeamError) -> JSONResponse:
        return JSONResponse(
            {"code": error.code, "message": str(error)},
            status_code=error.status,
            headers={"WWW-Authenticate": "Bearer"} if error.status == 401 else None,
        )

    @application.middleware("http")
    async def limit_json(request: Request, call_next: Any) -> Any:
        if request.url.path.startswith("/v1/"):
            return JSONResponse(
                {
                    "code": "upgrade_required",
                    "message": "Update the app and server together (API v2 required)",
                },
                status_code=426,
            )
        # Bound metadata bodies too, including chunked bodies without Content-Length.
        if request.method in {"POST", "PUT", "PATCH"} and not request.url.path.endswith(
            "/blobs"
        ):
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_METADATA_BODY_BYTES:
                    return JSONResponse(
                        {"code": "too_large", "message": "Metadata body is too large"},
                        status_code=413,
                    )
            request._body = bytes(body)
        return await call_next(request)

    def actor(authorization: Annotated[str | None, Header()] = None) -> str:
        if authorization is None or not authorization.startswith("Bearer "):
            raise Unauthorized("Bearer credential required")
        return service.identity.authenticate(authorization[7:])

    @application.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "api_version": API_VERSION,
            "capabilities": ["asset_copy"],
        }

    @application.get(API_PREFIX + "/projects/{project_id}/copy-check")
    def copy_check(
        project_id: str,
        name: str,
        category: str,
        library_uuid: str,
        asset_uuid: str,
        user: str = Depends(actor),
    ) -> dict[str, Any]:
        return service.catalog.copy_check(
            project_id, user, name, category, library_uuid, asset_uuid
        )

    @application.get(API_PREFIX + "/projects/{project_id}/blobs/{digest}/info")
    def blob_info(
        project_id: str, digest: str, user: str = Depends(actor)
    ) -> dict[str, Any]:
        path = service.download(project_id, user, digest)
        return {"digest": digest, "size": path.stat().st_size}

    @application.get(API_PREFIX + "/me")
    def me(user: str = Depends(actor)) -> dict[str, Any]:
        return {"user_id": user, "projects": service.catalog.projects(user)}

    @application.get(API_PREFIX + "/projects/{project_id}/assets/{asset_id}/files")
    def files(
        project_id: str, asset_id: int, user: str = Depends(actor)
    ) -> list[dict[str, Any]]:
        return service.catalog.file_status(project_id, user, asset_id)

    @application.get(API_PREFIX + "/projects/{project_id}/trash")
    def trash(project_id: str, user: str = Depends(actor)) -> list[dict[str, Any]]:
        return service.catalog.trash(project_id, user)

    @application.get(API_PREFIX + "/projects/{project_id}/events/{asset_uuid}")
    def events(
        project_id: str, asset_uuid: str, user: str = Depends(actor)
    ) -> list[dict[str, Any]]:
        return service.catalog.events(project_id, user, asset_uuid)

    @application.post(API_PREFIX + "/projects", status_code=201)
    def create_project(body: ProjectBody, user: str = Depends(actor)) -> dict[str, Any]:
        return service.catalog.create_project(user, body.name)

    @application.get(API_PREFIX + "/projects/{project_id}/members")
    def members(project_id: str, user: str = Depends(actor)) -> list[dict[str, Any]]:
        return service.catalog.members(project_id, user)

    @application.put(API_PREFIX + "/projects/{project_id}/members/{user_id}")
    def set_member(
        project_id: str, user_id: str, body: MemberBody, user: str = Depends(actor)
    ) -> dict[str, bool]:
        role: Role | None = body.role
        service.catalog.set_member(project_id, user, user_id, role)
        return {"updated": True}

    @application.get(API_PREFIX + "/projects/{project_id}/assets")
    def assets(
        project_id: str,
        user: str = Depends(actor),
        query: str = "",
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        return asdict(
            service.catalog.list_assets(project_id, user, query, offset, limit)
        )

    @application.get(API_PREFIX + "/projects/{project_id}/assets/{asset_id}")
    def asset(
        project_id: str, asset_id: int, user: str = Depends(actor)
    ) -> dict[str, Any]:
        return service.catalog.get_asset(project_id, user, asset_id)

    @application.get(API_PREFIX + "/projects/{project_id}/assets/{asset_id}/history")
    def history(
        project_id: str, asset_id: int, user: str = Depends(actor)
    ) -> list[dict[str, Any]]:
        return service.catalog.histories(project_id, user, asset_id)

    @application.post(API_PREFIX + "/projects/{project_id}/commands")
    def execute(
        project_id: str, body: CommandBody, user: str = Depends(actor)
    ) -> dict[str, Any]:
        return service.catalog.execute(project_id, user, Command(**body.model_dump()))

    @application.post(API_PREFIX + "/projects/{project_id}/blobs", status_code=201)
    async def upload(
        project_id: str, request: Request, user: str = Depends(actor)
    ) -> dict[str, Any]:
        await run_in_threadpool(service.catalog.require_access, project_id, user, True)
        # Spool first so untrusted network streams do not occupy a database transaction.
        with tempfile.TemporaryFile() as file:
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > max_upload:
                    raise TeamError("File is too large")
                await run_in_threadpool(file.write, chunk)
            file.seek(0)
            return await run_in_threadpool(
                service.upload,
                project_id,
                user,
                iter(lambda: file.read(FILE_READ_CHUNK_BYTES), b""),
            )

    @application.get(API_PREFIX + "/projects/{project_id}/blobs/{digest}")
    def download(
        project_id: str, digest: str, user: str = Depends(actor)
    ) -> FileResponse:
        path = service.download(project_id, user, digest)
        return FileResponse(
            path,
            media_type="application/octet-stream",
            headers={"ETag": f'"{digest}"', "Cache-Control": "private, no-store"},
        )

    return application


def create_app() -> FastAPI:
    url = os.environ["IHDA_DATABASE_URL"]
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Production server requires a PostgreSQL psycopg URL")
    engine = make_engine(url)
    storage = FileBlobStore(
        Path(os.environ.get("IHDA_BLOB_ROOT", "/data/blobs")),
        int(os.environ.get("IHDA_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))),
    )
    application = make_app(
        LibraryService(SqlCatalog(engine), storage, TokenIdentity(engine)),
        max_upload=storage.max_size,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(verify_schema, engine)
        try:
            yield
        finally:
            engine.dispose()

    application.router.lifespan_context = lifespan
    return application
