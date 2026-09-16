"""Resumable copy workflow depending on destination and journal ports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from threading import Event
from typing import Any

from libs.file_integrity import measure_file
from libs.library_maintenance import check_cancel
from libs.team.contracts import Command, Conflict, TeamError, parse_blob
from libs.team.copy_ports import COPY_JOURNAL_VERSION, CopyJournal
from libs.team.copy_ports import CopyDestination as CopyDestination


def check_destination(destination: CopyDestination, values: dict[str, Any]) -> None:
    matches = destination.check(values)
    if matches["source_match"]:
        raise Conflict(
            "This personal asset was already copied to this project. Check the project and Trash."
        )
    if matches["name_conflict"]:
        raise Conflict(
            "This name already exists in the destination (including Trash). Choose another name."
        )


class CopyTransfer:
    def __init__(self, destination: CopyDestination, store: CopyJournal) -> None:
        self.destination, self.store = destination, store

    def run(
        self,
        plan: dict[str, Any],
        cancel: Event | None = None,
        progress: Callable[[str], None] = lambda text: None,
    ) -> dict[str, Any]:
        with self.store.locked():
            state = self._load_or_prepare(plan)
            command = Command(**state["command"])
            if state["result"] is not None:
                return dict(state["result"])
            if state["submitted"]:
                # Resolve a lost response before requiring any source files again.
                progress("Confirming the previous registration…")
                result = self._submit(command, state)
            else:
                check_destination(self.destination, command.values)
                self._upload_missing_files(
                    command, state["plan"]["paths"], cancel, progress
                )
                check_cancel(cancel)
                progress("Registering the asset and versions…")
                state["submitted"] = True
                self.store.save(state)
                result = self._submit(command, state)
            state["result"] = result
            self.store.save(state)
            return dict(result)

    def _load_or_prepare(self, plan: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load()
        if state is not None:
            return state
        command = Command("copy_asset", values=plan["values"])
        command.validate()
        if command.values["origin"] != self.store.origin:
            raise TeamError("The personal library changed; preview again")
        check_destination(self.destination, command.values)
        state = {
            "schema": COPY_JOURNAL_VERSION,
            "plan": plan,
            "command": asdict(command),
            "submitted": False,
            "result": None,
        }
        self.store.save(state)
        return state

    def _upload_missing_files(
        self,
        command: Command,
        paths: dict[str, list[str]],
        cancel: Event | None,
        progress: Callable[[str], None],
    ) -> None:
        blobs = {
            blob["digest"]: parse_blob(blob)
            for version in command.values["versions"]
            for blob in version["values"]["files"].values()
        }
        for index, blob in enumerate(blobs.values(), 1):
            check_cancel(cancel)
            progress(f"Uploading file {index} of {len(blobs)}…")
            if self.destination.has_blob(asdict(blob)):
                continue
            candidates = paths[blob.digest]
            source = next(
                (
                    Path(name)
                    for name in candidates
                    if Path(name).is_file()
                    and measure_file(Path(name), lambda: check_cancel(cancel))
                    == blob.content
                ),
                None,
            )
            if source is None:
                raise TeamError(
                    "Source file is missing or changed since preview. Restore the original file to resume: "
                    + candidates[0]
                )
            if self.destination.upload(source).content != blob.content:
                raise TeamError(
                    "Source file changed during upload; restore it before resuming"
                )

    def _submit(self, command: Command, state: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.destination.execute(command)
        except TeamError as error:
            # A 400/409 response confirms rollback. An unavailable response does
            # not: retain submitted=True so the identical receipt is replayed.
            if error.status in {400, 409}:
                state["submitted"] = False
                self.store.save(state)
            raise
