"""Durable uncertain writes with cross-process ownership and conditional clearing."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from libs.settings_store import save_json
from libs.team.contracts import API_VERSION, Command, TeamError


class PendingCommand:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a+b") as lock:
            if sys.platform == "win32":
                import msvcrt

                lock.seek(0, os.SEEK_END)
                if lock.tell() == 0:
                    lock.write(b"0")
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if sys.platform == "win32":
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _read(self) -> Command | None:
        if not self.path.is_file():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("api_version") != API_VERSION:
            raise TeamError(
                "A pre-upgrade request is preserved. Review it against the latest asset before applying a new request."
            )
        command = Command(**payload["command"])
        command.validate()
        return command

    def legacy(self) -> dict[str, object] | None:
        with self._lock():
            if not self.path.is_file():
                return None
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return dict(payload) if payload.get("api_version") != API_VERSION else None

    def archive_legacy(self) -> None:
        from uuid import uuid4

        with self._lock():
            if not self.path.is_file():
                return
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("api_version") == API_VERSION:
                raise TeamError("The pending request changed; review it again")
            self.path.rename(
                self.path.with_name(self.path.name + ".pre-v2-" + uuid4().hex + ".json")
            )

    def load(self) -> Command | None:
        with self._lock():
            return self._read()

    def save(self, command: Command) -> None:
        command.validate()
        with self._lock():
            if self.path.exists():
                raise TeamError(
                    "Another workspace has a pending request; resolve it first"
                )
            save_json(
                self.path, {"api_version": API_VERSION, "command": asdict(command)}
            )

    def clear(self, request_id: str | None = None) -> None:
        with self._lock():
            command = self._read()
            if command is not None and (
                request_id is None or command.request_id == request_id
            ):
                self.path.unlink()
