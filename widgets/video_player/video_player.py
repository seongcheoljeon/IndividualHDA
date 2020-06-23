# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 01:43:35
# modified date:    
# description:      

import logging
from imp import reload

import pathlib2
from PySide2 import QtWidgets, QtGui, QtCore, QtMultimedia

import public
from widgets.video_player import video_player_ui, video_widget, video_ui_settings
from libs import ffmpeg_api, dragdrop_overlay, log_handler

reload(public)
reload(video_player_ui)
reload(video_widget)
reload(video_ui_settings)
reload(ffmpeg_api)
reload(dragdrop_overlay)
reload(log_handler)


class VideoPlayer(QtWidgets.QWidget, video_player_ui.Ui_Form__video_player):
    def __init__(self, ffmpeg_dirpath=None, parent=None):
        super(VideoPlayer, self).__init__(parent)
        self.setupUi(self)
        self.setAcceptDrops(True)
        # media settgins
        self.__ffmpeg_dirpath = ffmpeg_dirpath
        self.__video_widget = video_widget.VideoWidget(parent=self)
        self.__video_widget.overlay.show()
        self.horizontalLayout__viewport.addWidget(self.__video_widget)
        self.__player = QtMultimedia.QMediaPlayer()
        self.__player.setVideoOutput(self.__video_widget)
        self.__playlist = QtMultimedia.QMediaPlaylist()
        self.__player.setPlaylist(self.__playlist)
        #
        self.__ui_settings = video_ui_settings.VideoUISettings(window=self)
        self.__dragdrop_overlay = dragdrop_overlay.Overlay(text='', parent=self)
        self.__dragdrop_overlay.close()
        #
        self.__prev_volume = self.horizontalSlider__volume.value()
        self.__player.setVolume(self.__prev_volume)
        self.__playback_idx = 1
        self.__last_dirpath = None
        self.__org_title = self.windowTitle()
        self.__track_info = ''
        self.__status_info = ''
        # shortcut key
        self.__shortcut_play_tgl = QtWidgets.QShortcut(QtGui.QKeySequence('Space'), self)
        self.__shortcut_full_screen_tgl = QtWidgets.QShortcut(QtGui.QKeySequence('f'), self)
        #
        self.__video_filter_str = 'Video files ({0})'.format(' '.join(self.__video_extensions))
        self.__audio_filter_str = 'Audio files ({0})'.format(' '.join(self.__audio_extensions))
        self.__playlist_filter_str = 'Playlist files (*.m3u *.m3u8 *.M3U *.M3U8)'
        self.__all_filter_str = 'All files (*.*)'
        #
        self.listWidget__playlist.setCurrentRow(0)
        self.__playlist.setCurrentIndex(0)
        self.__connections()
        self.__init_set()

    def __init_set(self):
        self.doubleSpinBox__play_speed.setValue(1.0)
        self.listWidget__playlist.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget__playlist.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.__load_config()
        self.__set_playback_mode()
        self.__slot_update_btn(self.__player.state())
        self.__valid_check()

    def __valid_check(self):
        if not self.__player.isAvailable():
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='There is no valid service for iHDA video player app')
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='Please check the media service plugins are installed')

    def __connections(self):
        self.pushButton__add_playlist.clicked.connect(
            lambda: self.__slot_select_video_file(
                filter_str='{0};; {1};; {2};; {3}'.format(
                    self.__video_filter_str, self.__audio_filter_str,
                    self.__playlist_filter_str, self.__all_filter_str)))
        self.pushButton__del_playlist.clicked.connect(self.__slot_delete_playlist)
        self.pushButton__playback_mode.clicked.connect(self.__slot_playback_mode)
        self.pushButton__volume.clicked.connect(self.__slot_volume_btn)
        self.pushButton__full_screen.clicked.connect(lambda: self.__video_widget.setFullScreen(True))
        self.pushButton__play.clicked.connect(self.__slot_play_btn)
        self.pushButton__stop.clicked.connect(self.__slot_stop_btn)
        self.pushButton__previous_video.clicked.connect(
            lambda: self.__playlist.setCurrentIndex(self.__playlist.previousIndex()))
        self.pushButton__next_video.clicked.connect(
            lambda: self.__playlist.setCurrentIndex(self.__playlist.nextIndex()))
        self.listWidget__playlist.itemDoubleClicked.connect(self.__slot_playlist_doubleclicked)
        self.listWidget__playlist.customContextMenuRequested.connect(self.__build_context_playlist)
        self.__player.stateChanged.connect(self.__slot_update_btn)
        self.__player.durationChanged.connect(self.__slot_update_duration)
        self.__player.positionChanged.connect(self.__slot_player_position)
        self.__player.metaDataChanged.connect(self.__slot_video_metadata)
        self.__player.mediaStatusChanged.connect(self.__slot_status_changed)
        self.__player.bufferStatusChanged.connect(self.__slot_buffering_progress)
        self.__player.error.connect(self.__display_error_msg)
        self.horizontalSlider__volume.valueChanged.connect(self.__slot_volume_slider)
        self.horizontalSlider__progress.sliderMoved.connect(self.__seek)
        self.horizontalSlider__progress.valueChanged.connect(self.__slot_pos_value_changed)
        self.__shortcut_play_tgl.activated.connect(self.slot_play_toggle)
        self.doubleSpinBox__play_speed.valueChanged.connect(self.__slot_playspeed)

    def __slot_pos_value_changed(self, val):
        if val != (self.__player.position() / 1000):
            self.__player.setPosition(val * 1000)

    def __seek(self, seconds):
        self.__player.setPosition(seconds * 1000)

    def __display_error_msg(self, *args):
        self.__set_status_info(self.__player.errorString())

    def __handle_cursor(self, status):
        if status in (
                QtMultimedia.QMediaPlayer.LoadingMedia,
                QtMultimedia.QMediaPlayer.BufferingMedia,
                QtMultimedia.QMediaPlayer.StalledMedia):
            self.setCursor(QtCore.Qt.BusyCursor)
        else:
            self.unsetCursor()

    def __slot_status_changed(self, status):
        self.__handle_cursor(status)
        if status == QtMultimedia.QMediaPlayer.LoadingMedia:
            self.__set_status_info('Loading...')
        elif status == QtMultimedia.QMediaPlayer.StalledMedia:
            self.__set_status_info('Media Stalled')
        elif status == QtMultimedia.QMediaPlayer.EndOfMedia:
            QtWidgets.QApplication.alert(self)
        elif status == QtMultimedia.QMediaPlayer.InvalidMedia:
            self.__display_error_msg(None)
        else:
            self.__set_status_info('')

    def __slot_buffering_progress(self, progress):
        self.__set_status_info('Buffering {0}%'.format(progress))

    def __set_status_info(self, info):
        self.__status_info = info
        if self.__status_info != '':
            ste_info = '{0} | {1} - {2}'.format(self.__org_title, self.__track_info, self.__status_info)
        else:
            ste_info = '{0} | {1}'.format(self.__org_title, self.__track_info)
        self.setWindowTitle(ste_info)
        log_handler.LogHandler.log_msg(method=logging.info, msg=ste_info)

    def __set_track_info(self, info):
        self.__track_info = info
        if self.__status_info != '':
            track_info = '{0} | {1} - {2}'.format(self.__org_title, self.__track_info, self.__status_info)
        else:
            track_info = '{0} | {1}'.format(self.__org_title, self.__track_info)
        self.setWindowTitle(track_info)
        log_handler.LogHandler.log_msg(method=logging.info, msg=track_info)

    def closeEvent(self, event):
        self.__ui_settings.save_main_window_geometry()
        self.__ui_settings.save_splitter_status()
        self.__ui_settings.save_cfg_dict_to_file()
        self.__video_widget.overlay.close()
        self.__dragdrop_overlay.close()
        self.player_stop()
        event.accept()

    def resizeEvent(self, event):
        self.__dragdrop_overlay.resize(event.size())
        super(VideoPlayer, self).resizeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.__dragdrop_overlay.text = 'Drop the video file over here'
            self.__dragdrop_overlay.show()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.__dragdrop_overlay.close()

    def dropEvent(self, event):
        self.__dragdrop_overlay.close()
        filepath_lst = list()
        for url in event.mimeData().urls():
            video_filepath = url.toLocalFile().encode('utf8')
            exts = ['mp4', 'avi', 'mkv', 'mov', 'mp3', 'wav', 'm3u']
            video_fileinfo = QtCore.QFileInfo(video_filepath)
            if video_fileinfo.suffix().lower() not in exts:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='"{0}" extension is not supported'.format(video_fileinfo.suffix().lower()))
                continue
            if pathlib2.Path(video_fileinfo.absoluteFilePath().encode('utf8')) in self.get_all_playlist_path():
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='"{0}" already exists in the playlist'.format(
                        video_fileinfo.absoluteFilePath().encode('utf8')))
                continue
            filepath_lst.append(video_filepath)
        if len(filepath_lst):
            self.add_playlist(filepath_lst=filepath_lst)
            if self.__player.state() != QtMultimedia.QMediaPlayer.PlayingState:
                idx = self.__playlist.mediaCount() - len(filepath_lst)
                self.listWidget__playlist.setCurrentRow(idx)
                self.__playlist.setCurrentIndex(idx)
                self.__player.play()

    def __full_screen_toggle(self):
        is_full = self.__video_widget.isFullScreen()
        self.__video_widget.setFullScreen(not is_full)

    @staticmethod
    def __get_metadata(ffmpeg_dirpath=None, video_filepath=None):
        ffmpeg = ffmpeg_api.FFmpegAPI()
        video_info = ffmpeg.video_info(
            ffmpeg_dirpath=ffmpeg_dirpath, video_filepath=pathlib2.Path(video_filepath))
        if video_info is None:
            return
        stream_info = video_info.get('streams')
        format_info = video_info.get('format')
        if stream_info is not None:
            stream_info = stream_info[0]
        if format_info is not None:
            tags = format_info.get('tags')
            if tags is not None:
                artist = tags.get('artist')
                title = tags.get('title')
                year = tags.get('year')
                track_info = title
                if artist is not None:
                    track_info = '{0} - {1}'.format(artist, track_info)
                if year is not None:
                    track_info = '{0} [{1}]'.format(track_info, year)
                return track_info
        return None

    @property
    def ffmpeg_dirpath(self):
        return self.__ffmpeg_dirpath

    @ffmpeg_dirpath.setter
    def ffmpeg_dirpath(self, val):
        assert isinstance(val, pathlib2.Path)
        self.__ffmpeg_dirpath = val

    def __slot_video_metadata(self):
        if self.__player.isMetaDataAvailable():
            curt_item = self.listWidget__playlist.currentItem()
            if curt_item is None:
                return
            track_info = VideoPlayer.__get_metadata(
                ffmpeg_dirpath=self.ffmpeg_dirpath, video_filepath=curt_item.text().decode('utf8'))
            if track_info is not None:
                self.__set_track_info(track_info)

    @staticmethod
    def __get_codec_type(ffmpeg_dirpath=None, filepath=None):
        ffmpeg = ffmpeg_api.FFmpegAPI()
        info = ffmpeg.video_info(
            ffmpeg_dirpath=ffmpeg_dirpath, video_filepath=pathlib2.Path(filepath.encode('utf8')))
        if info is None:
            return None
        stream_info = info.get('streams')
        if stream_info is None:
            return None
        stream_info = stream_info[0]
        codec_type = stream_info.get('codec_type')
        if codec_type is None:
            return None
        return codec_type

    def __slot_update_duration(self, duration):
        self.horizontalSlider__progress.setMaximum(duration / 1000)
        if duration >= 0:
            self.label__total_time.setText(VideoPlayer.__msec2strftime(ms=duration))

    def __slot_player_position(self, progress):
        if progress >= 0:
            self.label__current_time.setText(VideoPlayer.__msec2strftime(ms=progress))
        if not self.horizontalSlider__progress.isSliderDown():
            self.horizontalSlider__progress.blockSignals(True)
            self.horizontalSlider__progress.setValue(progress / 1000)
            self.horizontalSlider__progress.blockSignals(False)

    def __slot_playspeed(self, speed):
        self.__player.setPlaybackRate(speed)

    def __set_playback_mode(self):
        mode, icon = VideoPlayer.__get_playback_mode(self.playback_idx)
        self.__playlist.setPlaybackMode(mode)
        self.pushButton__playback_mode.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/{0}'.format(icon))))

    def __build_context_playlist(self, point):
        index = self.listWidget__playlist.indexAt(point)
        if not index.isValid():
            context_menu = QtWidgets.QMenu(self)
            open_context_menu = QtWidgets.QMenu('Open', self)
            open_context_menu.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_donut_large_white.png')))

            action_open_context_video = open_context_menu.addAction('Video')
            action_open_context_video.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_movie_white.png')))
            action_open_context_audio = open_context_menu.addAction('Audio')
            action_open_context_audio.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_audiotrack_white.png')))
            action_open_context_playlist = open_context_menu.addAction('Playlist')
            action_open_context_playlist.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_playlist_play_white.png')))

            context_menu.addMenu(open_context_menu)
            action = context_menu.exec_(self.listWidget__playlist.mapToGlobal(point))
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

            play_menu_name = 'Play'
            play_icon = 'ic_play_arrow_white.png'
            if self.__is_playing() and (list_idx == play_idx):
                play_menu_name = 'Pause'
                play_icon = 'ic_pause_white.png'
            action_play = context_menu.addAction(play_menu_name)
            action_play.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/{0}'.format(play_icon))))
            action_stop = context_menu.addAction('Stop')
            action_stop.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_stop_white.png')))
            if self.__is_playing() or self.__is_paused():
                action_stop.setEnabled(True)
            else:
                action_stop.setEnabled(False)
            context_menu.addSeparator()
            action_remove = context_menu.addAction('Remove')
            action_remove.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_delete_forever_white.png')))

            action = context_menu.exec_(self.listWidget__playlist.mapToGlobal(point))
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

    def player_stop(self):
        if self.__is_playing() or self.__is_paused():
            self.__player.stop()

    def __is_playing(self):
        return self.__player.state() == QtMultimedia.QMediaPlayer.PlayingState

    def __is_paused(self):
        return self.__player.state() == QtMultimedia.QMediaPlayer.PausedState

    def __is_stopped(self):
        return self.__player.state() == QtMultimedia.QMediaPlayer.StoppedState

    def __slot_playlist_doubleclicked(self, index):
        row = index.listWidget().currentRow()
        vpath = QtCore.QFileInfo(self.listWidget__playlist.item(row).text().strip().encode('utf8'))
        if not vpath.exists():
            log_handler.LogHandler.log_msg(method=logging.warning, msg='file does not exists')
            return
        self.__playlist.setCurrentIndex(row)
        self.__player.play()

    def add_playlist(self, filepath_lst=()):
        for filepath in filepath_lst:
            fileinfo = QtCore.QFileInfo(filepath)
            if fileinfo.exists():
                url = QtCore.QUrl.fromLocalFile(fileinfo.absoluteFilePath())
                if fileinfo.suffix().lower() in ['m3u', 'm3u8']:
                    self.__playlist.load(url)
                else:
                    self.__playlist.addMedia(QtMultimedia.QMediaContent(url))
            else:
                url = QtCore.QUrl(filepath)
                if url.isValid():
                    self.__playlist.addMedia(QtMultimedia.QMediaContent(url))
            self.listWidget__playlist.addItem(filepath)
        for i in range(self.listWidget__playlist.count()):
            item = self.listWidget__playlist.item(i)
            filepath = item.text().encode('utf8')
            item.setToolTip(filepath)
            codec_type = VideoPlayer.__get_codec_type(ffmpeg_dirpath=self.ffmpeg_dirpath, filepath=filepath)
            if codec_type is not None:
                if codec_type == 'video':
                    item.setIcon(QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_movie_white.png')))
                elif codec_type == 'audio':
                    item.setIcon(QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/ic_audiotrack_white.png')))
                else:
                    item.setIcon(QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/unknown.png')))
            else:
                item.setIcon(QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/unknown.png')))
                item.setBackgroundColor(QtGui.QColor(255, 0, 0, 127))

    def play_after_add_playlist(self, filepath_lst=None):
        assert isinstance(filepath_lst[0], pathlib2.Path)
        all_playlist_path = self.get_all_playlist_path()
        if filepath_lst[0] in all_playlist_path:
            idx = 0
            for filepath in all_playlist_path:
                if filepath == filepath_lst[0]:
                    break
                idx += 1
        else:
            self.add_playlist(filepath_lst=[filepath_lst[0].as_posix()])
            idx = self.__playlist.mediaCount() - len(filepath_lst)
        self.listWidget__playlist.setCurrentRow(idx)
        self.__playlist.setCurrentIndex(idx)
        self.__player.play()

    def __load_config(self):
        if public.Paths.json_video_filepath.exists():
            self.__ui_settings.load_main_window_geometry()
            self.__ui_settings.load_splitter_status()
            self.__ui_settings.load_cfg_dict_from_file()

    def __slot_select_video_file(self, filter_str=''):
        if self.last_dirpath is None:
            last_dpath = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.MoviesLocation)
        else:
            last_dpath = self.last_dirpath.as_posix()
        filepath_lst, _ = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open files', last_dpath, filter_str)
        if not len(filepath_lst):
            return
        self.last_dirpath = pathlib2.Path(QtCore.QFileInfo(filepath_lst[0]).absoluteFilePath().encode('utf8')).parent
        all_playlist_path = self.get_all_playlist_path()
        for filepath in filepath_lst:
            fileinfo = QtCore.QFileInfo(filepath)
            if pathlib2.Path(fileinfo.absoluteFilePath().encode('utf8')) in all_playlist_path:
                continue
            self.add_playlist(filepath_lst=filepath_lst)

    def __slot_delete_playlist(self):
        item_lst = self.listWidget__playlist.selectedItems()
        if not item_lst:
            return
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setWindowTitle('Delete Video From Playlist')
        msgbox.setText('delete {0} selected video from playlist?'.format(len(item_lst)))
        msgbox.setIcon(QtWidgets.QMessageBox.Warning)
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Cancel:
            return
        for item in item_lst:
            row = self.listWidget__playlist.row(item)
            self.__delete_playlist_item(row)

    def __delete_playlist_item(self, row):
        self.listWidget__playlist.takeItem(row)
        self.__playlist.removeMedia(row)

    # 전체 history, 단일 history삭제나 iHDA삭제 시 적절히 playlist 비워야한다.
    def delete_playlist_item_by_filepath(self, filepath=None):
        assert isinstance(filepath, pathlib2.Path)
        find_idx = self.__find_playlist_index_by_filepath(filepath=filepath)
        if find_idx < 0:
            return
        self.__delete_playlist_item(find_idx)

    def __find_playlist_index_by_filepath(self, filepath=None):
        assert isinstance(filepath, pathlib2.Path)
        all_playlist_path = self.get_all_playlist_path()
        if filepath not in all_playlist_path:
            return -1
        idx = 0
        for fpath in all_playlist_path:
            if filepath == fpath:
                break
            idx += 1
        return idx

    def __slot_playback_mode(self):
        self.playback_idx += 1
        self.__set_playback_mode()
        pbmode = [QtMultimedia.QMediaPlaylist.Sequential, QtMultimedia.QMediaPlaylist.Loop]
        self.pushButton__previous_video.setEnabled(self.__playlist.playbackMode() in pbmode)
        self.pushButton__next_video.setEnabled(self.__playlist.playbackMode() in pbmode)

    def slot_play_toggle(self):
        if self.__is_playing():
            self.__player.pause()
        else:
            self.__player.play()

    def __slot_play_btn(self):
        row = self.listWidget__playlist.currentRow()
        item = self.listWidget__playlist.item(row)
        if item is None:
            return
        vpath = QtCore.QFileInfo(item.text().strip().encode('utf8'))
        if not vpath.exists():
            log_handler.LogHandler.log_msg(method=logging.warning, msg='file does not exists')
            return
        if self.__is_playing():
            self.__player.pause()
        elif self.__is_paused():
            self.__player.play()
        else:
            self.__playlist.setCurrentIndex(row)
            self.__player.play()

    def __slot_stop_btn(self):
        self.__player.stop()

    def __slot_update_btn(self, state):
        self.__video_widget.overlay.close()
        media_cnt = self.__playlist.mediaCount()
        self.pushButton__play.setEnabled(media_cnt > 0)
        self.pushButton__stop.setEnabled(media_cnt > 0)
        self.pushButton__previous_video.setEnabled(media_cnt > 0)
        self.pushButton__next_video.setEnabled(media_cnt > 0)
        if media_cnt <= 0:
            return
        if state == QtMultimedia.QMediaPlayer.PlayingState:
            self.__video_widget.overlay.close()
            icon = 'ic_pause_white.png'
            self.pushButton__stop.setEnabled(True)
            self.pushButton__play.setToolTip('pause')
        elif state == QtMultimedia.QMediaPlayer.PausedState:
            self.__video_widget.overlay.close()
            icon = 'ic_play_arrow_white.png'
            self.pushButton__stop.setEnabled(True)
            self.pushButton__play.setToolTip('play')
        else:
            self.__video_widget.overlay.show()
            icon = 'ic_play_arrow_white.png'
            self.pushButton__stop.setEnabled(False)
        pbmode = [QtMultimedia.QMediaPlaylist.Sequential, QtMultimedia.QMediaPlaylist.Loop]
        self.pushButton__previous_video.setEnabled(self.__playlist.playbackMode() in pbmode)
        self.pushButton__next_video.setEnabled(self.__playlist.playbackMode() in pbmode)
        self.pushButton__play.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/{0}'.format(icon))))

    def __slot_volume_btn(self, *args, **kwargs):
        if self.pushButton__volume.isChecked():
            self.__prev_volume = self.horizontalSlider__volume.value()
            self.__slot_volume_slider(0)
            self.__player.setMuted(True)
        else:
            self.__slot_volume_slider(self.__prev_volume)
            self.__player.setMuted(False)

    def __slot_volume_slider(self, val):
        if val == 0:
            icon = 'ic_volume_off_white.png'
            self.pushButton__volume.setChecked(True)
        else:
            icon = 'ic_volume_up_white.png'
            self.pushButton__volume.setChecked(False)
        self.pushButton__volume.setIcon(QtGui.QIcon(QtGui.QPixmap(':/video_player_main/icons/{0}'.format(icon))))
        self.horizontalSlider__volume.setValue(val)
        self.__player.setVolume(val)

    @property
    def playback_idx(self):
        return self.__playback_idx

    @playback_idx.setter
    def playback_idx(self, val):
        self.__playback_idx = (val % 5)

    def get_all_playlist_path(self):
        all_playlist = list()
        for i in range(self.listWidget__playlist.count()):
            vpath = pathlib2.Path(self.listWidget__playlist.item(i).text().encode('utf8'))
            all_playlist.append(vpath)
        return all_playlist

    @property
    def __video_extensions(self):
        ext_lst = [
            'mp4', 'avi', 'mpg', 'mpeg', 'mpe', 'wmv', 'asf', 'asx', 'flv', 'rm', 'mov', 'mkv',
            'webm', 'ts', 'vob']
        ext_lst += map(lambda x: x.upper(), ext_lst)
        return map(lambda x: '*.{0}'.format(x), ext_lst)

    @property
    def __audio_extensions(self):
        ext_lst = ['mp3', 'wav', 'ogg', 'gsm', 'flac', 'au', 'aiff', 'vox', 'wma', 'aac', 'dss', 'mid']
        ext_lst += map(lambda x: x.upper(), ext_lst)
        return map(lambda x: '*.{0}'.format(x), ext_lst)

    @property
    def last_dirpath(self):
        return self.__last_dirpath

    @last_dirpath.setter
    def last_dirpath(self, dirpath):
        if isinstance(dirpath, pathlib2.Path):
            self.__last_dirpath = dirpath
        else:
            self.__last_dirpath = pathlib2.Path(dirpath)

    @staticmethod
    def __get_playback_mode(index):
        playback_mode = {
            0: QtMultimedia.QMediaPlaylist.CurrentItemOnce,
            1: QtMultimedia.QMediaPlaylist.CurrentItemInLoop,
            2: QtMultimedia.QMediaPlaylist.Sequential,
            3: QtMultimedia.QMediaPlaylist.Loop,
            4: QtMultimedia.QMediaPlaylist.Random
        }
        playback_mode_icon = {
            0: 'ic_repeat_one_white.png',
            1: 'ic_repeat_white.png',
            2: 'ic_playlist_play_white.png',
            3: 'ic_playlist_repeat_white.png',
            4: 'ic_shuffle_white.png'
        }
        return [playback_mode[index], playback_mode_icon[index]]

    @staticmethod
    def __msec2strftime(ms=None):
        return ':'.join(map(lambda x: str(x).zfill(2), VideoPlayer.__msec2time(ms=ms)))

    # video는 milliseconds 이다.
    @staticmethod
    def __msec2time(ms=None):
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

