"""Bounded HTTP transport, explicit retry commands and verified local file cache."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from typing import Any, Protocol

from libs.file_integrity import FileContent, measure_file
from libs.search_limits import TEAM_PAGE_DEFAULT
from libs.team.contracts import (
    API_PREFIX,
    DEFAULT_AUDIT_EVENT_LIMIT,
    Blob,
    Command,
    Conflict,
    Forbidden,
    NotFound,
    Page,
    TeamError,
    Unauthorized,
    Unavailable,
)
from libs.team.limits import DEFAULT_HTTP_TIMEOUT_SECONDS, HttpLimits


class Transport(Protocol):
    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any: ...
    def upload(self, path: str, file: Path) -> dict[str, Any]: ...
    def download(self, path: str) -> Iterator[bytes]: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, request: Any, file: Any, code: int, message: str, headers: Any, url: str
    ) -> None:
        return None


class HttpTransport:
    def __init__(
        self,
        url: str,
        credential: Callable[[], str],
        *,
        timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
        limits: HttpLimits | None = None,
    ) -> None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("HTTP timeout must be finite and positive")
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "A server URL without credentials, query or fragment is required"
            )
        if parsed.scheme == "http" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                "Team servers require HTTPS; HTTP is allowed only for loopback development"
            )
        self.url = url.rstrip("/")
        self._credential = credential
        self._timeout = timeout
        self._limits = limits if limits is not None else HttpLimits()
        self._opener = urllib.request.build_opener(NoRedirect())

    def _open(
        self, method: str, path: str, body: Any = None, length: int | None = None
    ) -> Any:
        credential = self._credential().strip()
        if not credential:
            raise Unauthorized("Set the server credential environment variable")
        headers = {
            "Authorization": f"Bearer {credential}",
            "Content-Type": "application/json"
            if isinstance(body, bytes)
            else "application/octet-stream",
        }
        if length is not None:
            headers["Content-Length"] = str(length)
        request = urllib.request.Request(
            self.url + path, data=body, headers=headers, method=method
        )
        try:
            return self._opener.open(request, timeout=self._timeout)
        except urllib.error.HTTPError as error:
            try:
                message = json.loads(error.read(self._limits.diagnostic_bytes)).get(
                    "message", f"HTTP {error.code}"
                )
            except (ValueError, AttributeError):
                message = f"HTTP {error.code}"
            exception = {
                401: Unauthorized,
                403: Forbidden,
                404: NotFound,
                409: Conflict,
            }.get(error.code, TeamError)
            if error.code >= 500:
                raise Unavailable(
                    "Server failed to complete the response; retry the same pending request"
                ) from None
            raise exception(str(message)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise Unavailable(
                "Server request failed; retry the same pending request after checking the connection"
            ) from error

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        encoded = (
            json.dumps(payload, allow_nan=False, ensure_ascii=False).encode()
            if payload is not None
            else None
        )
        with self._open(method, path, encoded) as response:
            data = response.read(self._limits.response_bytes + 1)
        if len(data) > self._limits.response_bytes:
            raise TeamError("Server response is too large")
        return json.loads(data)

    def upload(self, path: str, file: Path) -> dict[str, Any]:
        with (
            file.open("rb") as source,
            self._open("POST", path, source, file.stat().st_size) as response,
        ):
            return dict(json.loads(response.read(self._limits.diagnostic_bytes)))

    def download(self, path: str) -> Iterator[bytes]:
        with self._open("GET", path) as response:
            while chunk := response.read(self._limits.chunk_bytes):
                yield chunk


class BlobCache:
    def __init__(self, root: Path, namespace: str) -> None:
        self.root = root / hashlib.sha256(namespace.encode()).hexdigest()
        self.root.mkdir(parents=True, exist_ok=True)

    def fetch(self, blob: Blob, chunks: Callable[[], Iterator[bytes]]) -> Path:
        blob.validate()
        target = self.root / blob.digest / blob.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.resolve().is_relative_to(self.root.resolve()):
            raise TeamError("Cache path escapes its root")
        if target.is_file() and target.stat().st_size == blob.size:
            if measure_file(target) == blob.content:
                return target
        descriptor, name = tempfile.mkstemp(dir=target.parent, prefix=".download-")
        temporary = Path(name)
        digest, size = hashlib.sha256(), 0
        try:
            with os.fdopen(descriptor, "wb") as output:
                for chunk in chunks():
                    size += len(chunk)
                    if size > blob.size:
                        raise TeamError("Downloaded file is larger than expected")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if FileContent(digest.hexdigest(), size) != blob.content:
                raise TeamError("Downloaded file failed SHA-256 verification")
            os.replace(temporary, target)
            return target
        finally:
            temporary.unlink(missing_ok=True)


class HttpCatalog:
    def __init__(self, transport: Transport, project_id: str, cache: BlobCache) -> None:
        from uuid import UUID

        UUID(project_id)
        self.transport = transport
        self.project_id = project_id
        self.cache = cache
        self._base = f"{API_PREFIX}/projects/{project_id}"

    @property
    def namespace(self) -> str:
        return "team:" + str(self.cache.root.resolve())

    def list_assets(
        self, query: str = "", offset: int = 0, limit: int = TEAM_PAGE_DEFAULT
    ) -> Page:
        values = self.transport.request(
            "GET",
            self._base
            + "/assets?"
            + urllib.parse.urlencode(
                {"query": query, "offset": offset, "limit": limit}
            ),
        )
        return Page(**values)

    def get_asset(self, asset_id: int) -> dict[str, Any]:
        return dict(self.transport.request("GET", f"{self._base}/assets/{asset_id}"))

    def histories(self, asset_id: int) -> list[dict[str, Any]]:
        return list(
            self.transport.request("GET", f"{self._base}/assets/{asset_id}/history")
        )

    def execute(self, command: Command) -> dict[str, Any]:
        command.validate()
        return dict(
            self.transport.request("POST", self._base + "/commands", asdict(command))
        )

    def tracking_supported(self) -> bool:
        return "version_tracking" in self.transport.request("GET", "/health").get(
            "capabilities", []
        )

    def tracking_read(
        self,
        kind: str,
        asset_uuid: str,
        version_uuid: str | None = None,
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> list[dict[str, Any]]:
        query = {"asset_uuid": asset_uuid, "offset": offset, "limit": limit}
        if version_uuid is not None:
            query["version_uuid"] = version_uuid
        return list(
            self.transport.request(
                "GET",
                self._base + "/tracking/" + kind + "?" + urllib.parse.urlencode(query),
            )
        )

    def tracking_execute(self, body: dict[str, Any]) -> dict[str, Any]:
        return dict(self.transport.request("POST", self._base + "/tracking", body))

    def file_status(self, asset_id: int) -> list[dict[str, Any]]:
        return list(
            self.transport.request("GET", f"{self._base}/assets/{asset_id}/files")
        )

    def trash(self) -> list[dict[str, Any]]:
        return list(self.transport.request("GET", self._base + "/trash"))

    def events(
        self, asset_uuid: str, offset: int = 0, limit: int = DEFAULT_AUDIT_EVENT_LIMIT
    ) -> list[dict[str, Any]]:
        return list(
            self.transport.request(
                "GET",
                self._base
                + "/events/"
                + urllib.parse.quote(asset_uuid, safe="")
                + "?"
                + urllib.parse.urlencode({"offset": offset, "limit": limit}),
            )
        )

    def upload(self, path: Path) -> Blob:
        result = self.transport.upload(self._base + "/blobs", path)
        blob = Blob(result["digest"], result["size"], path.name)
        blob.validate()
        if measure_file(path) != blob.content:
            raise TeamError("Uploaded file changed during transfer")
        return blob

    def download(self, blob: Blob) -> Path:
        return self.cache.fetch(
            blob, lambda: self.transport.download(self._base + "/blobs/" + blob.digest)
        )
