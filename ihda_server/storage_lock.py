"""Cross-process storage maintenance lock without a Qt runtime dependency."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from libs.team.contracts import Unavailable


@contextmanager
def storage_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".team-storage.lock").open("a+b") as stream:
        acquired = False
        try:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    stream.seek(0, 2)
                    if stream.tell() == 0:
                        stream.write(b"0")
                        stream.flush()
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as error:
                raise Unavailable(
                    "Storage maintenance or upload is active; retry shortly"
                ) from error
            yield
        finally:
            if acquired:
                if sys.platform == "win32":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
