"""Read-only detail formatting. Never modifies the selected model record."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from libs.asset_contracts import AssetData, HistoryData
from libs.keys import Key
from libs.scene_contracts import SceneRecord


@dataclass(frozen=True)
class DetailContent:
    rows: tuple[tuple[str, str], ...]
    thumbnail: Path | None
    copyable: dict[str, str]  # "Name" / "Path" / "Version" -> value, when known

    @property
    def text(self) -> str:
        return "\n".join(f"{key}: {value}" for key, value in self.rows)


def _first(values: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = values.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def copyable_values(values: dict[str, Any]) -> dict[str, str]:
    """The three things people paste elsewhere: the name, the file, the version."""
    result: dict[str, str] = {}
    name = _first(values, "hda_name", "org_hda_name", "node_name")
    version = _first(values, "hda_version", "version")
    path = _first(values, "hda_filepath")
    for directory, filename in (
        ("hda_dirpath", "hda_filename"),
        ("ihda_dirpath", "ihda_filename"),
    ):
        if not path and values.get(directory) and values.get(filename):
            path = str(Path(str(values[directory])) / str(values[filename]))
    if name:
        result["Name"] = name
    if path:
        result["Path"] = path
    if version:
        result["Version"] = version
    return result


class DetailView(Protocol):
    def show_content(self, content: DetailContent) -> None: ...


class DetailPresenter:
    def __init__(self, view: DetailView) -> None:
        self._view = view

    def show(
        self,
        data: AssetData | HistoryData | SceneRecord,
        *,
        history: bool = False,
        record: bool = False,
    ) -> None:
        values = asdict(data)
        if record:
            excluded = {
                Key.Record.record_id,
                Key.Record.hda_id,
                Key.Record.sf,
                Key.Record.ef,
                Key.Record.fps,
            }
            values["FRAME INFO"] = (
                f"[{values.get(Key.Record.sf)} - {values.get(Key.Record.ef)}], fps: {values.get(Key.Record.fps)}"
            )
            directory, filename = (
                values.get(Key.Record.thumb_dirpath),
                values.get(Key.Record.thumb_filename),
            )
        else:
            excluded = {
                Key.hda_icon,
                Key.History.icon,
                Key.hda_id,
                Key.History.hda_id,
                Key.History.hist_id,
                Key.hda_note,
            }
            directory = values.get(
                Key.History.thumb_dirpath if history else Key.thumbnail_dirpath
            )
            filename = values.get(
                Key.History.thumb_filename if history else Key.thumbnail_filename
            )
        content = DetailContent(
            tuple(
                (key.replace("_", " ").upper(), str(value))
                for key, value in sorted(values.items())
                if key not in excluded
            ),
            Path(directory) / filename if directory is not None and filename else None,
            copyable_values(values),
        )
        self._view.show_content(content)
