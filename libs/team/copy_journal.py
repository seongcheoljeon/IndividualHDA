"""Durable local copy journal; format and request identity survive refactoring."""

from __future__ import annotations

import hashlib
import json
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from libs.operation_journal import operation_lock, sync_directory
from libs.settings_store import save_json
from libs.team.contracts import Command, TeamError
from libs.team.copy_ports import COPY_JOURNAL_VERSION


class CopyJobStore:
    def __init__(self, root: Path, destination: str, origin: dict[str, str]) -> None:
        key = hashlib.sha256(
            json.dumps([destination, origin], sort_keys=True).encode()
        ).hexdigest()
        self.origin = dict(origin)
        self.root = root / key
        self.path = self.root / "copy.json"

    def locked(self) -> AbstractContextManager[None]:
        return operation_lock(self.root)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema") != COPY_JOURNAL_VERSION:
            raise TeamError("Unsupported copy journal; retain it for recovery")
        command = Command(**state["command"])
        command.validate()
        if (
            command.values["origin"] != self.origin
            or command.values != state["plan"]["values"]
        ):
            raise TeamError(
                "Copy journal does not match its source snapshot; retain it for recovery"
            )
        return dict(state)

    def discard_unsubmitted(self) -> None:
        with self.locked():
            state = self.load()
            if state and (state["submitted"] or state["result"] is not None):
                raise TeamError(
                    "Resume first to confirm the previous registration before changing the selection"
                )
            self.path.unlink(missing_ok=True)
            sync_directory(self.root)

    def save(self, state: dict[str, Any]) -> None:
        save_json(self.path, state)
        sync_directory(self.root)
