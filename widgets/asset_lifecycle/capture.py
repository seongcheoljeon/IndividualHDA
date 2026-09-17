"""Houdini capture adapter. Invoke on the GUI thread; never from a worker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from libs.host_ports import HostCapturePort
from libs.houdini_api import HoudiniAPI
from libs.repository import LibraryError


class HoudiniRegistrationCapture:
    def __init__(
        self, node: Any, version: str, host: HostCapturePort = HoudiniAPI
    ) -> None:
        self._host = host
        self._node = node
        self._version = version

    def asset(self, destination: Path) -> None:
        if not self._host.create_hda_file(
            node=self._node,
            hda_dirpath=destination.parent,
            hda_filename=destination.name,
            hda_version=self._version,
        ):
            raise LibraryError("Houdini asset capture failed")

    def thumbnail(self, destination: Path) -> None:
        if not self._host.create_thumbnail(output_filepath=destination):
            destination.unlink(missing_ok=True)
