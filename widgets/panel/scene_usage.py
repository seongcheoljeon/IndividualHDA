"""Capture scene facts on the GUI thread, deliver on a dedicated worker."""

from __future__ import annotations

import logging
import platform
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from libs.host_ports import HostScenePort
from libs.library_metadata import new_identity
from libs.scene_outbox import SceneOutbox
from libs.task_controller import TaskController
from libs.team.panel_catalog import PanelCatalog


@dataclass(frozen=True, slots=True, kw_only=True)
class SceneUsageBindings:
    host: HostScenePort
    closing: Callable[[], bool]
    actor: Callable[[], str]
    catalog: Callable[[], PanelCatalog | None]
    database: Callable[[], Path | None]
    message: Callable[[str, int], None]
    deliver_local: Callable[[Path, str, SceneOutbox], int]


@dataclass(frozen=True, slots=True, kw_only=True)
class SceneObservation:
    node: Any
    version_uuid: str
    namespace: str


class SceneUsageIntegration:
    def __init__(
        self, bindings: SceneUsageBindings, tasks: TaskController, outbox: SceneOutbox
    ) -> None:
        self.bindings = bindings
        self.outbox = outbox
        self.tasks = tasks
        self.unsaved = "unsaved:" + new_identity()
        self._previous_unsaved: str | None = None
        self._observed: list[SceneObservation] = []
        self._scene_path: str | None = None

    def observe(self, node: Any, version_uuid: str, namespace: str) -> None:

        try:
            path = self.bindings.host.current_hipfile()
            entry = SceneObservation(
                node=node, version_uuid=version_uuid, namespace=namespace
            )
            if entry not in self._observed:
                self._observed.append(entry)
            self._scene_path = str(path)
            saved = path.name.casefold() not in {
                "untitled.hip",
                "untitled.hiplc",
                "untitled.hipnc",
            }
            key = str(path.resolve()) if saved else self.unsaved
            values = {
                "version_uuid": version_uuid,
                "scene_key": key,
                "scene_path": str(path) if saved else "",
                "node_path": node.path(),
                "houdini_version": self.bindings.host.current_houdini_version(),
                "os": platform.system(),
            }
            if saved and self._previous_unsaved:
                values["previous_scene_key"] = self._previous_unsaved
            if not saved:
                self._previous_unsaved = self.unsaved
            self.outbox.enqueue(namespace, values)
        except Exception:
            logging.exception("Imported asset; scene record could not be queued")

    def flush(self) -> None:
        if self.bindings.closing() or self.tasks.busy:
            return

        try:
            path = str(self.bindings.host.current_hipfile())
            if self._scene_path is not None and path != self._scene_path:
                # Only surviving imported nodes are observations in the saved scene.
                observed, self._observed = self._observed, []
                for observation in observed:
                    node = observation.node
                    try:
                        node.path()
                    except Exception:
                        continue
                    self.observe(node, observation.version_uuid, observation.namespace)
                self._scene_path = path
        except Exception:
            pass
        actor = self.bindings.actor()
        catalog = self.bindings.catalog()
        if catalog is not None:

            def send() -> int:
                if not catalog.tracking_supported():
                    return 0
                return self.outbox.flush(catalog.namespace, catalog.tracking_execute)
        else:
            database = self.bindings.database()
            if database is None:
                return

            def send() -> int:
                return self.bindings.deliver_local(database, actor, self.outbox)

        self.tasks.start(send, self._delivered)

    def _delivered(self, pending: int) -> None:
        if pending:
            logging.warning(
                "%s scene records await delivery; Library Tools > Retry scene reporting",
                pending,
            )
            if not self.bindings.closing():
                self.bindings.message(
                    f"{pending} scene records await delivery. Library Tools → Retry scene reporting",
                    10000,
                )

    def close(self) -> None:
        self.tasks.drain()
