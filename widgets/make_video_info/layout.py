"""Code-built VideoInfo layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QCoreApplication,
    QLocale,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
)

from widgets.layout_helpers import make_font

from . import icons_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Dialog__makevideoinfo", text)


class VideoInfoLayout:
    def build_ui(self, window: QDialog) -> None:
        self._configure_window(window)
        self._build_header(window)
        self._build_sharing_options(window)
        self._build_video_settings(window)
        self._build_flipbook_options(window)
        self._build_dialog_buttons(window)

    def _configure_window(self, window: QDialog) -> None:
        if not window.objectName():
            window.setObjectName("Dialog__makevideoinfo")
        window.resize(642, 564)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/main/icons/viewport_logo_trans.png"))
        window.setWindowTitle(_translate("Make Video Information"))

    def _build_header(self, window: QDialog) -> None:
        self.verticalLayout__video_info = QVBoxLayout(window)
        self.verticalLayout__video_info.setSpacing(12)
        self.verticalLayout__video_info.setObjectName("verticalLayout__video_info")
        self.verticalLayout__video_info.setContentsMargins(3, 3, 3, 3)
        self.horizontalLayout__video_header = QHBoxLayout()
        self.horizontalLayout__video_header.setObjectName(
            "horizontalLayout__video_header"
        )
        self.label__company = QLabel(window)
        self.label__company.setObjectName("label__company")
        self.label__company.setMaximumSize(QSize(30, 30))
        self.label__company.setPixmap(QPixmap(":/main/icons/viewport_logo_trans.png"))
        self.label__company.setScaledContents(True)
        self.label__company.setText("")
        self.horizontalLayout__video_header.addWidget(self.label__company)
        self.label__title = QLabel(window)
        self.label__title.setObjectName("label__title")
        self.label__title.setFont(make_font(point_size=14))
        self.label__title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__title.setText(_translate("Make Video Information"))
        self.horizontalLayout__video_header.addWidget(self.label__title)
        self.verticalLayout__video_info.addLayout(self.horizontalLayout__video_header)

    def _build_sharing_options(self, window: QDialog) -> None:
        self.groupBox__share = QGroupBox(window)
        self.groupBox__share.setObjectName("groupBox__share")
        self.groupBox__share.setTitle(_translate("Share"))
        self.horizontalLayout__sharing = QHBoxLayout(self.groupBox__share)
        self.horizontalLayout__sharing.setObjectName("horizontalLayout__sharing")
        self.checkBox__youtube = QCheckBox(self.groupBox__share)
        self.checkBox__youtube.setObjectName("checkBox__youtube")
        self.checkBox__youtube.setIcon(QIcon(":/main/icons/youtube.png"))
        self.checkBox__youtube.setIconSize(QSize(24, 24))
        self.checkBox__youtube.setToolTip(_translate("Share Youtube"))
        self.checkBox__youtube.setText("")
        self.horizontalLayout__sharing.addWidget(self.checkBox__youtube)
        self.checkBox__vimeo = QCheckBox(self.groupBox__share)
        self.checkBox__vimeo.setObjectName("checkBox__vimeo")
        self.checkBox__vimeo.setIcon(QIcon(":/main/icons/vimeo.png"))
        self.checkBox__vimeo.setIconSize(QSize(24, 24))
        self.checkBox__vimeo.setToolTip(_translate("Share Vimeo"))
        self.checkBox__vimeo.setText("")
        self.horizontalLayout__sharing.addWidget(self.checkBox__vimeo)
        self.spacer__sharing = QSpacerItem(
            144, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__sharing.addItem(self.spacer__sharing)
        self.horizontalLayout__share_resolution_summary = QHBoxLayout()
        self.horizontalLayout__share_resolution_summary.setObjectName(
            "horizontalLayout__share_resolution_summary"
        )
        self.horizontalLayout__share_resolution = QHBoxLayout()
        self.horizontalLayout__share_resolution.setObjectName(
            "horizontalLayout__share_resolution"
        )
        self.label__resolution_share = QLabel(self.groupBox__share)
        self.label__resolution_share.setObjectName("label__resolution_share")
        self.label__resolution_share.setText(_translate("Share Resolution"))
        self.horizontalLayout__share_resolution.addWidget(self.label__resolution_share)
        self.comboBox__resolution_share = QComboBox(self.groupBox__share)
        self.comboBox__resolution_share.setObjectName("comboBox__resolution_share")
        self.comboBox__resolution_share.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.comboBox__resolution_share.setFrame(False)
        self.comboBox__resolution_share.setToolTip(
            _translate("Set the resolution of SNS upload video.")
        )
        self.horizontalLayout__share_resolution.addWidget(
            self.comboBox__resolution_share
        )
        self.horizontalLayout__share_resolution_summary.addLayout(
            self.horizontalLayout__share_resolution
        )
        self.label__confirm_resolution_share = QLabel(self.groupBox__share)
        self.label__confirm_resolution_share.setObjectName(
            "label__confirm_resolution_share"
        )
        self.label__confirm_resolution_share.setText("")
        self.horizontalLayout__share_resolution_summary.addWidget(
            self.label__confirm_resolution_share
        )
        self.horizontalLayout__sharing.addLayout(
            self.horizontalLayout__share_resolution_summary
        )
        self.verticalLayout__video_info.addWidget(self.groupBox__share)

    def _build_video_settings(self, window: QDialog) -> None:
        self.groupBox__video = QGroupBox(window)
        self.groupBox__video.setObjectName("groupBox__video")
        self.groupBox__video.setTitle(_translate("Video"))
        self.verticalLayout__video_settings = QVBoxLayout(self.groupBox__video)
        self.verticalLayout__video_settings.setObjectName(
            "verticalLayout__video_settings"
        )
        self.horizontalLayout__frame_range = QHBoxLayout()
        self.horizontalLayout__frame_range.setObjectName(
            "horizontalLayout__frame_range"
        )
        self.horizontalLayout__start_frame = QHBoxLayout()
        self.horizontalLayout__start_frame.setObjectName(
            "horizontalLayout__start_frame"
        )
        self.label__sf = QLabel(self.groupBox__video)
        self.label__sf.setObjectName("label__sf")
        self.label__sf.setText(_translate("Start Frame"))
        self.horizontalLayout__start_frame.addWidget(self.label__sf)
        self.spinBox__sf = QSpinBox(self.groupBox__video)
        self.spinBox__sf.setObjectName("spinBox__sf")
        self.spinBox__sf.setFrame(False)
        self.spinBox__sf.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.spinBox__sf.setMaximum(9999999)
        self.spinBox__sf.setValue(1001)
        self.spinBox__sf.setToolTip(_translate("Set the frame range of the video."))
        self.horizontalLayout__start_frame.addWidget(self.spinBox__sf)
        self.horizontalLayout__frame_range.addLayout(self.horizontalLayout__start_frame)
        self.spacer__frame_range = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__frame_range.addItem(self.spacer__frame_range)
        self.horizontalLayout__end_frame = QHBoxLayout()
        self.horizontalLayout__end_frame.setObjectName("horizontalLayout__end_frame")
        self.label__ef = QLabel(self.groupBox__video)
        self.label__ef.setObjectName("label__ef")
        self.label__ef.setText(_translate("End Frame"))
        self.horizontalLayout__end_frame.addWidget(self.label__ef)
        self.spinBox__ef = QSpinBox(self.groupBox__video)
        self.spinBox__ef.setObjectName("spinBox__ef")
        self.spinBox__ef.setFrame(False)
        self.spinBox__ef.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.spinBox__ef.setMaximum(9999999)
        self.spinBox__ef.setValue(1240)
        self.spinBox__ef.setToolTip(_translate("Set the frame range of the video."))
        self.horizontalLayout__end_frame.addWidget(self.spinBox__ef)
        self.horizontalLayout__frame_range.addLayout(self.horizontalLayout__end_frame)
        self.spacer__frame_range_end = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__frame_range.addItem(self.spacer__frame_range_end)
        self.verticalLayout__video_settings.addLayout(
            self.horizontalLayout__frame_range
        )
        self.horizontalLayout__frame_rate_row = QHBoxLayout()
        self.horizontalLayout__frame_rate_row.setObjectName(
            "horizontalLayout__frame_rate_row"
        )
        self.horizontalLayout__frame_rate = QHBoxLayout()
        self.horizontalLayout__frame_rate.setObjectName("horizontalLayout__frame_rate")
        self.label__fps = QLabel(self.groupBox__video)
        self.label__fps.setObjectName("label__fps")
        self.label__fps.setText(_translate("FPS (Frame Per Seconds)"))
        self.horizontalLayout__frame_rate.addWidget(self.label__fps)
        self.spinBox__fps = QSpinBox(self.groupBox__video)
        self.spinBox__fps.setObjectName("spinBox__fps")
        self.spinBox__fps.setFrame(False)
        self.spinBox__fps.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.spinBox__fps.setMinimum(1)
        self.spinBox__fps.setMaximum(120)
        self.spinBox__fps.setValue(24)
        self.spinBox__fps.setToolTip(_translate("Set the FPS of the video."))
        self.horizontalLayout__frame_rate.addWidget(self.spinBox__fps)
        self.horizontalLayout__frame_rate_row.addLayout(
            self.horizontalLayout__frame_rate
        )
        self.spacer__frame_rate_row = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__frame_rate_row.addItem(self.spacer__frame_rate_row)
        self.verticalLayout__video_settings.addLayout(
            self.horizontalLayout__frame_rate_row
        )
        self.horizontalLayout__resolution_summary = QHBoxLayout()
        self.horizontalLayout__resolution_summary.setObjectName(
            "horizontalLayout__resolution_summary"
        )
        self.horizontalLayout__resolution = QHBoxLayout()
        self.horizontalLayout__resolution.setObjectName("horizontalLayout__resolution")
        self.label__resolution = QLabel(self.groupBox__video)
        self.label__resolution.setObjectName("label__resolution")
        self.label__resolution.setText(_translate("Resolution"))
        self.horizontalLayout__resolution.addWidget(self.label__resolution)
        self.comboBox__resolution = QComboBox(self.groupBox__video)
        self.comboBox__resolution.setObjectName("comboBox__resolution")
        self.comboBox__resolution.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.comboBox__resolution.setFrame(False)
        self.comboBox__resolution.setToolTip(
            _translate("Set the resolution of images to render.")
        )
        self.horizontalLayout__resolution.addWidget(self.comboBox__resolution)
        self.horizontalLayout__resolution_summary.addLayout(
            self.horizontalLayout__resolution
        )
        self.spacer__resolution_summary = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__resolution_summary.addItem(
            self.spacer__resolution_summary
        )
        self.label__confirm_resolution = QLabel(self.groupBox__video)
        self.label__confirm_resolution.setObjectName("label__confirm_resolution")
        self.label__confirm_resolution.setText("")
        self.horizontalLayout__resolution_summary.addWidget(
            self.label__confirm_resolution
        )
        self.spacer__resolution_summary_end = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__resolution_summary.addItem(
            self.spacer__resolution_summary_end
        )
        self.verticalLayout__video_settings.addLayout(
            self.horizontalLayout__resolution_summary
        )
        self.verticalLayout__video_info.addWidget(self.groupBox__video)

    def _build_flipbook_options(self, window: QDialog) -> None:
        self.groupBox__flipbook = QGroupBox(window)
        self.groupBox__flipbook.setObjectName("groupBox__flipbook")
        self.groupBox__flipbook.setTitle(_translate("Flipbook"))
        self.horizontalLayout__flipbook_options = QHBoxLayout(self.groupBox__flipbook)
        self.horizontalLayout__flipbook_options.setObjectName(
            "horizontalLayout__flipbook_options"
        )
        self.verticalLayout__viewport_options = QVBoxLayout()
        self.verticalLayout__viewport_options.setObjectName(
            "verticalLayout__viewport_options"
        )
        self.checkBox__beautypassonly = QCheckBox(self.groupBox__flipbook)
        self.checkBox__beautypassonly.setObjectName("checkBox__beautypassonly")
        self.checkBox__beautypassonly.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__beautypassonly.setToolTip(
            _translate(
                "Allows everything in the viewport to be rendered (False), or just the user geometry (True)."
            )
        )
        self.checkBox__beautypassonly.setText(_translate("Beauty Pass Only"))
        self.verticalLayout__viewport_options.addWidget(self.checkBox__beautypassonly)
        self.checkBox__render_all_viewports = QCheckBox(self.groupBox__flipbook)
        self.checkBox__render_all_viewports.setObjectName(
            "checkBox__render_all_viewports"
        )
        self.checkBox__render_all_viewports.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__render_all_viewports.setToolTip(
            _translate(
                "Render all visible viewports (True), or only the currently selected one."
            )
        )
        self.checkBox__render_all_viewports.setText(_translate("Render All Viewports"))
        self.verticalLayout__viewport_options.addWidget(
            self.checkBox__render_all_viewports
        )
        self.horizontalLayout__flipbook_options.addLayout(
            self.verticalLayout__viewport_options
        )
        self.verticalLayout__simulation_options = QVBoxLayout()
        self.verticalLayout__simulation_options.setObjectName(
            "verticalLayout__simulation_options"
        )
        self.checkBox__use_motionblur = QCheckBox(self.groupBox__flipbook)
        self.checkBox__use_motionblur.setObjectName("checkBox__use_motionblur")
        self.checkBox__use_motionblur.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__use_motionblur.setToolTip(_translate("Turn on motion blur."))
        self.checkBox__use_motionblur.setText(_translate("Use Motion Blur"))
        self.verticalLayout__simulation_options.addWidget(self.checkBox__use_motionblur)
        self.checkBox__crop_out_mask_overlay = QCheckBox(self.groupBox__flipbook)
        self.checkBox__crop_out_mask_overlay.setObjectName(
            "checkBox__crop_out_mask_overlay"
        )
        self.checkBox__crop_out_mask_overlay.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__crop_out_mask_overlay.setToolTip(
            _translate("When enabled, the camera area is cropped out.")
        )
        self.checkBox__crop_out_mask_overlay.setText(
            _translate("Crop Out Mask Overlay")
        )
        self.verticalLayout__simulation_options.addWidget(
            self.checkBox__crop_out_mask_overlay
        )
        self.checkBox__initialize_sim = QCheckBox(self.groupBox__flipbook)
        self.checkBox__initialize_sim.setObjectName("checkBox__initialize_sim")
        self.checkBox__initialize_sim.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__initialize_sim.setToolTip(
            _translate(
                "When enabled, all simulations are re-initialized when the flipbook begins."
            )
        )
        self.checkBox__initialize_sim.setText(_translate("Initialize Simulations"))
        self.verticalLayout__simulation_options.addWidget(self.checkBox__initialize_sim)
        self.horizontalLayout__flipbook_options.addLayout(
            self.verticalLayout__simulation_options
        )
        self.verticalLayout__video_info.addWidget(self.groupBox__flipbook)

    def _build_dialog_buttons(self, window: QDialog) -> None:
        self.buttonBox__confirm = QDialogButtonBox(window)
        self.buttonBox__confirm.setObjectName("buttonBox__confirm")
        self.buttonBox__confirm.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.buttonBox__confirm.setLocale(
            QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        )
        self.buttonBox__confirm.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox__confirm.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.verticalLayout__video_info.addWidget(self.buttonBox__confirm)
        self.label__sf.setBuddy(self.spinBox__sf)
        self.label__ef.setBuddy(self.spinBox__ef)
        self.label__fps.setBuddy(self.spinBox__sf)
        self.buttonBox__confirm.accepted.connect(window.accept)
        self.buttonBox__confirm.rejected.connect(window.reject)
