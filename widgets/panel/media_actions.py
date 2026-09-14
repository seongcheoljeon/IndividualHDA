"""Media actions for the Individual HDA panel.

Mixin methods run on the panel GUI thread and share its protected state.
They do not own a separate QWidget or change the public panel interface.
"""

from __future__ import annotations

from contextlib import closing
from typing import Any
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

import uuid
import logging
from PySide6 import QtCore
import public
from libs import houdini_api, log_handler
from libs import ffmpeg_api, ihda_system


class MediaActionsMixin:
    @staticmethod
    def _remove_preview_dir(preview_dirpath: pathlib.Path | None = None) -> bool:
        assert isinstance(preview_dirpath, pathlib.Path)
        is_del = False
        if preview_dirpath.parent.exists():
            if preview_dirpath.parent.name == public.Name.preview_dirname:
                is_del = ihda_system.IHDASystem.remove_dir(
                    dirpath=preview_dirpath.parent, verbose=False
                )
        return is_del

    def _slot_make_thumbnail(self, db_api: SQLite3DatabaseAPI | None = None) -> None:
        if public.IS_HOUDINI:
            hda_dirpath = self._selection.asset.data.get(public.Key.hda_dirpath)
            hda_name = self._selection.asset.data.get(public.Key.hda_name)
            hda_version = self._selection.asset.data.get(public.Key.hda_version)
            hda_id = self._selection.asset.data.get(public.Key.hda_id)
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
            houdini_api.HoudiniAPI.create_thumbnail(output_filepath=thumb_filepath)
            is_update_thumb = db_api.update_thumbnail_info(
                hda_key_id=hda_id,
                dirpath=thumb_dirpath,
                filename=thumb_filename,
                version=hda_version,
            )
            # model에서 새로운 파일을 새롭게 읽을 수 있도록 thumb_filepath인자에 값을 배정하지 않았다.
            # self._update_pixmap_thumbnail(hkey_id=hda_id, thumb_filepath=pathlib.Path())
            self._update_pixmap_thumbnail(hkey_id=hda_id, thumb_filepath=thumb_filepath)
            hist_id = self._ihda_history_model.get_history_id_from_model(
                hkey_id=hda_id, version=hda_version
            )
            if hist_id is not None:
                self._update_pixmap_hist_thumbnail(
                    hist_id=hist_id, thumb_filepath=thumb_filepath
                )
            if is_update_thumb:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg="thumbnail update completed"
                )
        else:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="run on the houdini"
            )

    def _slot_make_video(self) -> None:
        if self._tasks.busy:
            return
        if not self._preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="ffmpeg is not installed"
            )
            return
        if not public.IS_HOUDINI:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="run on the houdini"
            )
            return
        new_frinfo = [
            self._make_videoinfo.sf,
            self._make_videoinfo.ef,
            self._make_videoinfo.fps,
        ]
        num_frame = (new_frinfo[1] - new_frinfo[0]) + 1
        if num_frame <= 0:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="frame range is wrong"
            )
            return
        self._loading_show()
        data = self._selection.asset.data
        hda_dirpath = data.get(public.Key.hda_dirpath)
        hda_name = data.get(public.Key.hda_name)
        hda_version = data.get(public.Key.hda_version)
        hda_id = data.get(public.Key.hda_id)
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
            res=self._make_videoinfo.get_resolution(),
            is_beauty=self._make_videoinfo.is_beautypass,
            is_initsim=self._make_videoinfo.is_init_sim,
            is_motion=self._make_videoinfo.is_motionblur,
            is_crop=self._make_videoinfo.is_crop_mask,
        )
        if preview_filepath is None:
            is_del = self._remove_preview_dir(preview_dirpath=preview_dirpath)
            self._loading_close()
            return
        # $F4 --> %04d
        preview_filepath = preview_filepath.with_name(
            self._regex_squence_str.sub("%04d", preview_filepath.name)
        )
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="[{0}-{1}, fps: {2}]".format(
                new_frinfo[0], new_frinfo[1], new_frinfo[2]
            ),
        )
        meta_data = {
            public.Name.FFmpeg.Metadata.author: self._user,
            public.Name.FFmpeg.Metadata.year: str(
                QtCore.QDate.currentDate().toString("yyyy")
            ),
            public.Name.FFmpeg.Metadata.title: hda_name,
            public.Name.FFmpeg.Metadata.desc: "{0} Video".format(
                public.Name.hda_prefix_str
            ),
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
                self._preference.ffmpeg_dirpath,
                preview_filepath,
                temporary,
                new_frinfo[0],
                num_frame,
                new_frinfo[2],
                meta_data,
            )
        except (OSError, ValueError) as error:
            logging.error("Cannot start video encoding: %s", error)
            self._loading_close()
            return
        self.centralwidget.setEnabled(False)
        self.toolBar.setEnabled(False)
        self.menubar.setEnabled(False)

        def finished(code: int, diagnostic: str) -> None:
            try:
                if code != 0 or self._closing:
                    if not self._closing:
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
                self._loading_close()
                self.centralwidget.setEnabled(True)
                self.toolBar.setEnabled(True)
                self.menubar.setEnabled(True)

        try:
            if not self._tasks.start_process(command, finished):
                finished(-1, "Another library operation is active")
        except Exception as error:
            finished(-1, str(error))

    def _finish_video(
        self,
        hda_id: int,
        hda_version: str | None,
        video_dirpath: pathlib.Path,
        video_filename: str,
        preview_dirpath: pathlib.Path,
    ) -> None:
        comment = ""
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is None:
            return
        with closing(db_api):
            row = self._assets.id_rows.get(hda_id)
            if row is None:
                raise RuntimeError("Encoded asset is no longer in the library")
            get_video_path = db_api.get_video_info(hda_key_id=hda_id)
            is_video_db_done = False
            if get_video_path is None:
                is_insert_video = db_api.insert_video_info(
                    hda_key_id=hda_id,
                    dirpath=video_dirpath,
                    filename=video_filename,
                    version=hda_version,
                )
                if is_insert_video is not None:
                    is_video_db_done = True
                    comment = "VIDEO (INSERT)"
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg="video insertion complete"
                    )
            else:
                is_update_video = db_api.update_video_info(
                    hda_key_id=hda_id,
                    dirpath=video_dirpath,
                    filename=video_filename,
                    version=hda_version,
                )
                if is_update_video is not None:
                    is_video_db_done = True
                    comment = "VIDEO (UPDATE)"
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg="video update complete"
                    )
            if is_video_db_done:
                self._change_hda_data(
                    row=row, key=public.Key.video_dirpath, val=video_dirpath
                )
                self._change_hda_data(
                    row=row, key=public.Key.video_filename, val=video_filename
                )
                # history
                self._insert_hist_db_from_curt_hist_data(
                    db_api=db_api, comment=comment, data=self._assets.rows[row]
                )
        is_del = self._remove_preview_dir(preview_dirpath=preview_dirpath)
        self._loading_close()

    @staticmethod
    def _make_preview(
        preview_dirpath: pathlib.Path | None = None,
        preview_filename: Any = None,
        frinfo: Any = None,
        res: Any = None,
        is_beauty: bool | None = None,
        is_initsim: bool | None = None,
        is_motion: bool | None = None,
        is_crop: bool | None = None,
    ) -> pathlib.Path | None:
        assert isinstance(preview_dirpath, pathlib.Path)
        preview_filepath = preview_dirpath / preview_filename
        for pfile in preview_dirpath.glob("*.jpg"):
            pfile.unlink()
        if not preview_dirpath.exists():
            preview_dirpath.mkdir(parents=True)
        is_done_preview = houdini_api.HoudiniAPI.create_preview(
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
