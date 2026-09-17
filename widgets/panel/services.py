"""Composition root: select concrete adapters here, inject them into the panel."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject

from libs.ai_provider import AIProvider, AISettings, make_provider
from libs.archive_transfer import ArchiveTransfer
from libs.asset_lifecycle import (
    AssetLifecycleGateway,
    LifecycleRepository,
    LocalAssetLifecycle,
)
from libs.asset_registration import RegistrationService, RegistrationWriter
from libs.asset_rename import AssetNames
from libs.asset_search import AssetSearch
from libs.browser_search import (
    AssetSearchGateway,
    RepositoryAssetSearch,
    SearchPolicy,
    SearchRepository,
)
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.domain import LibraryContext
from libs.host_ports import HostCallbacksPort, HostCapturePort, HostScenePort
from libs.houdini_api import HoudiniAPI
from libs.paths import Paths
from libs.repository import LibraryRepository, LibrarySettings
from libs.resource_policy import CallbackPolicy, MediaPolicy, ThumbnailPolicy
from libs.runtime_settings import RUNTIME_SETTINGS_KEY, RuntimeSettings
from libs.settings_store import load_json
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.task_controller import TaskController
from widgets.panel.policy import PanelPolicy


@dataclass(frozen=True, slots=True)
class PanelServices:
    settings: LibrarySettings = LibrarySettings()
    open_database: Callable[[Path], SQLite3DatabaseAPI] = SQLite3DatabaseAPI
    archives: Callable[[Path, Path], ArchiveTransfer] = ArchiveTransfer
    tasks: Callable[[QObject], TaskController] = TaskController
    names: AssetNames = HoudiniAPI
    host_callbacks: HostCallbacksPort = HoudiniAPI
    host_capture: HostCapturePort = HoudiniAPI
    host_scene: HostScenePort = HoudiniAPI
    ai: Callable[[AISettings], AIProvider] = make_provider

    lifecycle: Callable[[LifecycleRepository, AssetNames], AssetLifecycleGateway] = (
        LocalAssetLifecycle
    )

    registration: Callable[[RegistrationWriter], RegistrationService] = (
        RegistrationService
    )

    asset_search: Callable[[QObject], AssetSearch] = AssetSearch
    search_gateway: Callable[[SearchRepository], AssetSearchGateway] = (
        RepositoryAssetSearch
    )

    policy: PanelPolicy = PanelPolicy()
    runtime: RuntimeSettings = RuntimeSettings()
    callbacks: CallbackPolicy = CallbackPolicy()
    media: MediaPolicy = MediaPolicy()
    thumbnails: ThumbnailPolicy = ThumbnailPolicy()
    help_site: str | None = None
    host_actions_enabled: bool = True

    @classmethod
    def from_saved_settings(cls) -> PanelServices:
        runtime = RuntimeSettings.from_mapping(
            load_json(Paths.json_pref_filepath).get(RUNTIME_SETTINGS_KEY)
        )
        return cls(
            runtime=runtime,
            policy=PanelPolicy(
                sync_interval_ms=runtime.sync_interval_seconds * 1000,
                search=SearchPolicy(delay_ms=runtime.search_delay_ms),
                maximum_node_batch=runtime.maximum_node_batch,
                warn_node_batch=runtime.warn_node_batch,
            ),
        )

    def repository(self, context: LibraryContext | None) -> LibraryRepository | None:
        """Storage adapter for this session; None until a data directory is chosen."""
        if self.settings.mode != "local":
            raise ValueError(
                "Server mode requires a configured remote services adapter"
            )
        if context is None:
            return None
        return SqliteLibraryRepository(context.db_filepath, self.open_database)
