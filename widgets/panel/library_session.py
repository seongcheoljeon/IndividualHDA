"""Small library interaction ports shared by Personal and Team panel flows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from libs.asset_contracts import AssetData
from widgets.panel.state import PanelSessionState


@dataclass(frozen=True, slots=True)
class LibraryCapabilities:
    edit_metadata: bool = True
    local_files: bool = True
    manage_members: bool = False
    # Personal edits autosave; team edits wait for Save because every write
    # carries an expected revision and may conflict.
    explicit_save: bool = False


class PanelLibrarySession(Protocol):
    @property
    def capabilities(self) -> LibraryCapabilities: ...
    def select(self, asset_id: int | None, data: AssetData | None) -> None: ...
    def save(self) -> None: ...
    def refresh(self) -> None: ...
    def history(self) -> None: ...


class MetadataEditor(Protocol):
    def select(
        self, asset_id: int | None, note: str = "", tags: Sequence[str] = ()
    ) -> None: ...
    def save_pending(self) -> None: ...


class TeamSessionPort(Protocol):
    @property
    def writable(self) -> bool: ...
    @property
    def project(self) -> dict[str, Any]: ...
    def select(self, asset_id: int | None) -> None: ...
    def save(self) -> None: ...
    def refresh(self) -> None: ...
    def request_history(self) -> None: ...


class PersonalPanelSession:
    def __init__(
        self,
        state: PanelSessionState,
        details: MetadataEditor,
        refresh: Callable[[], None],
    ) -> None:
        self._state, self._details, self._refresh = state, details, refresh

    @property
    def capabilities(self) -> LibraryCapabilities:
        return LibraryCapabilities(edit_metadata=self._state.repository is not None)

    def select(self, asset_id: int | None, data: AssetData | None) -> None:
        self._details.select(
            asset_id,
            (data.hda_note or "") if data is not None else "",
            data.hda_tags if data is not None else (),
        )

    def save(self) -> None:
        self._details.save_pending()

    def refresh(self) -> None:
        self._refresh()

    def history(self) -> None:
        # Personal history is loaded with the library snapshot.
        pass


class TeamPanelSession:
    def __init__(self, integration: TeamSessionPort) -> None:
        self._integration = integration

    @property
    def capabilities(self) -> LibraryCapabilities:
        return LibraryCapabilities(
            edit_metadata=self._integration.writable,
            local_files=False,
            manage_members=self._integration.project.get("role") == "owner",
            explicit_save=True,
        )

    def select(self, asset_id: int | None, data: AssetData | None) -> None:
        self._integration.select(asset_id)

    def save(self) -> None:
        self._integration.save()

    def refresh(self) -> None:
        self._integration.refresh()

    def history(self) -> None:
        self._integration.request_history()
