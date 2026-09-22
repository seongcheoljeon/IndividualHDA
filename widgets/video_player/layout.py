"""Code-built VideoPlayer layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QCoreApplication,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
)
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from libs.ui_icons import Icon
from widgets.layout_helpers import make_font, size_policy
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

from . import video_player_icons_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Form__video_player", text)


class VideoPlayerLayout:
    def build_ui(self, window: QWidget) -> None:
        self._configure_window(window)
        self._build_viewport(window)
        self._build_playlist(window)
        self._build_progress_and_volume(window)
        self._build_playback_controls(window)
        self._build_time_display(window)

    def _configure_window(self, window: QWidget) -> None:
        if not window.objectName():
            window.setObjectName("Form__video_player")
        window.resize(964, 593)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/video_player_main/icons/viewport_logo_trans.png"))
        window.setWindowTitle(_translate("iHDA Video Player"))

    def _build_viewport(self, window: QWidget) -> None:
        self.verticalLayout__video_player = QVBoxLayout(window)
        self.verticalLayout__video_player.setSpacing(0)
        self.verticalLayout__video_player.setObjectName("verticalLayout__video_player")
        self.verticalLayout__video_player.setContentsMargins(0, 0, 0, 0)
        self.splitter__vertical = QSplitter(window)
        self.splitter__vertical.setObjectName("splitter__vertical")
        self.splitter__vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__vertical.setHandleWidth(3)
        self.splitter__horizontal = QSplitter(self.splitter__vertical)
        self.splitter__horizontal.setObjectName("splitter__horizontal")
        self.splitter__horizontal.setOrientation(Qt.Orientation.Horizontal)
        self.splitter__horizontal.setHandleWidth(3)
        self.widget__video_viewport = QWidget(self.splitter__horizontal)
        self.widget__video_viewport.setObjectName("widget__video_viewport")
        self.horizontalLayout__viewport = QHBoxLayout(self.widget__video_viewport)
        self.horizontalLayout__viewport.setSpacing(1)
        self.horizontalLayout__viewport.setObjectName("horizontalLayout__viewport")
        self.horizontalLayout__viewport.setContentsMargins(0, 0, 0, 0)
        self.splitter__horizontal.addWidget(self.widget__video_viewport)

    def _build_playlist(self, window: QWidget) -> None:
        self.widget__playlist = QWidget(self.splitter__horizontal)
        self.widget__playlist.setObjectName("widget__playlist")
        self.verticalLayout__playlist = QVBoxLayout(self.widget__playlist)
        self.verticalLayout__playlist.setSpacing(1)
        self.verticalLayout__playlist.setObjectName("verticalLayout__playlist")
        self.verticalLayout__playlist.setContentsMargins(0, 0, 0, 3)
        self.listWidget__playlist = QListWidget(self.widget__playlist)
        self.listWidget__playlist.setObjectName("listWidget__playlist")
        self.listWidget__playlist.setFont(make_font(point_size=11))
        self.listWidget__playlist.setFrameShape(QFrame.Shape.NoFrame)
        self.verticalLayout__playlist.addWidget(self.listWidget__playlist)
        self.horizontalLayout__playlist_actions = QHBoxLayout()
        self.horizontalLayout__playlist_actions.setSpacing(1)
        self.horizontalLayout__playlist_actions.setObjectName(
            "horizontalLayout__playlist_actions"
        )
        self.horizontalLayout__playlist_actions.setContentsMargins(3, -1, 3, -1)
        self.pushButton__add_playlist = QPushButton(self.widget__playlist)
        self.pushButton__add_playlist.setObjectName("pushButton__add_playlist")
        self.pushButton__add_playlist.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__add_playlist.setIcon(
            QIcon(":/video_player_main/icons/ic_playlist_add_white.png")
        )
        self.pushButton__add_playlist.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__add_playlist.setFlat(True)
        self.pushButton__add_playlist.setToolTip(_translate("Add Video To Playlist"))
        self.pushButton__add_playlist.setStatusTip(_translate("Add video to playlist."))
        self.pushButton__add_playlist.setText("")
        self.horizontalLayout__playlist_actions.addWidget(self.pushButton__add_playlist)
        self.spacer__playlist_actions = QSpacerItem(
            40, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__playlist_actions.addItem(self.spacer__playlist_actions)
        self.pushButton__del_playlist = QPushButton(self.widget__playlist)
        self.pushButton__del_playlist.setObjectName("pushButton__del_playlist")
        self.pushButton__del_playlist.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__del_playlist.setIcon(QIcon(Icon.VIDEO_IC_DELETE_FOREVER_WHITE))
        self.pushButton__del_playlist.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__del_playlist.setFlat(True)
        self.pushButton__del_playlist.setToolTip(
            _translate("Delete Video From Playlist")
        )
        self.pushButton__del_playlist.setStatusTip(
            _translate("Remove selected video from playlist")
        )
        self.pushButton__del_playlist.setText("")
        self.horizontalLayout__playlist_actions.addWidget(self.pushButton__del_playlist)
        self.verticalLayout__playlist.addLayout(self.horizontalLayout__playlist_actions)
        self.splitter__horizontal.addWidget(self.widget__playlist)
        self.splitter__vertical.addWidget(self.splitter__horizontal)

    def _build_progress_and_volume(self, window: QWidget) -> None:
        self.widget__playback_controls = QWidget(self.splitter__vertical)
        self.widget__playback_controls.setObjectName("widget__playback_controls")
        self.verticalLayout__playback_controls = QVBoxLayout(
            self.widget__playback_controls
        )
        self.verticalLayout__playback_controls.setSpacing(3)
        self.verticalLayout__playback_controls.setObjectName(
            "verticalLayout__playback_controls"
        )
        self.verticalLayout__playback_controls.setContentsMargins(3, 0, 3, 3)
        self.horizontalLayout__progress_and_volume = QHBoxLayout()
        self.horizontalLayout__progress_and_volume.setSpacing(1)
        self.horizontalLayout__progress_and_volume.setObjectName(
            "horizontalLayout__progress_and_volume"
        )
        self.horizontalLayout__progress_and_volume.setContentsMargins(3, 3, 3, 1)
        self.horizontalSlider__progress = QSlider(self.widget__playback_controls)
        self.horizontalSlider__progress.setObjectName("horizontalSlider__progress")
        self.horizontalSlider__progress.setOrientation(Qt.Orientation.Horizontal)
        self.horizontalLayout__progress_and_volume.addWidget(
            self.horizontalSlider__progress
        )
        self.spacer__progress_and_volume = QSpacerItem(
            10, 10, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__progress_and_volume.addItem(
            self.spacer__progress_and_volume
        )
        self.horizontalLayout__volume = QHBoxLayout()
        self.horizontalLayout__volume.setSpacing(5)
        self.horizontalLayout__volume.setObjectName("horizontalLayout__volume")
        self.pushButton__volume = QPushButton(self.widget__playback_controls)
        self.pushButton__volume.setObjectName("pushButton__volume")
        self.pushButton__volume.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__volume.setIcon(
            QIcon(":/video_player_main/icons/ic_volume_up_white.png")
        )
        self.pushButton__volume.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.pushButton__volume.setCheckable(True)
        self.pushButton__volume.setFlat(True)
        self.pushButton__volume.setToolTip(_translate("Volume"))
        self.pushButton__volume.setStatusTip(
            _translate("It is a toggle button that can mute the sound.")
        )
        self.pushButton__volume.setText("")
        self.horizontalLayout__volume.addWidget(self.pushButton__volume)
        self.horizontalSlider__volume = QSlider(self.widget__playback_controls)
        self.horizontalSlider__volume.setObjectName("horizontalSlider__volume")
        self.horizontalSlider__volume.setSizePolicy(
            size_policy(
                self.horizontalSlider__volume,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.horizontalSlider__volume.setMaximum(100)
        self.horizontalSlider__volume.setValue(30)
        self.horizontalSlider__volume.setOrientation(Qt.Orientation.Horizontal)
        self.horizontalSlider__volume.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.horizontalSlider__volume.setTickInterval(10)
        self.horizontalSlider__volume.setToolTip(_translate("Volume"))
        self.horizontalSlider__volume.setStatusTip(_translate("Adjust the volume."))
        self.horizontalLayout__volume.addWidget(self.horizontalSlider__volume)
        self.horizontalLayout__progress_and_volume.addLayout(
            self.horizontalLayout__volume
        )
        self.verticalLayout__playback_controls.addLayout(
            self.horizontalLayout__progress_and_volume
        )

    def _build_playback_controls(self, window: QWidget) -> None:
        self.horizontalLayout__playback_footer = QHBoxLayout()
        self.horizontalLayout__playback_footer.setSpacing(3)
        self.horizontalLayout__playback_footer.setObjectName(
            "horizontalLayout__playback_footer"
        )
        self.spacer__playback_footer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__playback_footer.addItem(self.spacer__playback_footer)
        self.horizontalLayout__playback_actions = QHBoxLayout()
        self.horizontalLayout__playback_actions.setObjectName(
            "horizontalLayout__playback_actions"
        )
        self.horizontalLayout__transport = QHBoxLayout()
        self.horizontalLayout__transport.setSpacing(20)
        self.horizontalLayout__transport.setObjectName("horizontalLayout__transport")
        self.pushButton__play = QPushButton(self.widget__playback_controls)
        self.pushButton__play.setObjectName("pushButton__play")
        self.pushButton__play.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__play.setIcon(
            QIcon(":/video_player_main/icons/ic_play_arrow_white.png")
        )
        self.pushButton__play.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.pushButton__play.setFlat(True)
        self.pushButton__play.setToolTip(_translate("Play"))
        self.pushButton__play.setStatusTip(_translate("Play the video."))
        self.pushButton__play.setText("")
        self.horizontalLayout__transport.addWidget(self.pushButton__play)
        self.pushButton__stop = QPushButton(self.widget__playback_controls)
        self.pushButton__stop.setObjectName("pushButton__stop")
        self.pushButton__stop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__stop.setIcon(QIcon(Icon.VIDEO_IC_STOP_WHITE))
        self.pushButton__stop.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.pushButton__stop.setFlat(True)
        self.pushButton__stop.setToolTip(_translate("Stop"))
        self.pushButton__stop.setStatusTip(_translate("Stop playing the video."))
        self.pushButton__stop.setText("")
        self.horizontalLayout__transport.addWidget(self.pushButton__stop)
        self.pushButton__previous_video = QPushButton(self.widget__playback_controls)
        self.pushButton__previous_video.setObjectName("pushButton__previous_video")
        self.pushButton__previous_video.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__previous_video.setIcon(
            QIcon(":/video_player_main/icons/ic_skip_previous_white.png")
        )
        self.pushButton__previous_video.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__previous_video.setFlat(True)
        self.pushButton__previous_video.setToolTip(_translate("Previous Video"))
        self.pushButton__previous_video.setStatusTip(
            _translate("Play the previous video in the playlist.")
        )
        self.pushButton__previous_video.setText("")
        self.horizontalLayout__transport.addWidget(self.pushButton__previous_video)
        self.pushButton__next_video = QPushButton(self.widget__playback_controls)
        self.pushButton__next_video.setObjectName("pushButton__next_video")
        self.pushButton__next_video.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__next_video.setIcon(
            QIcon(":/video_player_main/icons/ic_skip_next_white.png")
        )
        self.pushButton__next_video.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__next_video.setFlat(True)
        self.pushButton__next_video.setToolTip(_translate("Next Video"))
        self.pushButton__next_video.setStatusTip(
            _translate("Play the next video in the playlist.")
        )
        self.pushButton__next_video.setText("")
        self.horizontalLayout__transport.addWidget(self.pushButton__next_video)
        self.pushButton__playback_mode = QPushButton(self.widget__playback_controls)
        self.pushButton__playback_mode.setObjectName("pushButton__playback_mode")
        self.pushButton__playback_mode.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__playback_mode.setIcon(
            QIcon(":/video_player_main/icons/ic_repeat_one_white.png")
        )
        self.pushButton__playback_mode.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__playback_mode.setChecked(False)
        self.pushButton__playback_mode.setFlat(True)
        self.pushButton__playback_mode.setToolTip(_translate("Playback Mode"))
        self.pushButton__playback_mode.setStatusTip(
            _translate("Set the playback mode.")
        )
        self.pushButton__playback_mode.setText("")
        self.horizontalLayout__transport.addWidget(self.pushButton__playback_mode)
        self.line__transport_separator = QFrame(self.widget__playback_controls)
        self.line__transport_separator.setObjectName("line__transport_separator")
        self.line__transport_separator.setFrameShape(QFrame.Shape.VLine)
        self.line__transport_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout__transport.addWidget(self.line__transport_separator)
        self.pushButton__full_screen = QPushButton(self.widget__playback_controls)
        self.pushButton__full_screen.setObjectName("pushButton__full_screen")
        self.pushButton__full_screen.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__full_screen.setIcon(
            QIcon(":/video_player_main/icons/ic_zoom_out_map_white.png")
        )
        self.pushButton__full_screen.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__full_screen.setFlat(True)
        self.pushButton__full_screen.setToolTip(_translate("Full Screen (toggle, F)"))
        self.pushButton__full_screen.setStatusTip(
            _translate("You can view the video full-screen.")
        )
        self.pushButton__full_screen.setText("")
        self.horizontalLayout__transport.addWidget(self.pushButton__full_screen)
        self.line__speed_separator = QFrame(self.widget__playback_controls)
        self.line__speed_separator.setObjectName("line__speed_separator")
        self.line__speed_separator.setFrameShape(QFrame.Shape.VLine)
        self.line__speed_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.horizontalLayout__transport.addWidget(self.line__speed_separator)
        self.horizontalLayout__playback_actions.addLayout(
            self.horizontalLayout__transport
        )
        self.horizontalLayout__playback_speed = QHBoxLayout()
        self.horizontalLayout__playback_speed.setObjectName(
            "horizontalLayout__playback_speed"
        )
        self.doubleSpinBox__play_speed = QDoubleSpinBox(self.widget__playback_controls)
        self.doubleSpinBox__play_speed.setObjectName("doubleSpinBox__play_speed")
        self.doubleSpinBox__play_speed.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.doubleSpinBox__play_speed.setFrame(False)
        self.doubleSpinBox__play_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.doubleSpinBox__play_speed.setDecimals(1)
        self.doubleSpinBox__play_speed.setMinimum(0.1)
        self.doubleSpinBox__play_speed.setMaximum(10.0)
        self.doubleSpinBox__play_speed.setSingleStep(0.1)
        self.doubleSpinBox__play_speed.setValue(1.0)
        self.doubleSpinBox__play_speed.setToolTip(_translate("Play Speed"))
        self.doubleSpinBox__play_speed.setStatusTip(
            _translate("Adjust the video playback speed.")
        )
        self.doubleSpinBox__play_speed.setPrefix(_translate("x"))
        self.horizontalLayout__playback_speed.addWidget(self.doubleSpinBox__play_speed)
        self.spacer__playback_speed = QSpacerItem(
            18, 13, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__playback_speed.addItem(self.spacer__playback_speed)
        self.horizontalLayout__playback_actions.addLayout(
            self.horizontalLayout__playback_speed
        )
        self.horizontalLayout__playback_footer.addLayout(
            self.horizontalLayout__playback_actions
        )
        # The player is embedded in the panel, so its window title is never shown:
        # the current track and the playback status live in these labels.
        self.label__track = QLabel(self.widget__playback_controls)
        self.label__track.setObjectName("label__track")
        self.label__track.setToolTip(_translate("Current track"))
        self.horizontalLayout__playback_footer.addWidget(self.label__track)
        self.label__status = QLabel(self.widget__playback_controls)
        self.label__status.setObjectName("label__status")
        self.label__status.setToolTip(_translate("Playback status"))
        self.horizontalLayout__playback_footer.addWidget(self.label__status)
        self.spacer__playback_footer_end = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__playback_footer.addItem(self.spacer__playback_footer_end)

    def _build_time_display(self, window: QWidget) -> None:
        self.horizontalLayout__playback_time = QHBoxLayout()
        self.horizontalLayout__playback_time.setSpacing(1)
        self.horizontalLayout__playback_time.setObjectName(
            "horizontalLayout__playback_time"
        )
        self.label__current_time = QLabel(self.widget__playback_controls)
        self.label__current_time.setObjectName("label__current_time")
        self.label__current_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__current_time.setToolTip(_translate("Current time of the video"))
        self.label__current_time.setText(_translate("00:00:00"))
        self.horizontalLayout__playback_time.addWidget(self.label__current_time)
        self.label__sep = QLabel(self.widget__playback_controls)
        self.label__sep.setObjectName("label__sep")
        self.label__sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__sep.setText(_translate("/"))
        self.horizontalLayout__playback_time.addWidget(self.label__sep)
        self.label__total_time = QLabel(self.widget__playback_controls)
        self.label__total_time.setObjectName("label__total_time")
        self.label__total_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__total_time.setToolTip(_translate("Total time of the video"))
        self.label__total_time.setText(_translate("00:00:00"))
        self.horizontalLayout__playback_time.addWidget(self.label__total_time)
        self.horizontalLayout__playback_footer.addLayout(
            self.horizontalLayout__playback_time
        )
        self.verticalLayout__playback_controls.addLayout(
            self.horizontalLayout__playback_footer
        )
        self.splitter__vertical.addWidget(self.widget__playback_controls)
        self.verticalLayout__video_player.addWidget(self.splitter__vertical)
