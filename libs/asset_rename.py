"""Asset rename planning and execution, independent of widgets and SQL layout."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from libs.contracts import TransactionalRepository, OperationFactory
from libs.domain import AssetData
from libs.path_updates import relocated_path
from libs.operation_journal import durable_operation


class AssetNames(Protocol):
    def make_hda_filename(
        self,
        name: str | None = None,
        version: str | None = None,
        with_suffix: bool = True,
    ) -> str: ...
    def make_thumbnail_filename(
        self, name: str | None = None, version: str | None = None
    ) -> str: ...
    def make_video_filename(
        self, name: str | None = None, version: str | None = None
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class RenamePlan:
    asset_id: int
    name: str
    version: str
    directory: Path
    filename: str
    node_path: str
    thumbnail_directory: Path | None
    thumbnail_filename: str | None
    video_directory: Path | None
    video_filename: str | None
    moves: tuple[tuple[Path, Path], ...]


class RenameRepository(TransactionalRepository, Protocol):
    def apply_rename(self, plan: RenamePlan) -> tuple[int, int]: ...


def build_rename_plan(
    data: AssetData, name: str, names: AssetNames, *, rename_video: bool
) -> RenamePlan:
    if not name or name in (".", "..") or any(char in name for char in "/\\"):
        raise ValueError("Asset name must be a single directory name")
    old_directory, old_filename = data.get("hda_dirpath"), data.get("hda_filename")
    if old_directory is None or not old_filename:
        raise ValueError("Asset file location is missing")
    old_file = old_directory / old_filename
    if not old_file.is_file():
        raise FileNotFoundError(old_file)
    directory = old_directory.with_name(name)
    if directory != old_directory and directory.exists():
        raise FileExistsError(directory)
    version = data["hda_version"]
    filename = names.make_hda_filename(name, version)
    node_path = data["node_old_path"].rsplit("/", 1)[0] + "/" + name
    moves = [(old_file, old_directory / filename), (old_directory, directory)]
    thumb_directory = None
    thumb_filename = data.get("thumbnail_filename")
    old_thumb_directory = data.get("thumbnail_dirpath")
    if old_thumb_directory is not None:
        thumb_directory = relocated_path(
            old_thumb_directory, ((old_directory, directory),)
        )
        if (
            thumb_filename
            and old_thumb_directory.is_relative_to(old_directory)
            and (old_thumb_directory / thumb_filename).is_file()
        ):
            new_filename = names.make_thumbnail_filename(name, version)
            moves.append(
                (thumb_directory / thumb_filename, thumb_directory / new_filename)
            )
            thumb_filename = new_filename
    video_directory = None
    video_filename = None
    old_video_directory = data.get("video_dirpath")
    if old_video_directory is not None:
        video_directory = relocated_path(
            old_video_directory, ((old_directory, directory),)
        )
        video_filename = data.get("video_filename")
        if (
            rename_video
            and video_filename
            and old_video_directory.is_relative_to(old_directory)
            and (old_video_directory / video_filename).is_file()
        ):
            new_filename = names.make_video_filename(name, version)
            moves.append(
                (video_directory / video_filename, video_directory / new_filename)
            )
            video_filename = new_filename
    return RenamePlan(
        data["hda_id"],
        name,
        version,
        directory,
        filename,
        node_path,
        thumb_directory,
        thumb_filename,
        video_directory,
        video_filename,
        tuple((source, target) for source, target in moves if source != target),
    )


def rename_asset(
    repository: RenameRepository,
    plan: RenamePlan,
    *,
    operations: OperationFactory = durable_operation,
) -> tuple[int, int]:
    with operations(repository.db_filepath.parent, repository) as journal:
        for source, target in plan.moves:
            journal.move(source, target)
        asset_rows, history_rows = repository.apply_rename(plan)
        if asset_rows <= 0:
            raise RuntimeError("Asset rename did not update the database")
        return asset_rows, history_rows
