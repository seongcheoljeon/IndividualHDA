from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

from libs.team.contracts import Command, Conflict, Page, Unavailable
from libs.team.pending import PendingCommand
from widgets.team_library.presenter import WorkspacePresenter


class View:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.busy = False
        self.asset: Any = None
        self.page: Any = None

    def show_status(self, message: str) -> None:
        self.messages.append(message)

    show_error = show_status

    def show_busy(self, busy: bool) -> None:
        self.busy = busy

    def show_asset(self, asset: Any, note: str, tags: str) -> None:
        self.asset = asset, note, tags

    def show_page(self, page: Any) -> None:
        self.page = page


class Executor:
    def __init__(self) -> None:
        self.queued: (
            tuple[Callable[[], Any], Callable[[Any, Exception | None], None]] | None
        ) = None

    def submit(self, operation: Any, finished: Any) -> bool:
        assert self.queued is None
        self.queued = operation, finished
        return True

    def complete(self) -> None:
        assert self.queued is not None
        operation, finished = self.queued
        self.queued = None
        try:
            result = operation()
        except Exception as error:
            finished(None, error)
        else:
            finished(result, None)


class Backend:
    def __init__(self) -> None:
        self.items = {
            identifier: {
                "id": identifier,
                "revision": 1,
                "name": name,
                "version": "1",
                "note": "old",
                "tags": [],
                "category": "sop",
            }
            for identifier, name in [(1, "Water"), (2, "Fire")]
        }
        self.receipts: dict[str, Any] = {}
        self.lose_response = False
        self.writes = 0

    def list_assets(self, query: str = "", offset: int = 0, limit: int = 100) -> Page:
        return Page(copy.deepcopy(list(self.items.values())), 2, 0, limit, 1)

    def get_asset(self, asset_id: int) -> Any:
        return copy.deepcopy(self.items[asset_id])

    def execute(self, command: Command) -> Any:
        if command.request_id in self.receipts:
            return copy.deepcopy(self.receipts[command.request_id])
        item = self.items[command.asset_id]
        if command.expected_revision != item["revision"]:
            raise Conflict("Reload before saving")
        self.writes += 1
        item.update(command.values)
        item["revision"] += 1
        self.receipts[command.request_id] = copy.deepcopy(item)
        if self.lose_response:
            self.lose_response = False
            raise Unavailable("Response lost")
        return copy.deepcopy(item)


def workspace(tmp_path: Path) -> tuple[Any, ...]:
    view, backend, executor = View(), Backend(), Executor()
    pending = PendingCommand(tmp_path / "pending.json")
    presenter = WorkspacePresenter(view, backend, executor, pending)
    presenter.refresh()
    executor.complete()
    presenter.select(1)
    return presenter, view, backend, executor, pending


def test_async_save_captures_selection_and_keeps_newer_draft(tmp_path: Path) -> None:
    presenter, view, backend, executor, pending = workspace(tmp_path)
    presenter.edit("first", "#water")
    presenter.save_metadata()
    presenter.edit("newer", "#new")
    presenter.select(2)
    executor.complete()
    assert backend.items[1]["note"] == "first" and backend.items[2]["note"] == "old"
    assert view.asset[0]["id"] == 2
    presenter.select(1)
    assert view.asset[1:] == ("newer", "#new")
    assert not pending.path.exists() and not view.busy


def test_lost_response_can_be_retried_after_restart_without_duplicate_write(
    tmp_path: Path,
) -> None:
    presenter, view, backend, executor, pending = workspace(tmp_path)
    backend.lose_response = True
    presenter.edit("saved once", "")
    presenter.save_metadata()
    executor.complete()
    command = pending.load()
    assert command is not None and backend.writes == 1
    presenter.close()
    restarted = WorkspacePresenter(
        view, backend, executor, PendingCommand(pending.path)
    )
    restarted.retry()
    executor.complete()
    assert backend.writes == 1 and pending.load() is None


def test_conflict_keeps_draft_and_refresh_does_not_silently_rebase_it(
    tmp_path: Path,
) -> None:
    presenter, view, backend, executor, pending = workspace(tmp_path)
    presenter.edit("my draft", "#water")
    backend.items[1].update(note="other user's note", revision=2)
    presenter.refresh()
    executor.complete()
    presenter.select(1)
    assert view.asset[0]["revision"] == 1
    presenter.save_metadata()
    executor.complete()
    assert pending.load() is None and backend.writes == 0
    assert view.asset[1] == "my draft"
    presenter.reload_selected()
    executor.complete()
    assert (
        view.asset[0]["revision"] == 2 and view.asset[0]["note"] == "other user's note"
    )
    assert view.asset[1] == "my draft"


def test_closing_does_not_deliver_results_to_dead_view(tmp_path: Path) -> None:
    presenter, view, backend, executor, pending = workspace(tmp_path)
    presenter.edit("commit on shutdown", "")
    presenter.save_metadata()
    before = copy.deepcopy(view.asset)
    presenter.close()
    executor.complete()
    assert backend.items[1]["note"] == "commit on shutdown"
    assert view.asset == before and pending.load() is None


def test_personal_ui_import_does_not_load_server_dependencies() -> None:
    import subprocess
    import sys

    code = """
import builtins
original = builtins.__import__
def guard(name, *args, **kwargs):
    if name.split('.')[0] in {'fastapi', 'sqlalchemy', 'psycopg', 'httpx', 'ihda_server'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guard
from libs.team.panel_catalog import PanelCatalog
from widgets.library_connection.dialog import ConnectionDialog
from widgets.team_library.integration import MainLibraryIntegration
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_pending_ownership_and_late_completion(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from libs.team.contracts import TeamError

    path = tmp_path / "shared.json"
    commands = [Command("metadata", asset_id=1, expected_revision=1) for _ in range(4)]

    def claim(command: Command) -> bool:
        try:
            PendingCommand(path).save(command)
            return True
        except TeamError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        claimed = list(pool.map(claim, commands))
    assert sum(claimed) == 1
    winner = commands[claimed.index(True)]
    pending = PendingCommand(path)
    assert pending.load() == winner
    pending.clear(winner.request_id)
    newer = Command("metadata", asset_id=2, expected_revision=1)
    pending.save(newer)
    pending.clear(winner.request_id)
    assert pending.load() == newer


def test_history_delete_keeps_its_asset_when_selection_changes(tmp_path: Path) -> None:
    presenter, _, backend, executor, _ = workspace(tmp_path)
    presenter.select(2)
    presenter.delete_history(1, 10)
    executor.complete()
    assert backend.items[1]["history_id"] == 10
    assert "history_id" not in backend.items[2]


def test_unsaved_fields_is_per_field_and_per_selected_asset(tmp_path: Path) -> None:
    """Two indicators need per-field dirtiness; leaving the library needs the
    whole-library answer. The two questions stay separate."""
    presenter, view, backend, executor, pending = workspace(tmp_path)
    assert presenter.unsaved_fields == (False, False)
    assert not presenter.has_unsaved_changes

    note, tags = view.asset[1:]
    presenter.edit("edited note", tags)
    assert presenter.unsaved_fields == (True, False)
    presenter.edit(note, "#brand #new")
    assert presenter.unsaved_fields == (False, True)

    # Selecting a clean asset clears the indicators, but the library is still
    # dirty, so the "discard unsaved edits?" prompt must keep firing.
    presenter.select(2)
    assert presenter.unsaved_fields == (False, False)
    assert presenter.has_unsaved_changes
