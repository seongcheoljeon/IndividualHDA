"""Application operations for registration, rename and removal.

The local adapter owns path planning. A remote implementation can accept the same
asset identity/name request and perform file changes on the server instead.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from libs.asset_names import validate_name
from libs.asset_rename import AssetNames, RenamePlan, build_rename_plan
from libs.domain import AssetData
from libs.repository import RegistrationPayload, RegistrationResult


@dataclass(frozen=True)
class RenameResult:
    plan: RenamePlan
    asset_rows: int
    history_rows: int


class LifecycleRepository(Protocol):
    def register_asset(self, payload: RegistrationPayload) -> RegistrationResult: ...
    def add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult: ...
    def video_matches_version(self, asset_id: int, version: str) -> bool: ...
    def rename_asset(self, plan: RenamePlan) -> tuple[int, int]: ...
    def delete_asset(self, asset_id: int, directory: Path) -> None: ...
    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None: ...


class AssetLifecycleGateway(Protocol):
    def register(
        self, payload: RegistrationPayload, asset_id: int | None = None
    ) -> RegistrationResult: ...
    def rename(self, asset: AssetData, name: str) -> RenameResult: ...
    def delete(self, asset_id: int, directory: Path) -> None: ...
    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None: ...


class LocalAssetLifecycle:
    def __init__(self, repository: LifecycleRepository, names: AssetNames) -> None:
        self._repository = repository
        self._names = names

    def register(
        self, payload: RegistrationPayload, asset_id: int | None = None
    ) -> RegistrationResult:
        if asset_id is None:
            return self._repository.register_asset(payload)
        return self._repository.add_version(asset_id, payload)

    def rename(self, asset: AssetData, name: str) -> RenameResult:
        validation = validate_name(name, asset.get("hda_name", ""))
        if not validation.valid:
            raise ValueError(validation.error)
        name = validation.name
        node_type = asset.get("node_type_name", "").split(":", 1)[0].strip()
        if node_type and name in {node_type, node_type + "1"}:
            raise ValueError("The asset name must differ from its node type")
        plan = build_rename_plan(
            asset,
            name,
            self._names,
            rename_video=self._repository.video_matches_version(
                asset["hda_id"], asset["hda_version"]
            ),
        )
        asset_rows, history_rows = self._repository.rename_asset(plan)
        return RenameResult(plan, asset_rows, history_rows)

    def delete(self, asset_id: int, directory: Path) -> None:
        self._repository.delete_asset(asset_id, directory)

    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None:
        self._repository.delete_history(asset_id, history_id, files)
