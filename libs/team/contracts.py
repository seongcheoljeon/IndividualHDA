"""Versioned user intentions. No client filesystem paths cross this boundary."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol, get_args
from uuid import UUID, uuid4

from libs.file_integrity import FileContent
from libs.search_limits import TEAM_PAGE_DEFAULT

API_VERSION = 2
API_PREFIX = f"/v{API_VERSION}"

# Protocol caps: the client validates them before sending and the server before
# accepting, so they change together and live with the contract.
MAX_COMMAND_BYTES = 256 * 1024
MAX_METADATA_BODY_BYTES = 300 * 1024
MAX_COPY_VERSIONS = 500
DEFAULT_AUDIT_EVENT_LIMIT = 500
DEFAULT_MAX_UPLOAD_BYTES = 1024**3
Role = Literal["viewer", "editor", "owner"]
Operation = Literal[
    "copy_asset",
    "create",
    "version",
    "metadata",
    "rename",
    "delete",
    "delete_history",
    "media",
    "preference",
    "usage",
    "restore",
    "purge",
    "restore_history",
    "purge_history",
    "version_details",
]


class TeamError(Exception):
    status = 400
    code = "invalid_request"


class Unauthorized(TeamError):
    status, code = 401, "unauthorized"


class Forbidden(TeamError):
    status, code = 403, "forbidden"


class NotFound(TeamError):
    status, code = 404, "not_found"


class Conflict(TeamError):
    status, code = 409, "conflict"


class Unavailable(TeamError):
    status, code = 503, "unavailable"


@dataclass(frozen=True)
class Blob:
    digest: str
    size: int
    filename: str

    @property
    def content(self) -> FileContent:
        return FileContent(self.digest, self.size)

    def validate(self) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", self.digest) or self.size < 0:
            raise TeamError("Invalid file reference")
        if (
            not self.filename
            or self.filename in {".", ".."}
            or any(char in self.filename for char in "/\\\x00:")
        ):
            raise TeamError("Filename must be a single safe component")
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        if (
            self.filename.rstrip(" .") != self.filename
            or self.filename.split(".")[0].upper() in reserved
            or any(char in self.filename for char in '<>"|?*')
        ):
            raise TeamError(
                "Filename is not portable across supported operating systems"
            )
        if len(self.filename) > 240:
            raise TeamError("Filename is too long")


@dataclass(frozen=True)
class Command:
    operation: Operation
    request_id: str = field(default_factory=lambda: str(uuid4()))
    asset_id: int | None = None
    expected_revision: int | None = None
    values: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        try:
            UUID(self.request_id)
        except (ValueError, TypeError) as error:
            raise TeamError("request_id must be a UUID") from error
        if self.operation not in get_args(Operation):
            raise TeamError("Unknown operation")
        if self.operation not in {"create", "copy_asset"} and (
            not self.asset_id
            or self.expected_revision is None
            or self.expected_revision
            < (0 if self.operation in {"preference", "usage"} else 1)
        ):
            raise TeamError("Asset identity and expected_revision are required")
        try:
            encoded = json.dumps(asdict(self), allow_nan=False, ensure_ascii=False)
        except (ValueError, TypeError) as error:
            raise TeamError("Command values must be finite JSON data") from error
        if len(encoded.encode()) > MAX_COMMAND_BYTES:
            raise TeamError(f"Command metadata exceeds {MAX_COMMAND_BYTES // 1024} KiB")
        if self.operation == "copy_asset":
            from libs.team.copy_contract import validate_copy

            validate_copy(self.values)
            return
        allowed = {
            "create": {
                "name",
                "category",
                "version",
                "metadata",
                "files",
                "note",
                "tags",
                "description",
                "dependencies",
                "dependency_status",
            },
            "version": {
                "version",
                "metadata",
                "files",
                "description",
                "dependencies",
                "dependency_status",
            },
            "metadata": {"note", "tags"},
            "preference": {"favorite"},
            "usage": set(),
            "restore": set(),
            "purge": set(),
            "restore_history": {"history_id"},
            "purge_history": {"history_id"},
            "version_details": {
                "history_id",
                "description",
                "dependencies",
                "dependency_status",
            },
            "rename": {"name"},
            "delete": set(),
            "delete_history": {"history_id"},
            "media": {"kind", "file"},
        }
        if set(self.values) - allowed[self.operation]:
            raise TeamError("Unexpected command field")
        if self.operation in {"create", "rename"}:
            name = self.values.get("name")
            if not isinstance(name, str) or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_. -]{1,239}", name
            ):
                raise TeamError(
                    "Name must start with a letter and contain 2–240 safe characters"
                )
            Blob("0" * 64, 0, name).validate()
        if self.operation == "create" and not re.fullmatch(
            r"[A-Za-z0-9_-]{1,80}", str(self.values.get("category", ""))
        ):
            raise TeamError("Invalid category")
        if self.operation in {"create", "version"}:
            version = self.values.get("version")
            if not isinstance(version, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]{1,80}", version
            ):
                raise TeamError("Invalid version")
            files = self.values.get("files")
            if (
                not isinstance(files, dict)
                or not files.get("asset")
                or set(files) - {"asset", "thumbnail", "video"}
            ):
                raise TeamError("An asset file is required")
            for file in files.values():
                parse_blob(file)
            if not isinstance(self.values.get("metadata", {}), dict):
                raise TeamError("metadata must be an object")
        if self.operation in {"create", "version", "version_details"}:
            from libs.library_metadata import validate_version_details

            try:
                validate_version_details(self.values)
            except ValueError as error:
                raise TeamError(str(error)) from error
        if self.operation == "preference" and "favorite" not in self.values:
            raise TeamError("favorite is required")
        if "note" in self.values and not isinstance(self.values["note"], str):
            raise TeamError("note must be text")
        if "tags" in self.values and (
            not isinstance(self.values["tags"], list)
            or not all(
                isinstance(tag, str) and len(tag) <= 256 for tag in self.values["tags"]
            )
        ):
            raise TeamError("tags must be a list of strings")
        if "favorite" in self.values and not isinstance(self.values["favorite"], bool):
            raise TeamError("favorite must be boolean")
        if self.operation == "media":
            if self.values.get("kind") not in {"thumbnail", "video"}:
                raise TeamError("Invalid media kind")
            parse_blob(self.values.get("file"))
        if self.operation in {
            "delete_history",
            "restore_history",
            "purge_history",
            "version_details",
        } and (
            not isinstance(self.values.get("history_id"), int)
            or self.values["history_id"] < 1
        ):
            raise TeamError("history_id is required")

    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                asdict(self), sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest()


def parse_blob(value: Any) -> Blob:
    if not isinstance(value, dict) or set(value) != {"digest", "size", "filename"}:
        raise TeamError("Invalid file reference")
    if (
        not isinstance(value["digest"], str)
        or not isinstance(value["size"], int)
        or not isinstance(value["filename"], str)
    ):
        raise TeamError("Invalid file reference types")
    blob = Blob(**value)
    blob.validate()
    return blob


@dataclass(frozen=True)
class Page:
    items: list[dict[str, Any]]
    total: int
    offset: int
    limit: int
    revision: int


class AssetCatalog(Protocol):
    def list_assets(
        self, query: str = "", offset: int = 0, limit: int = TEAM_PAGE_DEFAULT
    ) -> Page: ...
    def get_asset(self, asset_id: int) -> dict[str, Any]: ...
    def histories(self, asset_id: int) -> list[dict[str, Any]]: ...
    def execute(self, command: Command) -> dict[str, Any]: ...


class TrackingCatalog(Protocol):
    """Version tracking is optional on a catalog; ask tracking_supported() first."""

    def tracking_supported(self) -> bool: ...
    def tracking_read(
        self,
        kind: str,
        asset_uuid: str,
        version_uuid: str | None = None,
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> list[dict[str, Any]]: ...
    def tracking_execute(self, body: dict[str, Any]) -> dict[str, Any]: ...


class ManagementCatalog(AssetCatalog, TrackingCatalog, Protocol):
    """What the library management dialog needs beyond the asset catalog."""

    def events(self, asset_uuid: str) -> list[dict[str, Any]]: ...
    def file_status(self, asset_id: int) -> list[dict[str, Any]]: ...
    def trash(self) -> list[dict[str, Any]]: ...
