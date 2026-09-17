"""Personal scene-record metadata deletion. Never modifies HIP or HDA files."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SceneRecordFiles:
    record_id: int
    hip_path: Path
    hda_path: Path


class SceneRecordRepository(Protocol):
    def scene_record_files(self, user: str) -> list[SceneRecordFiles]: ...
    def delete_scene_record(self, record_id: int) -> bool: ...


@dataclass(frozen=True, slots=True)
class RecordCleanupResult:
    deleted: tuple[int, ...]
    failed: tuple[tuple[int, str], ...]


def file_exists(path: Path) -> bool:
    """Unlike Path.exists on newer Python, preserve permission and IO errors."""
    try:
        path.stat()
    except FileNotFoundError:
        return False
    return True


class SceneRecordCleanup:
    def __init__(
        self,
        repository: SceneRecordRepository,
        exists: Callable[[Path], bool] = file_exists,
    ) -> None:
        self.repository = repository
        self.exists = exists

    def delete(self, identities: Iterable[int]) -> RecordCleanupResult:
        deleted: list[int] = []
        failed: list[tuple[int, str]] = []
        for identity in sorted(set(identities)):
            try:
                if not self.repository.delete_scene_record(identity):
                    raise ValueError("Record was not deleted; reload the library")
            except Exception as error:
                failed.append((identity, str(error)))
            else:
                deleted.append(identity)
        return RecordCleanupResult(tuple(deleted), tuple(failed))

    def cleanup(self, user: str) -> RecordCleanupResult:
        candidates: set[int] = set()
        failed: list[tuple[int, str]] = []
        for record in self.repository.scene_record_files(user):
            try:
                hip_exists = self.exists(record.hip_path)
                hda_exists = self.exists(record.hda_path)
            except OSError as error:
                failed.append((record.record_id, str(error)))
                continue
            if not hip_exists or not hda_exists:
                candidates.add(record.record_id)
        result = self.delete(candidates)
        return RecordCleanupResult(result.deleted, tuple(failed) + result.failed)
