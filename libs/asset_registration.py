"""Capture/publish/commit orchestration without Qt, Houdini or SQL dependencies."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from libs.repository import (
    LibraryConflict,
    LibraryError,
    RegistrationPayload,
    RegistrationResult,
)


class RegistrationCapture(Protocol):
    def asset(self, destination: Path) -> None: ...
    def thumbnail(self, destination: Path) -> None: ...


class RegistrationWriter(Protocol):
    """Commit metadata; on failure clean only files proven unreferenced.

    An uncertain commit must preserve files. The local lifecycle/repository adapter
    already implements this rule; transport-backed writers require their own receipt.
    """

    def register(
        self, payload: RegistrationPayload, asset_id: int | None = None
    ) -> RegistrationResult: ...


class RegistrationService:
    def __init__(self, writer: RegistrationWriter) -> None:
        self._writer = writer

    def register(
        self,
        payload: RegistrationPayload,
        capture: RegistrationCapture,
        asset_id: int | None = None,
    ) -> RegistrationResult:
        asset_path = payload.hda_dirpath / payload.hda_filename
        thumbnail_path = payload.thumb_dirpath / payload.thumb_filename
        for filename in (payload.hda_filename, payload.thumb_filename):
            if Path(filename).name != filename or filename in {"", ".", ".."}:
                raise LibraryError("Registration filenames must be plain filenames")
        if asset_path == thumbnail_path:
            raise LibraryError("Asset and thumbnail must use different paths")
        for destination in (asset_path, thumbnail_path):
            if destination.exists() or destination.is_symlink():
                raise LibraryConflict(
                    f"Registration file already exists: {destination}"
                )
        payload.hda_dirpath.mkdir(parents=True, exist_ok=True)
        published: list[Path] = []
        try:
            with TemporaryDirectory(
                prefix=".ihda-registration-", dir=payload.hda_dirpath
            ) as temporary:
                staging = Path(temporary)
                staged_asset = staging / payload.hda_filename
                staged_thumbnail = staging / "thumbnail" / payload.thumb_filename
                staged_thumbnail.parent.mkdir()
                capture.asset(staged_asset)
                if not staged_asset.is_file() or staged_asset.stat().st_size == 0:
                    raise LibraryError("Houdini did not create a valid asset file")
                capture.thumbnail(staged_thumbnail)
                self._publish(staged_asset, asset_path, published)
                # Thumbnail capture has historically been optional (no viewport).
                if staged_thumbnail.is_file():
                    self._publish(staged_thumbnail, thumbnail_path, published)
        except Exception:
            for path in reversed(published):
                try:
                    path.unlink(missing_ok=True)
                except OSError as error:
                    logging.warning(
                        "Could not remove incomplete registration file %s: %s",
                        path,
                        error,
                    )
            raise
        # From here the writer owns commit ambiguity and reference-aware cleanup.
        return self._writer.register(payload, asset_id)

    @staticmethod
    def _publish(source: Path, destination: Path, published: list[Path]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also closes the race after the preflight check.
        with destination.open("xb") as output:
            published.append(destination)
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
