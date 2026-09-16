"""Small library interaction ports shared by Personal and Team panel flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from libs.domain import AssetData
from widgets.asset_details.presenter import Field


@dataclass(frozen=True, slots=True)
class LibraryCapabilities:
    edit_metadata: bool = True
    local_files: bool = True
    manage_members: bool = False
    confirm_metadata_save: bool = True


class PanelLibrarySession(Protocol):
    @property
    def capabilities(self) -> LibraryCapabilities: ...
    def select(self, asset_id: int | None, data: AssetData | None) -> None: ...
    def save(self, field: Field) -> None: ...
    def refresh(self) -> None: ...
    def history(self) -> None: ...


class PersonalPanelSession:
    def __init__(self, window: Any) -> None:
        self._window = window

    @property
    def capabilities(self) -> LibraryCapabilities:
        return LibraryCapabilities(edit_metadata=self._window._repository is not None)

    def select(self, asset_id: int | None, data: AssetData | None) -> None:
        self._window._details.presenter.select(
            asset_id,
            (data or {}).get("hda_note") or "",
            (data or {}).get("hda_tags") or [],
        )

    def save(self, field: Field) -> None:
        self._window._details.presenter.save(field)

    def refresh(self) -> None:
        self._window._library_sync_presenter.refresh()

    def history(self) -> None:
        # Personal history is loaded with the library snapshot.
        pass


class TeamPanelSession:
    def __init__(self, integration: Any) -> None:
        self._integration = integration

    @property
    def capabilities(self) -> LibraryCapabilities:
        return LibraryCapabilities(
            edit_metadata=self._integration.writable,
            local_files=False,
            manage_members=self._integration.project.get("role") == "owner",
            confirm_metadata_save=False,
        )

    def select(self, asset_id: int | None, data: AssetData | None) -> None:
        self._integration.select(asset_id)

    def save(self, field: Field) -> None:
        self._integration.save(field)

    def refresh(self) -> None:
        self._integration.refresh()

    def history(self) -> None:
        self._integration.request_history()
