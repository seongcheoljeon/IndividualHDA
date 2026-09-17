"""Read-only detail formatting. Never modifies the selected model record."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from libs.asset_contracts import AssetData, HistoryData
from libs.keys import Key
from libs.scene_contracts import SceneRecord


@dataclass(frozen=True)
class DetailContent:
    text: str
    thumbnail: Path | None


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
            "\n".join(
                f"{key.replace('_', ' ').upper()}: {value}"
                for key, value in sorted(values.items())
                if key not in excluded
            ),
            Path(directory) / filename if directory is not None and filename else None,
        )
        self._view.show_content(content)
