from __future__ import annotations
import pathlib

from typing import Any
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from PySide6 import QtCore, QtMultimedia
from libs.ffmpeg_api import FFmpegAPI
from libs.process_job import ProcessJob
from libs.background_job import BackgroundJob
from libs.media_playlist import MediaPlaylist
from libs.settings_store import save_json


def test_ffmpeg_arguments_preserve_unicode_spaces_quotes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.setattr(
        FFmpegAPI,
        "executable",
        lambda *args: str(tmp_path / "program files" / "ffmpeg"),
    )
    image = tmp_path / "시퀀스 'quote' %04d.jpg"
    output = tmp_path / "out file.mp4"
    args = FFmpegAPI.image_sequence_command(
        None, image, output, 1001, 12, 23.976, {"title": 'quote"; $HOME'}
    )
    assert args[args.index("-i") + 1] == str(image)
    assert args[args.index("-metadata") + 1] == 'title=quote"; $HOME'
    assert args[-1] == str(output)
    assert args[args.index("-framerate") + 1] == "23.976"


def test_failed_encode_preserves_previous_video(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    output = tmp_path / "old.mp4"
    output.write_bytes(b"previous video")
    monkeypatch.setattr(FFmpegAPI, "executable", lambda *args: "ffmpeg")

    def fail(command: list[str], **kwargs: Any) -> Any:
        Path(command[-1]).write_bytes(b"partial")
        return SimpleNamespace(returncode=1, stderr="encoder error")

    monkeypatch.setattr(subprocess, "run", fail)
    assert (
        FFmpegAPI.make_image_seq_to_video(
            None, tmp_path / "image%04d.jpg", output, 1, 3
        )
        == 1
    )
    assert output.read_bytes() == b"previous video"
    assert list(tmp_path.iterdir()) == [output]


def test_probe_parses_json_without_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FFmpegAPI, "executable", lambda *args: "ffprobe")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout='{"streams": [], "flag": true}'),
    )
    assert FFmpegAPI.video_info(video_filepath="test.mp4")["flag"] is True
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout='__import__("os")'),
    )
    assert FFmpegAPI.video_info(video_filepath="test.mp4") is None


def test_cancel_process_emits_once(app: Any) -> None:
    job = ProcessJob([sys.executable, "-c", "import time; time.sleep(30)"])
    results = []
    loop = QtCore.QEventLoop()
    job.finished.connect(lambda *result: (results.append(result), loop.quit()))
    QtCore.QTimer.singleShot(50, job.cancel)
    timeout = QtCore.QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(5000)
    job.start()
    loop.exec()
    job.shutdown()
    assert len(results) == 1 and results[0][0] != 0


def test_background_result_on_ui_thread(app: Any) -> None:
    loop = QtCore.QEventLoop()
    results = []

    class Receiver(QtCore.QObject):
        @QtCore.Slot(object, object)
        def receive(self, value: Any, error: Any) -> None:
            results.append((value, error, QtCore.QThread.currentThread()))
            loop.quit()

    receiver = Receiver()
    job = BackgroundJob(lambda: QtCore.QThread.currentThread())
    job.result.connect(receiver.receive)
    timeout = QtCore.QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(5000)
    job.start()
    loop.exec()
    job.wait(5000)
    assert results and results[0][0] != app.thread()
    assert results[0][1] is None and results[0][2] == app.thread()


class FakePlayer(QtCore.QObject):
    mediaStatusChanged = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.state = QtMultimedia.QMediaPlayer.StoppedState
        self.source = QtCore.QUrl()
        self.position = 0

    def playbackState(self) -> Any:
        return self.state

    def setSource(self, source: Any) -> None:
        self.source = source

    def setPosition(self, value: Any) -> None:
        self.position = value

    def play(self) -> None:
        self.state = QtMultimedia.QMediaPlayer.PlayingState

    def stop(self) -> None:
        self.state = QtMultimedia.QMediaPlayer.StoppedState


def test_playlist_modes_and_removal(app: Any) -> None:
    player = FakePlayer()
    playlist = MediaPlaylist(player)
    for path in ("first.mp4", "second.mp4"):
        playlist.addMedia(QtCore.QUrl.fromLocalFile(path))
    playlist.setCurrentIndex(0)
    playlist.setPlaybackMode(MediaPlaylist.Sequential)
    player.play()
    player.mediaStatusChanged.emit(QtMultimedia.QMediaPlayer.EndOfMedia)
    assert playlist.currentIndex() == 1
    player.mediaStatusChanged.emit(QtMultimedia.QMediaPlayer.EndOfMedia)
    assert player.state == QtMultimedia.QMediaPlayer.StoppedState
    playlist.setPlaybackMode(MediaPlaylist.Loop)
    player.mediaStatusChanged.emit(QtMultimedia.QMediaPlayer.EndOfMedia)
    assert playlist.currentIndex() == 0
    playlist.setPlaybackMode(MediaPlaylist.CurrentItemInLoop)
    player.position = 100
    player.mediaStatusChanged.emit(QtMultimedia.QMediaPlayer.EndOfMedia)
    assert playlist.currentIndex() == 0 and player.position == 0
    playlist.removeMedia(0)
    assert playlist.mediaCount() == 1 and playlist.currentIndex() == 0
    playlist.removeMedia(0)
    assert playlist.currentIndex() == -1 and player.source.isEmpty()


def test_settings_write_failure_keeps_old_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "settings.json"
    save_json(path, {"name": "한글"})
    with pytest.raises(TypeError):
        save_json(path, {"invalid": object()})
    assert json.loads(path.read_text(encoding="utf-8")) == {"name": "한글"}
    assert list(tmp_path.iterdir()) == [path]


def test_rename_failure_preserves_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from libs.ihda_system import IHDASystem

    source, target = tmp_path / "new", tmp_path / "old"
    source.write_bytes(b"new")
    target.write_bytes(b"old")

    def fail(*args: Any) -> None:
        raise PermissionError("in use")

    monkeypatch.setattr(Path, "replace", fail)
    assert not IHDASystem.rename_file(source, target)
    assert source.read_bytes() == b"new" and target.read_bytes() == b"old"
