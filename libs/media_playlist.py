"""Qt 6 playlist controller preserving the five existing playback modes."""

from __future__ import annotations
from PySide6 import QtMultimedia

from typing import Any
from PySide6 import QtCore
from enum import IntEnum
import random


class MediaPlaylist(QtCore.QObject):
    class PlaybackMode(IntEnum):
        CurrentItemOnce = 0
        CurrentItemInLoop = 1
        Sequential = 2
        Loop = 3
        Random = 4

    CurrentItemOnce, CurrentItemInLoop, Sequential, Loop, Random = PlaybackMode
    currentIndexChanged = QtCore.Signal(int)

    def __init__(
        self, player: QtMultimedia.QMediaPlayer, parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.player = player
        self.urls = []
        self.index = -1
        self.mode = self.Sequential
        player.mediaStatusChanged.connect(self._status_changed)

    def addMedia(self, url: str) -> None:
        self.urls.append(QtCore.QUrl(url))

    def mediaCount(self) -> int:
        return len(self.urls)

    def currentIndex(self) -> int:
        return self.index

    def setCurrentIndex(self, index: int) -> None:
        index = index if 0 <= index < len(self.urls) else -1
        if index == self.index:
            return
        playing = self.player.playbackState() == QtMultimedia.QMediaPlayer.PlayingState
        self.index = index
        self.player.setSource(self.urls[index] if index >= 0 else QtCore.QUrl())
        self.currentIndexChanged.emit(index)
        if playing and index >= 0:
            self.player.play()

    def playbackMode(self) -> int:
        return self.mode

    def setPlaybackMode(self, mode: int) -> None:
        self.mode = self.PlaybackMode(mode)

    def _step(self, step: int) -> int:
        count = len(self.urls)
        if not count:
            return -1
        if self.mode == self.Random:
            return random.randrange(count)
        if self.mode == self.CurrentItemInLoop:
            return self.index
        if self.mode == self.CurrentItemOnce:
            return -1
        candidate = self.index + step
        if self.mode == self.Loop:
            return candidate % count
        return candidate if 0 <= candidate < count else -1

    def nextIndex(self) -> int:
        return self._step(1)

    def previousIndex(self) -> int:
        return self._step(-1)

    def removeMedia(self, index: int) -> bool:
        if not 0 <= index < len(self.urls):
            return False
        del self.urls[index]
        if index == self.index:
            self.index = -1
            self.setCurrentIndex(min(index, len(self.urls) - 1))
            if not self.urls:
                self.player.setSource(QtCore.QUrl())
                self.currentIndexChanged.emit(-1)
        elif index < self.index:
            self.index -= 1
            self.currentIndexChanged.emit(self.index)
        return True

    def _status_changed(self, status: Any) -> None:
        if status != QtMultimedia.QMediaPlayer.EndOfMedia:
            return
        next_index = self.nextIndex()
        if next_index < 0:
            self.player.stop()
        elif next_index == self.index:
            self.player.setPosition(0)
            self.player.play()
        else:
            self.setCurrentIndex(next_index)
            self.player.play()
