from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


def test_panel_imports_without_multimedia_and_webengine() -> None:
    code = """
import sys
for name in ('PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
             'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'):
    sys.modules[name] = None  # forces ImportError for these modules
from PySide6 import QtWidgets
app = QtWidgets.QApplication([])
from widgets.video_player import make_video_player, UnavailableVideoPlayer
from widgets.web_view import make_web_view, UnavailableWebView
player = make_video_player(None, None)
assert isinstance(player, UnavailableVideoPlayer), type(player)
player.ffmpeg_dirpath = '/tmp/ffmpeg'
player.player_stop(); player.play_after_add_playlist([]); player.delete_playlist_item_by_filepath('x')
assert isinstance(make_web_view(None, None), UnavailableWebView)
import main  # must not import the optional modules at module level
print('OPTIONAL_MEDIA_OK')
"""
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OPTIONAL_MEDIA_OK" in result.stdout
