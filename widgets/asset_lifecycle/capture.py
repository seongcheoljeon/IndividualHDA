"""Houdini capture adapter. Invoke on the GUI thread; never from a worker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from libs.houdini_api import HoudiniAPI
from libs.repository import LibraryError


class HoudiniRegistrationCapture:
    def __init__(self, node: Any, version: str) -> None:
        self._node = node
        self._version = version

    def asset(self, destination: Path) -> None:
        if not HoudiniAPI.create_hda_file(
            node=self._node,
            hda_dirpath=destination.parent,
            hda_filename=destination.name,
            hda_version=self._version,
        ):
            raise LibraryError("Houdini asset capture failed")

    def thumbnail(self, destination: Path) -> None:
        if not HoudiniAPI.create_thumbnail(output_filepath=destination):
            destination.unlink(missing_ok=True)
