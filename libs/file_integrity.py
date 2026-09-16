"""File content values and streaming measurement, independent of host and transport."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

FILE_READ_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class FileContent:
    """Content identity: equality/hash use both SHA-256 and byte count.

    A filename is deliberately not part of content equality. Dataclass-generated
    __eq__ and __hash__ follow the same fields and keep set/dict behavior consistent.
    Content has no meaningful arithmetic or ordering operators.
    """

    digest: str
    size: int

    def __post_init__(self) -> None:
        if not isinstance(self.digest, str) or not re.fullmatch(
            r"[a-f0-9]{64}", self.digest
        ):
            raise ValueError("File content requires a SHA-256 digest")
        if not isinstance(self.size, int) or self.size < 0:
            raise ValueError("File content requires a nonnegative byte count")


def measure_file(
    path: Path, check_cancel: Callable[[], None] | None = None
) -> FileContent:
    """Hash the bytes actually read; cancellation is supplied by the caller."""
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while True:
            if check_cancel is not None:
                check_cancel()
            chunk = stream.read(FILE_READ_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return FileContent(digest.hexdigest(), size)
