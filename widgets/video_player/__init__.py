"""Video player factory: falls back to a placeholder when QtMultimedia is missing."""

from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from widgets.video_player.video_player import VideoPlayer

from PySide6 import QtCore, QtWidgets

from libs.resource_policy import MediaPolicy

_MESSAGE = (
    "Video player unavailable: PySide6.QtMultimedia is missing in this Houdini build"
)


class UnavailableVideoPlayer(QtWidgets.QWidget):
    """Null object with the panel-facing surface of VideoPlayer."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ffmpeg_dirpath: pathlib.Path | None = None
        label = QtWidgets.QLabel(_MESSAGE, self)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label)

    @property
    def ffmpeg_dirpath(self) -> pathlib.Path | None:
        return self._ffmpeg_dirpath

    @ffmpeg_dirpath.setter
    def ffmpeg_dirpath(self, val: Any) -> None:
        self._ffmpeg_dirpath = pathlib.Path(val) if val else None

    def player_stop(self) -> None:
        return None

    def play_after_add_playlist(self, filepath_lst: Any = None) -> None:
        return None

    def delete_playlist_item_by_filepath(self, filepath: Any = None) -> None:
        return None


def make_video_player(
    ffmpeg_dirpath: pathlib.Path | None,
    parent: QtWidgets.QWidget | None,
    *,
    policy: MediaPolicy = MediaPolicy(),
) -> VideoPlayer | UnavailableVideoPlayer:
    try:
        from widgets.video_player.video_player import VideoPlayer
    except ImportError as error:
        logging.getLogger(__name__).warning("%s (%s)", _MESSAGE, error)
        return UnavailableVideoPlayer(parent)
    return VideoPlayer(ffmpeg_dirpath=ffmpeg_dirpath, parent=parent, policy=policy)
