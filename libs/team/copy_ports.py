"""Ports required by the copy workflow; no concrete storage or HTTP imports."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol

from libs.team.contracts import Blob, Command

COPY_JOURNAL_VERSION = 1


class CopyDestination(Protocol):
    identity: str

    def check(self, values: dict[str, Any]) -> dict[str, Any]: ...
    def has_blob(self, blob: dict[str, Any]) -> bool: ...
    def upload(self, path: Path) -> Blob: ...
    def execute(self, command: Command) -> dict[str, Any]: ...


class CopyJournal(Protocol):
    origin: dict[str, str]

    def locked(self) -> AbstractContextManager[None]: ...
    def load(self) -> dict[str, Any] | None: ...
    def save(self, state: dict[str, Any]) -> None: ...
    def discard_unsubmitted(self) -> None: ...
