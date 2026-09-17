"""Asset rename planning and execution, independent of widgets and SQL layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from libs.asset_contracts import AssetData
from libs.contracts import OperationFactory, TransactionalRepository
from libs.path_updates import PathMove, PathMoves, relocated_path


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


@dataclass(frozen=True, slots=True, kw_only=True)
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
    moves: PathMoves


@dataclass(frozen=True, slots=True, kw_only=True)
class RenameCounts:
    assets: int
    histories: int


class RenameRepository(TransactionalRepository, Protocol):
    def apply_rename(self, plan: RenamePlan) -> RenameCounts: ...


def build_rename_plan(
    data: AssetData, name: str, names: AssetNames, *, rename_video: bool
) -> RenamePlan:
    if not name or name in (".", "..") or any(char in name for char in "/\\"):
        raise ValueError("Asset name must be a single directory name")
    old_directory, old_filename = data.hda_dirpath, data.hda_filename
    if old_directory is None or not old_filename:
        raise ValueError("Asset file location is missing")
    old_file = old_directory / old_filename
    if not old_file.is_file():
        raise FileNotFoundError(old_file)
    directory = old_directory.with_name(name)
    if directory != old_directory and directory.exists():
        raise FileExistsError(directory)
    version = data.hda_version
    filename = names.make_hda_filename(name, version)
    node_path = data.node_old_path.rsplit("/", 1)[0] + "/" + name
    moves = [
        PathMove(source=old_file, target=old_directory / filename),
        PathMove(source=old_directory, target=directory),
    ]
    thumb_directory = None
    thumb_filename = data.thumbnail_filename
    old_thumb_directory = data.thumbnail_dirpath
    if old_thumb_directory is not None:
        thumb_directory = relocated_path(
            old_thumb_directory, (PathMove(source=old_directory, target=directory),)
        )
        if (
            thumb_filename
            and old_thumb_directory.is_relative_to(old_directory)
            and (old_thumb_directory / thumb_filename).is_file()
        ):
            new_filename = names.make_thumbnail_filename(name, version)
            moves.append(
                PathMove(
                    source=thumb_directory / thumb_filename,
                    target=thumb_directory / new_filename,
                )
            )
            thumb_filename = new_filename
    video_directory = None
    video_filename = None
    old_video_directory = data.video_dirpath
    if old_video_directory is not None:
        video_directory = relocated_path(
            old_video_directory, (PathMove(source=old_directory, target=directory),)
        )
        video_filename = data.video_filename
        if (
            rename_video
            and video_filename
            and old_video_directory.is_relative_to(old_directory)
            and (old_video_directory / video_filename).is_file()
        ):
            new_filename = names.make_video_filename(name, version)
            moves.append(
                PathMove(
                    source=video_directory / video_filename,
                    target=video_directory / new_filename,
                )
            )
            video_filename = new_filename
    return RenamePlan(
        asset_id=data.hda_id,
        name=name,
        version=version,
        directory=directory,
        filename=filename,
        node_path=node_path,
        thumbnail_directory=thumb_directory,
        thumbnail_filename=thumb_filename,
        video_directory=video_directory,
        video_filename=video_filename,
        moves=tuple(move for move in moves if move.source != move.target),
    )


def rename_asset(
    repository: RenameRepository,
    plan: RenamePlan,
    *,
    operations: OperationFactory,
) -> RenameCounts:
    with operations(repository.db_filepath.parent, repository) as journal:
        for move in plan.moves:
            journal.move(move.source, move.target)
        counts = repository.apply_rename(plan)
        if counts.assets <= 0:
            raise RuntimeError("Asset rename did not update the database")
        return counts
