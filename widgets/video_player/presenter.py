"""Playback metadata formatting independent of multimedia/Qt objects."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol


class VideoView(Protocol):
    def show_track_metadata(
        self, filepath: Path, title: str, is_video: bool
    ) -> None: ...


class VideoPresenter:
    def __init__(self, view: VideoView) -> None:
        self._view = view

    def metadata(self, filepath: Path, info: Mapping[str, Any]) -> None:
        streams = info.get("streams") or []
        is_video = any(stream.get("codec_type") == "video" for stream in streams)
        tags = (info.get("format") or {}).get("tags") or {}
        self._view.show_track_metadata(
            Path(filepath), str(tags.get("title") or Path(filepath).name), is_video
        )
