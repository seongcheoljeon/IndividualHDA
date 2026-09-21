from __future__ import annotations

import json

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 01:43:35
# modified date:
# description:
import logging
import pathlib
from collections.abc import Sequence
from typing import Any

from PySide6 import QtCore, QtGui, QtMultimedia, QtWidgets

from libs import dragdrop_overlay, ffmpeg_api, log_handler, paths
from libs.media_playlist import MediaPlaylist
from libs.process_job import ProcessJob
from libs.resource_policy import MediaPolicy
from libs.ui_icons import Icon
from widgets.video_player import video_ui_settings, video_widget
from widgets.video_player.layout import VideoPlayerLayout
from widgets.video_player.presenter import VideoPresenter


class VideoPlayer(QtWidgets.QWidget, VideoPlayerLayout):
    def __init__(
        self,
        ffmpeg_dirpath: pathlib.Path | None = None,
        parent: QtWidgets.QWidget | None = None,
        *,
        policy: MediaPolicy = MediaPolicy(),
    ) -> None:
        super().__init__(parent)
        self.build_ui(self)
        self.policy = policy
        self._presenter = VideoPresenter(self)
        self.setAcceptDrops(True)
        # media settgins
        self.__ffmpeg_dirpath = ffmpeg_dirpath
        self.__video_widget = video_widget.VideoWidget(parent=self)
        self.__video_widget.overlay.show()
        self.__video_widget.play_toggle_requested.connect(self.slot_play_toggle)
        self.horizontalLayout__viewport.addWidget(self.__video_widget)
        self.__player = QtMultimedia.QMediaPlayer(self)
        self.__player.setVideoOutput(self.__video_widget)
        self.__playlist = MediaPlaylist(self.__player, self)
        self.__audio = QtMultimedia.QAudioOutput(self)
        self.__player.setAudioOutput(self.__audio)
        self.__probe_jobs: dict[ProcessJob, pathlib.Path] = {}
        self.__probe_pending: list[pathlib.Path] = []
        self.__probe_closing = False
        self.__probe_cache: dict[pathlib.Path, Any] = {}
        self.__playlist.currentIndexChanged.connect(
            self.listWidget__playlist.setCurrentRow
        )
        #
        self.__ui_settings = video_ui_settings.VideoUISettings(window=self)
        self.__dragdrop_overlay = dragdrop_overlay.Overlay(text="", parent=self)
        self.__dragdrop_overlay.close()
        #
        self.__prev_volume = self.horizontalSlider__volume.value()
        self.__audio.setVolume(self.__prev_volume / 100.0)
        self.__playback_idx = 1
        self.__last_dirpath: pathlib.Path | None = None
        self.__org_title = self.windowTitle()
        self.__track_info = ""
        self.__status_info = ""
        # shortcut key
        self.__shortcut_play_tgl = QtGui.QShortcut(QtGui.QKeySequence("Space"), self)
        self.__shortcut_full_screen_tgl = QtGui.QShortcut(QtGui.QKeySequence("f"), self)
        #
        self.__video_filter_str = "Video files ({})".format(
            " ".join(self.__video_extensions)
        )
        self.__audio_filter_str = "Audio files ({})".format(
            " ".join(self.__audio_extensions)
        )
        self.__playlist_filter_str = "Playlist files (*.m3u *.m3u8 *.M3U *.M3U8)"
        self.__all_filter_str = "All files (*.*)"
        #
        self.listWidget__playlist.setCurrentRow(0)
        self.__playlist.setCurrentIndex(0)
        self.__connections()
        self.__init_set()

    def __init_set(self) -> None:
        self.doubleSpinBox__play_speed.setValue(1.0)
        self.listWidget__playlist.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.listWidget__playlist.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.__load_config()
        self.__set_playback_mode()
        self.__slot_update_btn(self.__player.playbackState())
        self.__valid_check()

    def __valid_check(self) -> None:
        if not self.__player.isAvailable():
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="There is no valid service for iHDA video player app",
            )
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="Please check the media service plugins are installed",
            )

    def __connections(self) -> None:
        self.pushButton__add_playlist.clicked.connect(
            lambda: self.__slot_select_video_file(
                filter_str=f"{self.__video_filter_str};; {self.__audio_filter_str};; {self.__playlist_filter_str};; {self.__all_filter_str}"
            )
        )
        self.pushButton__del_playlist.clicked.connect(self.__slot_delete_playlist)
        self.pushButton__playback_mode.clicked.connect(self.__slot_playback_mode)
        self.pushButton__volume.clicked.connect(self.__slot_volume_btn)
        self.pushButton__full_screen.clicked.connect(
            lambda: self.__video_widget.setFullScreen(True)
        )
        self.pushButton__play.clicked.connect(self.__slot_play_btn)
        self.pushButton__stop.clicked.connect(self.__slot_stop_btn)
        self.pushButton__previous_video.clicked.connect(
            lambda: self.__playlist.setCurrentIndex(self.__playlist.previousIndex())
        )
        self.pushButton__next_video.clicked.connect(
            lambda: self.__playlist.setCurrentIndex(self.__playlist.nextIndex())
        )
        self.listWidget__playlist.itemDoubleClicked.connect(
            self.__slot_playlist_doubleclicked
        )
        self.listWidget__playlist.customContextMenuRequested.connect(
            self.__build_context_playlist
        )
        self.__player.playbackStateChanged.connect(self.__slot_update_btn)
        self.__player.durationChanged.connect(self.__slot_update_duration)
        self.__player.positionChanged.connect(self.__slot_player_position)
        self.__player.metaDataChanged.connect(self.__slot_video_metadata)
        self.__player.mediaStatusChanged.connect(self.__slot_status_changed)
        self.__player.bufferProgressChanged.connect(self.__slot_buffering_progress)
        self.__player.errorOccurred.connect(self.__display_error_msg)
        self.horizontalSlider__volume.valueChanged.connect(self.__slot_volume_slider)
        self.horizontalSlider__progress.sliderMoved.connect(self.__seek)
        self.horizontalSlider__progress.valueChanged.connect(
            self.__slot_pos_value_changed
        )
        self.__shortcut_play_tgl.activated.connect(self.slot_play_toggle)
        self.__shortcut_full_screen_tgl.activated.connect(self.__full_screen_toggle)
        self.doubleSpinBox__play_speed.valueChanged.connect(self.__slot_playspeed)

    def __slot_pos_value_changed(self, val: Any) -> None:
        if val != (self.__player.position() / 1000):
            self.__player.setPosition(val * 1000)

    def __seek(self, seconds: Any) -> None:
        self.__player.setPosition(seconds * 1000)

    def __display_error_msg(self, *args: Any) -> None:
        # A decode or backend failure used to reach the log only as part of the
        # window title, at info level; it never read as an error.
        message = self.__player.errorString()
        self.__set_status_info(message)
        if message:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg=f"video playback failed: {message}"
            )

    def __handle_cursor(self, status: Any) -> None:
        if status in (
            QtMultimedia.QMediaPlayer.MediaStatus.LoadingMedia,
            QtMultimedia.QMediaPlayer.MediaStatus.BufferingMedia,
            QtMultimedia.QMediaPlayer.MediaStatus.StalledMedia,
        ):
            self.setCursor(QtCore.Qt.CursorShape.BusyCursor)
        else:
            self.unsetCursor()

    def __slot_status_changed(self, status: Any) -> None:
        self.__handle_cursor(status)
        if status == QtMultimedia.QMediaPlayer.MediaStatus.LoadingMedia:
            self.__set_status_info("Loading...")
        elif status == QtMultimedia.QMediaPlayer.MediaStatus.StalledMedia:
            self.__set_status_info("Media Stalled")
        elif status == QtMultimedia.QMediaPlayer.MediaStatus.EndOfMedia:
            QtWidgets.QApplication.alert(self)
        elif status == QtMultimedia.QMediaPlayer.MediaStatus.InvalidMedia:
            self.__display_error_msg(None)
        else:
            self.__set_status_info("")

    def __slot_buffering_progress(self, progress: int) -> None:
        self.__set_status_info(f"Buffering {progress}%")

    def __set_status_info(self, info: Any) -> None:
        self.__status_info = info
        if self.__status_info != "":
            ste_info = (
                f"{self.__org_title} | {self.__track_info} - {self.__status_info}"
            )
        else:
            ste_info = f"{self.__org_title} | {self.__track_info}"
        # Title only. Playback state changes several times a second, and the
        # window title already shows it; logging it flooded the panel.
        self.setWindowTitle(ste_info)

    def __set_track_info(self, info: Any) -> None:
        self.__track_info = info
        if self.__status_info != "":
            track_info = (
                f"{self.__org_title} | {self.__track_info} - {self.__status_info}"
            )
        else:
            track_info = f"{self.__org_title} | {self.__track_info}"
        self.setWindowTitle(track_info)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.__probe_closing = True
        self.__probe_pending.clear()
        for job in tuple(self.__probe_jobs):
            job.shutdown()
        self.__player.stop()
        self.__ui_settings.save_main_window_geometry()
        self.__ui_settings.save_splitter_status()
        self.__ui_settings.save_cfg_dict_to_file()
        self.__video_widget.overlay.close()
        self.__dragdrop_overlay.close()
        self.player_stop()
        event.accept()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.__dragdrop_overlay.resize(event.size())
        super().resizeEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self.__dragdrop_overlay.text = "Drop the video file over here"
            self.__dragdrop_overlay.show()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent) -> None:
        self.__dragdrop_overlay.close()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        self.__dragdrop_overlay.close()
        filepath_lst = []
        for url in event.mimeData().urls():
            video_filepath = url.toLocalFile()
            exts = ["mp4", "avi", "mkv", "mov", "mp3", "wav", "m3u"]
            video_fileinfo = QtCore.QFileInfo(video_filepath)
            if video_fileinfo.suffix().lower() not in exts:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'"{video_fileinfo.suffix().lower()}" extension is not supported',
                )
                continue
            if (
                pathlib.Path(video_fileinfo.absoluteFilePath())
                in self.get_all_playlist_path()
            ):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg=f'"{video_fileinfo.absoluteFilePath()}" already exists in the playlist',
                )
                continue
            filepath_lst.append(video_filepath)
        if len(filepath_lst):
            self.add_playlist(filepath_lst=filepath_lst)
            if (
                self.__player.playbackState()
                != QtMultimedia.QMediaPlayer.PlaybackState.PlayingState
            ):
                idx = self.__playlist.mediaCount() - len(filepath_lst)
                self.listWidget__playlist.setCurrentRow(idx)
                self.__playlist.setCurrentIndex(idx)
                self.__player.play()

    def __full_screen_toggle(self) -> None:
        is_full = self.__video_widget.isFullScreen()
        self.__video_widget.setFullScreen(not is_full)

    @property
    def ffmpeg_dirpath(self) -> pathlib.Path | None:
        return self.__ffmpeg_dirpath

    @ffmpeg_dirpath.setter
    def ffmpeg_dirpath(self, val: Any) -> None:
        self.__ffmpeg_dirpath = pathlib.Path(val) if val is not None else None

    def __slot_video_metadata(self) -> None:
        item = self.listWidget__playlist.currentItem()
        if item is not None:
            self.__probe(pathlib.Path(item.text()))

    def __probe(self, filepath: pathlib.Path) -> None:
        if filepath in self.__probe_cache:
            self.__apply_probe(filepath, self.__probe_cache[filepath])
            return
        if self.__probe_closing or filepath in self.__probe_pending:
            return
        if filepath in self.__probe_jobs.values():
            return
        if len(self.__probe_jobs) >= 2:
            self.__probe_pending.append(filepath)
            return
        try:
            command = [
                ffmpeg_api.FFmpegAPI.executable("ffprobe", self.ffmpeg_dirpath),
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(filepath),
            ]
        except FileNotFoundError:
            return
        job = ProcessJob(
            command, self, timeout_ms=self.policy.probe_timeout_seconds * 1000
        )
        self.__probe_jobs[job] = filepath

        def complete(code: Any, output: Any) -> None:
            self.__probe_jobs.pop(job, None)
            try:
                info = json.loads(output) if code == 0 else {}
                self.__probe_cache[filepath] = info
                self.__apply_probe(filepath, info)
            except (ValueError, TypeError):
                pass
            job.deleteLater()
            if self.__probe_pending and not self.__probe_closing:
                self.__probe(self.__probe_pending.pop(0))

        job.finished.connect(complete)
        job.start()

    def __apply_probe(self, filepath: pathlib.Path, info: Any) -> None:
        self._presenter.metadata(pathlib.Path(filepath), info)

    def show_track_metadata(
        self, filepath: pathlib.Path, title: str, is_video: bool
    ) -> None:
        icon = "ic_movie_white.png" if is_video else "ic_audiotrack_white.png"
        for index in range(self.listWidget__playlist.count()):
            item = self.listWidget__playlist.item(index)
            if pathlib.Path(item.text()) == filepath:
                item.setIcon(QtGui.QIcon(":/video_player_main/icons/" + icon))
        current = self.listWidget__playlist.currentItem()
        if current and pathlib.Path(current.text()) == filepath:
            self.__set_track_info(title)

    def __slot_update_duration(self, duration: int) -> None:
        self.horizontalSlider__progress.setMaximum(duration // 1000)
        if duration >= 0:
            self.label__total_time.setText(VideoPlayer.__msec2strftime(ms=duration))

    def __slot_player_position(self, progress: int) -> None:
        if progress >= 0:
            self.label__current_time.setText(VideoPlayer.__msec2strftime(ms=progress))
        if not self.horizontalSlider__progress.isSliderDown():
            self.horizontalSlider__progress.blockSignals(True)
            self.horizontalSlider__progress.setValue(progress // 1000)
            self.horizontalSlider__progress.blockSignals(False)

    def __slot_playspeed(self, speed: Any) -> None:
        self.__player.setPlaybackRate(speed)

    def __set_playback_mode(self) -> None:
        mode, icon = VideoPlayer.__get_playback_mode(self.playback_idx)
        self.__playlist.setPlaybackMode(mode)
        self.pushButton__playback_mode.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/video_player_main/icons/{icon}"))
        )

    def __build_context_playlist(self, point: Any) -> None:
        index = self.listWidget__playlist.indexAt(point)
        if not index.isValid():
            context_menu = QtWidgets.QMenu(self)
            open_context_menu = QtWidgets.QMenu("Open", self)
            open_context_menu.setIcon(
                QtGui.QIcon(
                    QtGui.QPixmap(":/video_player_main/icons/ic_donut_large_white.png")
                )
            )

            action_open_context_video = open_context_menu.addAction("Video")
            action_open_context_video.setIcon(
                QtGui.QIcon(
                    QtGui.QPixmap(":/video_player_main/icons/ic_movie_white.png")
                )
            )
            action_open_context_audio = open_context_menu.addAction("Audio")
            action_open_context_audio.setIcon(
                QtGui.QIcon(
                    QtGui.QPixmap(":/video_player_main/icons/ic_audiotrack_white.png")
                )
            )
            action_open_context_playlist = open_context_menu.addAction("Playlist")
            action_open_context_playlist.setIcon(
                QtGui.QIcon(
                    QtGui.QPixmap(
                        ":/video_player_main/icons/ic_playlist_play_white.png"
                    )
                )
            )

            context_menu.addMenu(open_context_menu)
            action = context_menu.exec(self.listWidget__playlist.mapToGlobal(point))
            if action == action_open_context_video:
                self.__slot_select_video_file(filter_str=self.__video_filter_str)
            if action == action_open_context_audio:
                self.__slot_select_video_file(filter_str=self.__audio_filter_str)
            if action == action_open_context_playlist:
                self.__slot_select_video_file(filter_str=self.__playlist_filter_str)
        else:
            list_idx = index.row()
            play_idx = self.__playlist.currentIndex()
            context_menu = QtWidgets.QMenu(self)

            play_menu_name = "Play"
            play_icon = "ic_play_arrow_white.png"
            if self.__is_playing() and (list_idx == play_idx):
                play_menu_name = "Pause"
                play_icon = "ic_pause_white.png"
            action_play = context_menu.addAction(play_menu_name)
            action_play.setIcon(
                QtGui.QIcon(QtGui.QPixmap(f":/video_player_main/icons/{play_icon}"))
            )
            action_stop = context_menu.addAction("Stop")
            action_stop.setIcon(QtGui.QIcon(QtGui.QPixmap(Icon.VIDEO_IC_STOP_WHITE)))
            if self.__is_playing() or self.__is_paused():
                action_stop.setEnabled(True)
            else:
                action_stop.setEnabled(False)
            context_menu.addSeparator()
            action_remove = context_menu.addAction("Remove")
            action_remove.setIcon(
                QtGui.QIcon(QtGui.QPixmap(Icon.VIDEO_IC_DELETE_FOREVER_WHITE))
            )

            action = context_menu.exec(self.listWidget__playlist.mapToGlobal(point))
            if action == action_play:
                if self.__is_playing() and (list_idx == play_idx):
                    self.__player.pause()
                elif self.__is_paused() and (list_idx == play_idx):
                    self.__player.play()
                else:
                    self.__playlist.setCurrentIndex(list_idx)
                    self.__player.play()
            if action == action_stop:
                self.__player.stop()
            if action == action_remove:
                self.__slot_delete_playlist()

    def player_stop(self) -> None:
        if self.__is_playing() or self.__is_paused():
            self.__player.stop()

    def __is_playing(self) -> bool:
        return (
            self.__player.playbackState()
            == QtMultimedia.QMediaPlayer.PlaybackState.PlayingState
        )

    def __is_paused(self) -> bool:
        return (
            self.__player.playbackState()
            == QtMultimedia.QMediaPlayer.PlaybackState.PausedState
        )

    def __is_stopped(self) -> bool:
        return (
            self.__player.playbackState()
            == QtMultimedia.QMediaPlayer.PlaybackState.StoppedState
        )

    def __slot_playlist_doubleclicked(self, index: QtWidgets.QListWidgetItem) -> None:
        row = self.listWidget__playlist.row(index)
        vpath = QtCore.QFileInfo(self.listWidget__playlist.item(row).text().strip())
        if not vpath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="file does not exists"
            )
            return
        self.__playlist.setCurrentIndex(row)
        self.__player.play()

    def add_playlist(self, filepath_lst: Sequence[Any] = ()) -> None:
        paths = []
        for filepath in filepath_lst:
            path = pathlib.Path(filepath)
            if path.suffix.lower() in (".m3u", ".m3u8") and path.is_file():
                for line in path.read_text(encoding="utf-8-sig").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        paths.append(line if "://" in line else str(path.parent / line))
            else:
                paths.append(str(filepath))
        existing = {
            self.listWidget__playlist.item(i).text()
            for i in range(self.listWidget__playlist.count())
        }
        for filepath in paths:
            if filepath in existing:
                continue
            url = (
                QtCore.QUrl(filepath)
                if "://" in filepath
                else QtCore.QUrl.fromLocalFile(str(pathlib.Path(filepath).absolute()))
            )
            self.__playlist.addMedia(url.toString())
            self.listWidget__playlist.addItem(filepath)
            self.listWidget__playlist.item(
                self.listWidget__playlist.count() - 1
            ).setToolTip(filepath)
            existing.add(filepath)
            self.__probe(pathlib.Path(filepath))

    def play_after_add_playlist(self, filepath_lst: Any = None) -> None:
        assert isinstance(filepath_lst[0], pathlib.Path)
        all_playlist_path = self.get_all_playlist_path()
        if filepath_lst[0] in all_playlist_path:
            idx = len(all_playlist_path)
            for position, filepath in enumerate(all_playlist_path):
                if filepath == filepath_lst[0]:
                    idx = position
                    break
        else:
            self.add_playlist(filepath_lst=[filepath_lst[0].as_posix()])
            idx = self.__playlist.mediaCount() - len(filepath_lst)
        self.listWidget__playlist.setCurrentRow(idx)
        self.__playlist.setCurrentIndex(idx)
        self.__player.play()

    def __load_config(self) -> None:
        if paths.Paths.json_video_filepath.exists():
            self.__ui_settings.load_main_window_geometry()
            self.__ui_settings.load_splitter_status()
            self.__ui_settings.load_cfg_dict_from_file()

    def __slot_select_video_file(self, filter_str: str = "") -> None:
        if self.last_dirpath is None:
            last_dpath = QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.StandardLocation.MoviesLocation
            )
        else:
            last_dpath = self.last_dirpath.as_posix()
        filepath_lst, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Open files", last_dpath, filter_str
        )
        if not len(filepath_lst):
            return
        self.last_dirpath = pathlib.Path(
            QtCore.QFileInfo(filepath_lst[0]).absoluteFilePath()
        ).parent
        all_playlist_path = self.get_all_playlist_path()
        for filepath in filepath_lst:
            fileinfo = QtCore.QFileInfo(filepath)
            if pathlib.Path(fileinfo.absoluteFilePath()) in all_playlist_path:
                continue
            self.add_playlist(filepath_lst=filepath_lst)

    def __slot_delete_playlist(self) -> None:
        item_lst = self.listWidget__playlist.selectedItems()
        if not item_lst:
            return
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setWindowTitle("Delete Video From Playlist")
        msgbox.setText(f"delete {len(item_lst)} selected video from playlist?")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
            return
        for item in item_lst:
            row = self.listWidget__playlist.row(item)
            self.__delete_playlist_item(row)

    def __delete_playlist_item(self, row: int) -> None:
        self.listWidget__playlist.takeItem(row)
        self.__playlist.removeMedia(row)

    # 전체 history, 단일 history삭제나 iHDA삭제 시 적절히 playlist 비워야한다.
    def delete_playlist_item_by_filepath(
        self, filepath: pathlib.Path | None = None
    ) -> None:
        assert isinstance(filepath, pathlib.Path)
        find_idx = self.__find_playlist_index_by_filepath(filepath=filepath)
        if find_idx < 0:
            return
        self.__delete_playlist_item(find_idx)

    def __find_playlist_index_by_filepath(
        self, filepath: pathlib.Path | None = None
    ) -> int:
        assert isinstance(filepath, pathlib.Path)
        all_playlist_path = self.get_all_playlist_path()
        if filepath not in all_playlist_path:
            return -1
        idx = 0
        for fpath in all_playlist_path:
            if filepath == fpath:
                break
            idx += 1
        return idx

    def __slot_playback_mode(self) -> None:
        self.playback_idx += 1
        self.__set_playback_mode()
        pbmode = [MediaPlaylist.Sequential, MediaPlaylist.Loop]
        self.pushButton__previous_video.setEnabled(
            self.__playlist.playbackMode() in pbmode
        )
        self.pushButton__next_video.setEnabled(self.__playlist.playbackMode() in pbmode)

    def slot_play_toggle(self) -> None:
        if self.__is_playing():
            self.__player.pause()
        else:
            self.__player.play()

    def __slot_play_btn(self) -> None:
        row = self.listWidget__playlist.currentRow()
        item = self.listWidget__playlist.item(row)
        if item is None:
            return
        vpath = QtCore.QFileInfo(item.text().strip())
        if not vpath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="file does not exists"
            )
            return
        if self.__is_playing():
            self.__player.pause()
        elif self.__is_paused():
            self.__player.play()
        else:
            self.__playlist.setCurrentIndex(row)
            self.__player.play()

    def __slot_stop_btn(self) -> None:
        self.__player.stop()

    def __slot_update_btn(self, state: QtMultimedia.QMediaPlayer.PlaybackState) -> None:
        self.__video_widget.overlay.close()
        media_cnt = self.__playlist.mediaCount()
        self.pushButton__play.setEnabled(media_cnt > 0)
        self.pushButton__stop.setEnabled(media_cnt > 0)
        self.pushButton__previous_video.setEnabled(media_cnt > 0)
        self.pushButton__next_video.setEnabled(media_cnt > 0)
        if media_cnt <= 0:
            return
        if state == QtMultimedia.QMediaPlayer.PlaybackState.PlayingState:
            self.__video_widget.overlay.close()
            icon = "ic_pause_white.png"
            self.pushButton__stop.setEnabled(True)
            self.pushButton__play.setToolTip("pause")
        elif state == QtMultimedia.QMediaPlayer.PlaybackState.PausedState:
            self.__video_widget.overlay.close()
            icon = "ic_play_arrow_white.png"
            self.pushButton__stop.setEnabled(True)
            self.pushButton__play.setToolTip("play")
        else:
            self.__video_widget.overlay.show()
            icon = "ic_play_arrow_white.png"
            self.pushButton__stop.setEnabled(False)
        pbmode = [MediaPlaylist.Sequential, MediaPlaylist.Loop]
        self.pushButton__previous_video.setEnabled(
            self.__playlist.playbackMode() in pbmode
        )
        self.pushButton__next_video.setEnabled(self.__playlist.playbackMode() in pbmode)
        self.pushButton__play.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/video_player_main/icons/{icon}"))
        )

    def __slot_volume_btn(self, *args: Any, **kwargs: Any) -> None:
        if self.pushButton__volume.isChecked():
            self.__prev_volume = self.horizontalSlider__volume.value()
            self.__slot_volume_slider(0)
            self.__audio.setMuted(True)
        else:
            self.__slot_volume_slider(self.__prev_volume)
            self.__audio.setMuted(False)

    def __slot_volume_slider(self, val: Any) -> None:
        if val == 0:
            icon = "ic_volume_off_white.png"
            self.pushButton__volume.setChecked(True)
        else:
            icon = "ic_volume_up_white.png"
            self.pushButton__volume.setChecked(False)
        self.pushButton__volume.setIcon(
            QtGui.QIcon(QtGui.QPixmap(f":/video_player_main/icons/{icon}"))
        )
        self.horizontalSlider__volume.setValue(val)
        self.__audio.setVolume(val / 100.0)

    @property
    def playback_idx(self) -> int:
        return self.__playback_idx

    @playback_idx.setter
    def playback_idx(self, val: Any) -> None:
        self.__playback_idx = val % 5

    def get_all_playlist_path(self) -> list[Any]:
        all_playlist = []
        for i in range(self.listWidget__playlist.count()):
            vpath = pathlib.Path(self.listWidget__playlist.item(i).text())
            all_playlist.append(vpath)
        return all_playlist

    @property
    def __video_extensions(self) -> list[Any]:
        ext_lst = [
            "mp4",
            "avi",
            "mpg",
            "mpeg",
            "mpe",
            "wmv",
            "asf",
            "asx",
            "flv",
            "rm",
            "mov",
            "mkv",
            "webm",
            "ts",
            "vob",
        ]
        ext_lst += [x.upper() for x in ext_lst]
        return [f"*.{x}" for x in ext_lst]

    @property
    def __audio_extensions(self) -> list[Any]:
        ext_lst = [
            "mp3",
            "wav",
            "ogg",
            "gsm",
            "flac",
            "au",
            "aiff",
            "vox",
            "wma",
            "aac",
            "dss",
            "mid",
        ]
        ext_lst += [x.upper() for x in ext_lst]
        return [f"*.{x}" for x in ext_lst]

    @property
    def last_dirpath(self) -> pathlib.Path | None:
        return self.__last_dirpath

    @last_dirpath.setter
    def last_dirpath(self, dirpath: pathlib.Path) -> None:
        if isinstance(dirpath, pathlib.Path):
            self.__last_dirpath = dirpath
        else:
            self.__last_dirpath = pathlib.Path(dirpath)

    @staticmethod
    def __get_playback_mode(index: int) -> list[Any]:
        playback_mode = {
            0: MediaPlaylist.CurrentItemOnce,
            1: MediaPlaylist.CurrentItemInLoop,
            2: MediaPlaylist.Sequential,
            3: MediaPlaylist.Loop,
            4: MediaPlaylist.Random,
        }
        playback_mode_icon = {
            0: "ic_repeat_one_white.png",
            1: "ic_repeat_white.png",
            2: "ic_playlist_play_white.png",
            3: "ic_playlist_repeat_white.png",
            4: "ic_shuffle_white.png",
        }
        return [playback_mode[index], playback_mode_icon[index]]

    @staticmethod
    def __msec2strftime(ms: int = 0) -> str:
        return ":".join([str(x).zfill(2) for x in VideoPlayer.__msec2time(ms=ms)])

    # video는 milliseconds 이다.
    @staticmethod
    def __msec2time(ms: int = 0) -> list[Any]:
        sec = ms // 1000
        h, m = divmod(sec, 3600)
        m, s = divmod(m, 60)
        return [h, m, s]

    # @staticmethod
    # def time2sec(hours=None, minutes=None, seconds=None):
    #     hsec = hours * 3600
    #     msec = minutes * 60
    #     sec = seconds
    #     return hsec + msec + sec
