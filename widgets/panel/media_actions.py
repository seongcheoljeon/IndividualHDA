"""Media actions for the Individual HDA panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
import pathlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets

from libs import ffmpeg_api, host, houdini_api, ihda_system, keys, log_handler
from libs.host_ports import HostCapturePort
from widgets.asset_media.presenter import AssetMediaPresenter, MediaRequest

if TYPE_CHECKING:
    from re import Pattern

    from libs.task_controller import TaskController
    from widgets.make_video_info.make_video_info import MakeVideoInfo
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.library_port import LibraryPort
    from widgets.panel.ports import (
        AssetModelPort,
        LibraryQueryPort,
        PresentationPort,
        SelectionPort,
    )
    from widgets.panel.state import PanelSessionState, PanelStatus
    from widgets.preference.preference import Preference


@dataclass(frozen=True, slots=True)
class PanelMediaActionsBindings:
    capture: HostCapturePort
    host_enabled: bool
    models: AssetModelPort
    parent: QtWidgets.QWidget
    preference: Preference
    presentation: PresentationPort
    queries: LibraryQueryPort
    selection: SelectionPort
    sequence_pattern: Pattern[str]
    session: PanelSessionState
    status: PanelStatus
    tasks: TaskController
    library: Callable[[], LibraryPort]
    ui: MainWindowLayout
    video_info: MakeVideoInfo


class PanelMediaActions:
    bindings: PanelMediaActionsBindings

    def show_media_error(self, message: str) -> None:
        log_handler.LogHandler.log_msg(method=logging.error, msg=message)

    @staticmethod
    def _remove_preview_dir(preview_dirpath: pathlib.Path | None = None) -> bool:
        assert isinstance(preview_dirpath, pathlib.Path)
        is_del = False
        if preview_dirpath.parent.exists():
            if preview_dirpath.parent.name == keys.Name.preview_dirname:
                is_del = ihda_system.IHDASystem.remove_dir(
                    dirpath=preview_dirpath.parent, verbose=False
                )
        return is_del

    def slot_make_thumbnail(self) -> None:
        if not self.bindings.host_enabled:
            return
        if self.bindings.library().attach("thumbnail"):
            return
        if host.IS_HOUDINI:
            hda_dirpath = self.bindings.selection.state.asset.require_data().hda_dirpath
            hda_name = self.bindings.selection.state.asset.require_data().hda_name
            hda_version = self.bindings.selection.state.asset.require_data().hda_version
            hda_id = self.bindings.selection.state.asset.require_data().hda_id
            # thumbnail
            thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(
                hda_dirpath=hda_dirpath
            )
            thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(
                name=hda_name, version=hda_version
            )
            thumb_filepath = thumb_dirpath / thumb_filename
            if not thumb_dirpath.exists():
                thumb_dirpath.mkdir(parents=True)
            self.bindings.capture.create_thumbnail(output_filepath=thumb_filepath)
            AssetMediaPresenter(
                self, self.bindings.session.require_repository()
            ).thumbnail(
                MediaRequest(hda_id, hda_version, thumb_dirpath, thumb_filename),
                lambda updated: self._apply_thumbnail(
                    hda_id, hda_version, thumb_filepath, updated
                ),
            )
        else:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="run on the houdini"
            )

    def _apply_thumbnail(
        self,
        hda_id: int,
        hda_version: str,
        thumb_filepath: pathlib.Path,
        is_update_thumb: bool,
    ) -> None:
        # model에서 새로운 파일을 새롭게 읽을 수 있도록 thumb_filepath인자에 값을 배정하지 않았다.
        # self._update_pixmap_thumbnail(hkey_id=hda_id, thumb_filepath=pathlib.Path())
        self.bindings.models.update_pixmap_thumbnail(
            hkey_id=hda_id, thumb_filepath=thumb_filepath
        )
        hist_id = self.bindings.models.history_model.get_history_id_from_model(
            hkey_id=hda_id, version=hda_version
        )
        if hist_id is not None:
            self.bindings.models.update_pixmap_hist_thumbnail(
                hist_id=hist_id, thumb_filepath=thumb_filepath
            )
        if is_update_thumb:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="thumbnail update completed"
            )

    def _slot_make_video(self) -> None:
        if not self.bindings.host_enabled:
            return
        if self.bindings.library().attach("video"):
            return
        if self.bindings.tasks.busy:
            return
        if not self.bindings.preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="ffmpeg is not installed"
            )
            return
        if not host.IS_HOUDINI:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="run on the houdini"
            )
            return
        new_frinfo = [
            self.bindings.video_info.sf,
            self.bindings.video_info.ef,
            self.bindings.video_info.fps,
        ]
        num_frame = (new_frinfo[1] - new_frinfo[0]) + 1
        if num_frame <= 0:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="frame range is wrong"
            )
            return
        self.bindings.presentation.loading_show()
        data = self.bindings.selection.state.asset.require_data()
        hda_dirpath = data.hda_dirpath
        hda_name = data.hda_name
        hda_version = data.hda_version
        hda_id = data.hda_id
        preview_dirpath = houdini_api.HoudiniAPI.make_preview_dirpath(
            hda_dirpath=hda_dirpath, version=hda_version
        )
        preview_filename = houdini_api.HoudiniAPI.make_preview_filename(
            name=hda_name, version=hda_version
        )
        preview_filepath = self._make_preview(
            preview_dirpath=preview_dirpath,
            preview_filename=preview_filename,
            frinfo=new_frinfo,
            res=self.bindings.video_info.get_resolution(),
            is_beauty=self.bindings.video_info.is_beautypass,
            is_initsim=self.bindings.video_info.is_init_sim,
            is_motion=self.bindings.video_info.is_motionblur,
            is_crop=self.bindings.video_info.is_crop_mask,
        )
        if preview_filepath is None:
            self._remove_preview_dir(preview_dirpath=preview_dirpath)
            self.bindings.presentation.loading_close()
            return
        # $F4 --> %04d
        preview_filepath = preview_filepath.with_name(
            self.bindings.sequence_pattern.sub("%04d", preview_filepath.name)
        )
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg=f"[{new_frinfo[0]}-{new_frinfo[1]}, fps: {new_frinfo[2]}]",
        )
        meta_data = {
            keys.Name.FFmpeg.Metadata.author: self.bindings.session.user,
            keys.Name.FFmpeg.Metadata.year: str(
                QtCore.QDate.currentDate().toString("yyyy")
            ),
            keys.Name.FFmpeg.Metadata.title: hda_name,
            keys.Name.FFmpeg.Metadata.desc: f"{keys.Name.hda_prefix_str} Video",
        }
        video_dirpath = houdini_api.HoudiniAPI.make_video_dirpath(
            hda_dirpath=hda_dirpath
        )
        video_filename = houdini_api.HoudiniAPI.make_video_filename(
            name=hda_name, version=hda_version
        )
        video_dirpath.mkdir(parents=True, exist_ok=True)
        output = video_dirpath / video_filename
        temporary = output.with_name(
            f".{output.stem}-{uuid.uuid4().hex}{output.suffix}"
        )
        try:
            command = ffmpeg_api.FFmpegAPI.image_sequence_command(
                self.bindings.preference.ffmpeg_dirpath,
                preview_filepath,
                temporary,
                int(new_frinfo[0]),
                int(num_frame),
                new_frinfo[2],
                meta_data,
            )
        except (OSError, ValueError) as error:
            logging.error("Cannot start video encoding: %s", error)
            self.bindings.presentation.loading_close()
            return
        self.bindings.ui.centralwidget.setEnabled(False)
        self.bindings.ui.toolBar.setEnabled(False)
        self.bindings.ui.menubar.setEnabled(False)

        def finished(code: int, diagnostic: str) -> None:
            try:
                if code != 0 or self.bindings.status.closing:
                    if not self.bindings.status.closing:
                        logging.error("Video creation failed: %s", diagnostic[-8192:])
                    return
                temporary.replace(output)
                self._finish_video(
                    hda_id, hda_version, video_dirpath, video_filename, preview_dirpath
                )
            except (OSError, RuntimeError) as error:
                logging.error("Cannot finish video creation: %s", error)
            finally:
                temporary.unlink(missing_ok=True)
                self.bindings.presentation.loading_close()
                self.bindings.ui.centralwidget.setEnabled(True)
                self.bindings.ui.toolBar.setEnabled(True)
                self.bindings.ui.menubar.setEnabled(True)

        try:
            if not self.bindings.tasks.start_process(command, finished):
                finished(-1, "Another library operation is active")
        except Exception as error:
            finished(-1, str(error))

    def _finish_video(
        self,
        hda_id: int,
        hda_version: str,
        video_dirpath: pathlib.Path,
        video_filename: str,
        preview_dirpath: pathlib.Path,
    ) -> None:
        if self.bindings.session.repository is None:
            return
        row = self.bindings.models.assets.id_rows.get(hda_id)
        if row is None:
            raise RuntimeError("Encoded asset is no longer in the library")
        request = MediaRequest(hda_id, hda_version, video_dirpath, video_filename)
        if AssetMediaPresenter(self, self.bindings.session.require_repository()).video(
            request, lambda kind: self._apply_video(row, request, kind)
        ):
            self._remove_preview_dir(preview_dirpath=preview_dirpath)
        self.bindings.presentation.loading_close()

    def _apply_video(self, row: int, request: MediaRequest, kind: str) -> None:
        video_dirpath, video_filename = request.directory, request.filename
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f"video {kind} complete"
        )
        self.bindings.queries.change_hda_data(
            row=row, key=keys.Key.video_dirpath, val=video_dirpath
        )
        self.bindings.queries.change_hda_data(
            row=row, key=keys.Key.video_filename, val=video_filename
        )
        # history
        # Media changes update the current version and its audit trail.

    def _make_preview(
        self,
        preview_dirpath: pathlib.Path | None = None,
        preview_filename: Any = None,
        frinfo: Any = None,
        res: Any = None,
        is_beauty: bool = False,
        is_initsim: bool = False,
        is_motion: bool = False,
        is_crop: bool = False,
    ) -> pathlib.Path | None:
        assert isinstance(preview_dirpath, pathlib.Path)
        preview_filepath = preview_dirpath / preview_filename
        for pfile in preview_dirpath.glob("*.jpg"):
            pfile.unlink()
        if not preview_dirpath.exists():
            preview_dirpath.mkdir(parents=True)
        is_done_preview = self.bindings.capture.create_preview(
            output_filepath=preview_filepath,
            frame_info=frinfo,
            resolution=res,
            is_beautypass_only=is_beauty,
            is_init_sim=is_initsim,
            is_motionblur=is_motion,
            is_crop_out_mask=is_crop,
        )
        if not is_done_preview:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="failed to create preview"
            )
            ihda_system.IHDASystem.remove_dir(dirpath=preview_dirpath, verbose=False)
            return None
        return preview_filepath
