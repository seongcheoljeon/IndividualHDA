"""One port for whichever library the panel shows: personal SQLite or a team.

Panel features used to ask the team integration whether it was active in a
dozen places and then know both worlds. They now hold a ``LibraryPort`` and never
learn which kind is behind it; the composition root picks the adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from libs.library_management import LocalManagement, ManagementGateway, RemoteManagement
from libs.paths import Paths
from libs.registration_recovery import RegistrationRecovery
from libs.team.contracts import FileKind
from libs.team.copy_source import PersonalCopySource
from libs.team.registration_recovery import TeamRegistrationRecovery

if TYPE_CHECKING:
    from PySide6 import QtCore

    from widgets.team_library.integration import MainLibraryIntegration


@dataclass(frozen=True, slots=True, kw_only=True)
class Recovery:
    """Pending registrations of the active library, retry already bound to it."""

    jobs: Callable[[], list[dict[str, Any]]]
    retry: Callable[[str], Any]
    discard: Callable[[str], None]


class LibraryPort(Protocol):
    @property
    def writable(self) -> bool: ...
    @property
    def owner(self) -> bool: ...
    @property
    def busy(self) -> bool: ...
    @property
    def supports_scene_records(self) -> bool: ...
    def refresh(self) -> None: ...
    def metadata_changed(self) -> None: ...
    def metadata_dialog_closed(self) -> None: ...
    def registration_recovery(self) -> Recovery | None: ...
    def management_gateway(self) -> ManagementGateway | None: ...
    def copy_source(self, asset_id: int) -> PersonalCopySource | None: ...

    # Requests the panel forwards. True: the library handled it. False: the
    # panel's own implementation runs. A new kind of library implements these
    # instead of every feature growing another branch.
    def register_nodes(self, nodes: Any) -> bool: ...
    def import_drop(self, drop_data: Any) -> bool: ...
    def remove_selected(self) -> bool: ...
    def context_menu(self, point: QtCore.QPoint) -> bool: ...
    def history_menu(self, point: QtCore.QPoint) -> bool: ...
    def attach(self, kind: FileKind) -> bool: ...
    def play_video(self) -> bool: ...


class PersonalLibrary:
    """The local SQLite library; the panel's own code does the work."""

    def __init__(
        self,
        *,
        database: Callable[[], Path | None],
        writer: Callable[[], Any],
        reload: Callable[[], None],
        paths_changed: Callable[[], None],
    ) -> None:
        self._database = database
        self._writer = writer
        self._reload = reload
        self._paths_changed = paths_changed

    writable = owner = True
    busy = False
    supports_scene_records = True

    def _file(self) -> Path | None:
        database = self._database()
        return database if database is not None and database.is_file() else None

    def refresh(self) -> None:
        self._reload()

    def metadata_changed(self) -> None:
        self._paths_changed()

    def metadata_dialog_closed(self) -> None:
        self._reload()

    def registration_recovery(self) -> Recovery | None:
        database = self._file()
        if database is None:
            return None
        recovery = RegistrationRecovery(database)
        return Recovery(
            jobs=recovery.jobs,
            retry=lambda identity: recovery.retry(identity, self._writer()),
            discard=recovery.discard,
        )

    def management_gateway(self) -> ManagementGateway | None:
        database = self._file()
        return LocalManagement(database) if database is not None else None

    def copy_source(self, asset_id: int) -> PersonalCopySource | None:
        database = self._database()
        return PersonalCopySource(database, asset_id) if database is not None else None

    def register_nodes(self, nodes: Any) -> bool:
        return False

    def import_drop(self, drop_data: Any) -> bool:
        return False

    def remove_selected(self) -> bool:
        return False

    def context_menu(self, point: QtCore.QPoint) -> bool:
        return False

    def history_menu(self, point: QtCore.QPoint) -> bool:
        return False

    def attach(self, kind: FileKind) -> bool:
        return False

    def play_video(self) -> bool:
        return False


class TeamLibrary:
    """A connected team library; requests go to the team integration."""

    def __init__(self, team: MainLibraryIntegration) -> None:
        self._team = team

    @property
    def writable(self) -> bool:
        return self._team.writable

    @property
    def owner(self) -> bool:
        return self._team.project.get("role") == "owner"

    @property
    def busy(self) -> bool:
        return self._team.busy

    supports_scene_records = False

    def refresh(self) -> None:
        if self._team.presenter is not None:
            self._team.presenter.refresh()

    def metadata_changed(self) -> None:
        self.refresh()

    def metadata_dialog_closed(self) -> None:
        self._team.show_status("")

    def registration_recovery(self) -> Recovery | None:
        catalog = self._team.require_catalog()
        recovery = TeamRegistrationRecovery(
            Paths.config_dirpath / "workspace" / "registrations", catalog.namespace
        )
        return Recovery(
            jobs=recovery.jobs,
            retry=lambda identity: recovery.retry(
                identity, catalog, self._team.pending
            ),
            discard=recovery.discard,
        )

    def management_gateway(self) -> ManagementGateway | None:
        return RemoteManagement(self._team.require_catalog(), self._team.pending)

    def copy_source(self, asset_id: int) -> PersonalCopySource | None:
        return None  # copying goes from the personal library to a team, not back

    def register_nodes(self, nodes: Any) -> bool:
        self._team.actions.register_nodes(nodes)
        return True

    def import_drop(self, drop_data: Any) -> bool:
        self._team.actions.import_drop(drop_data)
        return True

    def remove_selected(self) -> bool:
        self._team.actions.remove()
        return True

    def context_menu(self, point: QtCore.QPoint) -> bool:
        self._team.actions.context_menu(point)
        return True

    def history_menu(self, point: QtCore.QPoint) -> bool:
        self._team.actions.history_menu(point)
        return True

    def attach(self, kind: FileKind) -> bool:
        self._team.actions.attach(kind)
        return True

    def play_video(self) -> bool:
        self._team.actions.play_video()
        return True
