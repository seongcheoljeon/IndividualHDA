"""Prepare and resume copies without accessing widgets from a worker thread."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event
from typing import Any

from libs.team.client import HttpCatalog
from libs.team.contracts import Command
from libs.team.copy_destination import HttpCopyDestination
from libs.team.copy_journal import CopyJobStore
from libs.team.copy_ports import CopyDestination, CopyJournal
from libs.team.copy_source import CopySource
from libs.team.copy_workflow import CopyTransfer, check_destination


class CopyPresenter:
    def __init__(
        self,
        source: CopySource,
        root: Path,
        *,
        destination_factory: Callable[
            [HttpCatalog], CopyDestination
        ] = HttpCopyDestination,
        journal_factory: Callable[
            [Path, str, dict[str, str]], CopyJournal
        ] = CopyJobStore,
    ) -> None:
        self.source, self.root = source, root
        self._destination_factory = destination_factory
        self._journal_factory = journal_factory

    def prepare(
        self,
        catalog: HttpCatalog,
        name: str,
        all_versions: bool,
        previews: bool,
        cancel: Event,
    ) -> dict[str, Any]:
        destination = self._destination_factory(catalog)
        store = self._journal_factory(
            self.root / "copies", destination.identity, self.source.identity()
        )
        state = store.load()
        if state is not None:
            return {
                "plan": state["plan"],
                "transfer": CopyTransfer(destination, store),
                "frozen": True,
                "result": state["result"],
            }
        plan = self.source.preview(
            all_versions=all_versions, previews=previews, cancel=cancel
        )
        if name:
            plan["values"]["name"] = name
        Command("copy_asset", values=plan["values"]).validate()
        check_destination(destination, plan["values"])
        return {
            "plan": plan,
            "transfer": CopyTransfer(destination, store),
            "frozen": False,
            "result": None,
        }
