"""Immutable blob storage. Publication is atomic; failed uploads leave no partial blob."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Iterable
from pathlib import Path

from libs.team.contracts import TeamError
from libs.team.limits import DEFAULT_MAX_UPLOAD_BYTES


class FileBlobStore:
    def __init__(self, root: Path, max_size: int = DEFAULT_MAX_UPLOAD_BYTES) -> None:
        self.root = root.resolve()
        self.max_size = max_size
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, digest: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise TeamError("Invalid blob digest")
        return self.root / digest[:2] / digest

    def put(self, chunks: Iterable[bytes]) -> tuple[str, int]:
        digest, size = hashlib.sha256(), 0
        descriptor, name = tempfile.mkstemp(prefix="upload-", dir=self.root)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                for chunk in chunks:
                    size += len(chunk)
                    if size > self.max_size:
                        raise TeamError("Upload exceeds the configured size limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            target = self.path(digest.hexdigest())
            target.parent.mkdir(exist_ok=True)
            os.replace(temporary, target)
            return digest.hexdigest(), size
        finally:
            temporary.unlink(missing_ok=True)
