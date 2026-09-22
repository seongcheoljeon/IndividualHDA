"""Workspace state and commands without Qt, SQL, HTTP or Houdini imports."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol

from libs.search_limits import TEAM_PAGE_DEFAULT, TEAM_PAGE_MAX
from libs.tags import normalize_tags
from libs.team.contracts import (
    DEFAULT_AUDIT_EVENT_LIMIT,
    AssetCatalog,
    Blob,
    Command,
    FileKind,
    Operation,
    Page,
    TeamError,
)
from libs.team.pending import PendingCommand


class WorkspaceBackend(AssetCatalog, Protocol):
    @property
    def namespace(self) -> str: ...

    def upload(self, path: Path) -> Blob: ...
    def download(self, blob: Blob) -> Path: ...
    def events(
        self, asset_uuid: str, offset: int = 0, limit: int = DEFAULT_AUDIT_EVENT_LIMIT
    ) -> list[dict[str, Any]]: ...


class WorkspaceView(Protocol):
    def show_page(self, page: Page) -> None: ...
    def show_asset(
        self, asset: dict[str, Any], note: str, tags: Sequence[str]
    ) -> None: ...
    def show_error(self, message: str) -> None: ...
    def show_failure(self, error: Exception) -> None: ...
    def asset_committed(self, result: dict[str, Any]) -> None: ...
    def show_status(self, message: str) -> None: ...
    def show_busy(self, busy: bool) -> None: ...
    def show_history(
        self, items: list[dict[str, Any]], events: Sequence[dict[str, Any]] = ()
    ) -> None: ...
    def file_ready(self, path: Path, asset: dict[str, Any]) -> None: ...


class WorkspaceExecutor(Protocol):
    def submit(
        self,
        operation: Callable[[], Any],
        finished: Callable[[Any, Exception | None], None],
    ) -> bool: ...


class WorkspacePresenter:
    def __init__(
        self,
        view: WorkspaceView,
        backend: WorkspaceBackend,
        executor: WorkspaceExecutor,
        pending: PendingCommand,
        *,
        page_size: int = TEAM_PAGE_DEFAULT,
    ) -> None:
        self._view, self._backend, self._executor, self._pending = (
            view,
            backend,
            executor,
            pending,
        )
        self._assets: dict[int, dict[str, Any]] = {}
        self._drafts: dict[int, tuple[str, list[str]]] = {}
        self._selected: int | None = None
        self._selection_generation = 0
        self._busy = False
        self.failed_command: Command | None = None
        self._closed = False
        if type(page_size) is not int or not 1 <= page_size <= TEAM_PAGE_MAX:
            raise ValueError("Invalid team page size")
        self.query, self.offset, self.limit = "", 0, page_size

    def _run(
        self, operation: Callable[[], Any], completed: Callable[[Any], None]
    ) -> bool:
        if self._busy or self._closed:
            return False
        self._busy = True
        self._view.show_busy(True)

        def finished(value: Any, error: Exception | None) -> None:
            self._busy = False
            if self._closed:
                return
            self._view.show_busy(False)
            if error is not None:
                self._view.show_failure(error)
            else:
                completed(value)

        try:
            if not self._executor.submit(operation, finished):
                finished(None, TeamError("Wait for the current operation to finish"))
                return False
        except Exception as error:
            finished(None, error)
            return False
        return True

    def refresh(self, query: str = "", offset: int = 0) -> None:
        if self._busy:
            return
        self.query, self.offset = query, max(0, offset)
        self._run(
            lambda: self._backend.list_assets(query, self.offset, self.limit),
            self.page_ready,
        )

    def page_ready(self, page: Page) -> None:
        for asset in page.items:
            asset_id = asset["id"]
            previous = self._assets.get(asset_id)
            draft = self._drafts.get(asset_id)
            if previous is None or draft is None or draft == self._text(previous):
                self._assets[asset_id] = asset
                self._drafts[asset_id] = self._text(asset)
        self._view.show_page(page)
        self._view.show_status(
            f"{page.total} assets · loaded {page.offset + len(page.items)} · drafts are kept until this window closes"
        )

    @staticmethod
    def _text(asset: dict[str, Any]) -> tuple[str, list[str]]:
        return asset.get("note", ""), list(asset.get("tags", []))

    def select(self, asset_id: int | None) -> None:
        if asset_id is not None and asset_id not in self._assets:
            return
        if self._selected != asset_id:
            self._selection_generation += 1
        self._selected = asset_id
        if asset_id is None:
            return
        self._view.show_asset(self._assets[asset_id], *self._drafts[asset_id])

    def edit(self, note: str, tags: Sequence[str]) -> None:
        if self._selected is not None:
            self._drafts[self._selected] = (note, list(tags))

    def _selection(self) -> dict[str, Any]:
        if self._selected is None:
            raise TeamError("Select an asset first")
        return self._assets[self._selected]

    def _execute(self, command: Command) -> dict[str, Any]:
        if self._pending.load() is not None:
            raise TeamError(
                "Resolve the pending request with Retry before starting another write"
            )
        self._pending.save(command)
        return self._send(command)

    def _send(self, command: Command) -> dict[str, Any]:
        try:
            result = self._backend.execute(command)
        except TeamError as error:
            self.failed_command = command
            if error.status in {400, 403, 404, 409, 422}:
                self._pending.clear(command.request_id)
            raise
        self.failed_command = None
        self._pending.clear(command.request_id)
        return result

    def mutate(
        self, operation: Operation, values: dict[str, Any], asset_id: int | None = None
    ) -> None:
        """Write to the selected asset, or to ``asset_id`` (a card's star)."""
        try:
            if asset_id is None:
                asset = self._selection()
            elif asset_id in self._assets:
                asset = self._assets[asset_id]
            else:
                raise TeamError("The asset is no longer loaded")
            command = Command(
                operation,
                asset_id=asset["id"],
                expected_revision=asset.get("preference_revision", 0)
                if operation == "preference"
                else asset["revision"],
                values=values,
            )
            command.validate()
        except TeamError as error:
            self._view.show_error(str(error))
            return
        self._run(lambda: self._execute(command), self._committed)

    def save_metadata(self) -> None:
        if self._selected is not None:
            note, tags = self._drafts[self._selected]
            self.mutate("metadata", {"note": note, "tags": normalize_tags(tags)})

    def _committed(self, result: dict[str, Any]) -> None:
        asset_id = result["id"]
        previous = self._assets.get(asset_id)
        if result.get("deleted"):
            self._assets.pop(asset_id, None)
            self._drafts.pop(asset_id, None)
            if self._selected == asset_id:
                self.select(None)
        else:
            self._assets[asset_id] = result
            if (
                asset_id not in self._drafts
                or previous is not None
                and self._drafts[asset_id] == self._text(previous)
            ):
                self._drafts[asset_id] = self._text(result)
            if self._selected == asset_id:
                self.select(asset_id)
        self._view.show_status(
            "Saved. Refresh the list to see name, version or deletion changes."
        )
        self._view.asset_committed(result)

    def reload_selected(self) -> None:
        try:
            asset_id = self._selection()["id"]
        except TeamError as error:
            self._view.show_error(str(error))
            return

        def ready(asset: dict[str, Any]) -> None:
            self._assets[asset_id] = asset
            if self._selected == asset_id:
                self.select(asset_id)
            self._view.show_status(
                "Latest revision loaded. Compare the stored values with your draft before saving."
            )

        self._run(lambda: self._backend.get_asset(asset_id), ready)

    def retry(self) -> None:
        def operation() -> dict[str, Any]:
            command = self._pending.load()
            if command is None:
                raise TeamError("There is no pending request")
            return self._send(command)

        self._run(operation, self._committed)

    def register(
        self,
        path: Path,
        name: str,
        category: str,
        version: str,
        metadata: dict[str, Any],
        thumbnail: Path | None = None,
        *,
        new_version: bool = False,
        description: str = "",
    ) -> None:
        try:
            asset = dict(self._selection()) if new_version else None
        except TeamError as error:
            self._view.show_error(str(error))
            return

        from libs.paths import Paths
        from libs.team.registration_recovery import TeamRegistrationRecovery

        recovery = TeamRegistrationRecovery(
            Paths.config_dirpath / "workspace" / "registrations",
            self._backend.namespace,
        )
        metadata = dict(metadata)
        identity = metadata.pop("_registration_job_id", None)

        def operation() -> dict[str, Any]:
            job_id = recovery.prepare(
                path,
                name,
                category,
                version,
                metadata or (asset.get("metadata", {}) if asset else {}),
                thumbnail,
                asset,
                description,
                identity,
            )
            return recovery.retry(job_id, self._backend, self._pending)

        self._run(operation, self._committed)

    def attach_media(self, path: Path, kind: str) -> None:
        try:
            asset = dict(self._selection())
        except TeamError as error:
            self._view.show_error(str(error))
            return

        def operation() -> dict[str, Any]:
            blob = self._backend.upload(path)
            return self._execute(
                Command(
                    "media",
                    asset_id=asset["id"],
                    expected_revision=asset["revision"],
                    values={"kind": kind, "file": asdict(blob)},
                )
            )

        self._run(operation, self._committed)

    def history(self) -> bool:
        try:
            asset = self._selection()
        except TeamError as error:
            self._view.show_error(str(error))
            return False
        asset_id, asset_uuid = asset["id"], asset.get("asset_uuid", "")
        generation = self._selection_generation

        def load() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            items = self._backend.histories(asset_id)
            try:
                events = self._backend.events(asset_uuid) if asset_uuid else []
            except TeamError:
                events = []  # activity is decoration; never hide the versions
            return items, events

        def ready(result: tuple[list[dict[str, Any]], list[dict[str, Any]]]) -> None:
            if self._selected == asset_id and self._selection_generation == generation:
                self._view.show_history(*result)

        return self._run(load, ready)

    def restore(self, asset_id: int, revision: int) -> None:
        """Undo of a trash: the revision is the one the delete result reported."""
        command = Command(
            "restore", asset_id=asset_id, expected_revision=revision, values={}
        )
        if not self._run(lambda: self._execute(command), self._committed):
            self._view.show_error("Wait for the current operation to finish")

    def delete_history(self, asset_id: int, history_id: int) -> None:
        asset = self._assets.get(asset_id)
        if asset is None:
            self._view.show_error("The history asset is no longer loaded")
            return
        command = Command(
            "delete_history",
            asset_id=asset_id,
            expected_revision=asset["revision"],
            values={"history_id": history_id},
        )
        self._run(lambda: self._execute(command), self._committed)

    def download(
        self, kind: FileKind = "asset", historical: dict[str, Any] | None = None
    ) -> None:
        from libs.team.contracts import parse_blob

        try:
            asset = historical or self._selection()
            blob = parse_blob(asset.get("files", {}).get(kind))
        except TeamError as error:
            self._view.show_error(str(error))
            return

        def download() -> Path:
            self._backend.get_asset(asset["id"])
            if asset.get("version_uuid") and not any(
                row["document"].get("version_uuid") == asset["version_uuid"]
                for row in self._backend.histories(asset["id"])
            ):
                raise TeamError(
                    "This version is no longer available. Refresh the library."
                )
            return self._backend.download(blob)

        self._run(download, lambda path: self._view.file_ready(path, asset))

    @property
    def unsaved_fields(self) -> tuple[bool, bool]:
        """(note, tags) dirtiness of the selected asset, for the two indicators.

        has_unsaved_changes below answers a different question -- "may we leave
        this library?" -- and must keep scanning every cached asset.
        """
        asset_id = self._selected
        draft = self._drafts.get(asset_id) if asset_id is not None else None
        if draft is None or asset_id not in self._assets:
            return False, False
        note, tags = self._text(self._assets[asset_id])
        return draft[0] != note, draft[1] != tags

    @property
    def has_unsaved_changes(self) -> bool:
        return any(
            asset_id in self._assets and draft != self._text(self._assets[asset_id])
            for asset_id, draft in self._drafts.items()
        )

    def close(self) -> None:
        self._closed = True
