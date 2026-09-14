from __future__ import annotations

import logging
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from logging import warning

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.21 02:29:45
# modified date:
# description:      iHDA icons
from re import compile
from typing import Any
from zipfile import ZipFile, is_zipfile

from PySide6 import QtGui

import public

# third-party modules
from libs import log_handler
from libs.domain import AssetData, HistoryData
from libs.thumbnail_cache import ThumbnailCache


class IHDAIcons:
    def __init__(self) -> None:
        self.__zip_filepath = public.Paths.hh_dirpath / "help" / "icons.zip"
        if not self.__zip_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="icon zip file does not exist"
            )
        self.__pattern_icon_map = compile(r"(?P<dirname>^[A-Z_]+)(?P<filename>.+)")
        self.__default_pixmap = QtGui.QPixmap(":/main/icons/no_img_available.png")
        self.__pixmap_ihda_data = {}
        self.__pixmap_cate_data = {}
        self.__pixmap_thumbnail_data = ThumbnailCache(self.__default_pixmap)
        self.__pixmap_hist_thumbnail_data = ThumbnailCache(self.__default_pixmap)
        self.__icons_map = self.__icons_mapping_from_file() or {}

    def __del__(self) -> None:
        del self.__pixmap_ihda_data
        del self.__pixmap_cate_data
        del self.__pixmap_thumbnail_data
        del self.__pixmap_hist_thumbnail_data
        del self.__icons_map

    @property
    def pixmap_ihda_data(self) -> dict[int, QtGui.QPixmap]:
        return self.__pixmap_ihda_data

    @property
    def pixmap_cate_data(self) -> dict[str, QtGui.QPixmap]:
        return self.__pixmap_cate_data

    @property
    def pixmap_thumbnail_data(self) -> ThumbnailCache:
        return self.__pixmap_thumbnail_data

    @property
    def pixmap_hist_thumbnail_data(self) -> ThumbnailCache:
        return self.__pixmap_hist_thumbnail_data

    def remove_pixmap_ihda_data(self, hkey_id: int | None = None) -> None:
        if hkey_id in self.__pixmap_ihda_data:
            del self.__pixmap_ihda_data[hkey_id]

    def remove_pixmap_cate_data(self, category: str | None = None) -> None:
        if category in self.__pixmap_cate_data:
            del self.__pixmap_cate_data[category]

    def remove_pixmap_thumbnail_data(self, hkey_id: int | None = None) -> None:
        if hkey_id in self.__pixmap_thumbnail_data:
            del self.__pixmap_thumbnail_data[hkey_id]

    def remove_pixmap_hist_thumbnail_data(self, hist_id: int | None = None) -> None:
        if hist_id in self.__pixmap_hist_thumbnail_data:
            del self.__pixmap_hist_thumbnail_data[hist_id]

    def clear_pixmap_hist_thumbnail_data(self) -> None:
        self.__pixmap_hist_thumbnail_data.clear()

    def add_pixmap_ihda_data(
        self, hkey_id: int | None = None, icon_lst: list[str] | None = None
    ) -> None:
        if hkey_id not in self.__pixmap_ihda_data:
            with self._icon_archive() as zip_fp:
                self.__pixmap_ihda_data[hkey_id] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst
                )

    def add_pixmap_cate_data(self, category: str | None = None) -> None:
        if category not in self.__pixmap_cate_data:
            with self._icon_archive() as zip_fp:
                net_dirname = public.Name.Icons.networks
                icon_lst = [net_dirname, category]
                self.__pixmap_cate_data[category] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst
                )

    def add_pixmap_thumbnail_data(
        self, hkey_id: int, thumb_filepath: pathlib.Path
    ) -> None:
        self.__pixmap_thumbnail_data.set_path(hkey_id, thumb_filepath)

    def add_pixmap_hist_thumbnail_data(
        self, hist_id: int, thumb_filepath: pathlib.Path
    ) -> None:
        self.__pixmap_hist_thumbnail_data.set_path(hist_id, thumb_filepath)

    def update_pixmap_thumbnail_data(
        self, hkey_id: int, thumb_filepath: pathlib.Path
    ) -> None:
        self.__pixmap_thumbnail_data.set_path(hkey_id, thumb_filepath)

    def update_pixmap_hist_thumbnail_data(
        self, hist_id: int, thumb_filepath: pathlib.Path
    ) -> None:
        self.__pixmap_hist_thumbnail_data.set_path(hist_id, thumb_filepath)

    def shutdown(self) -> None:
        self.__pixmap_thumbnail_data.shutdown()
        self.__pixmap_hist_thumbnail_data.shutdown()

    def make_pixmap_ihda_data(self, icon_info: Any = None) -> None:
        if icon_info is None:
            return
        with self._icon_archive() as zip_fp:
            for info in icon_info:
                hkey_id, icon_lst = info
                self.__pixmap_ihda_data[hkey_id] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst
                )

    def make_pixmap_cate_data(self, cate_lst: Any = None) -> None:
        if cate_lst is None:
            return
        net_dirname = public.Name.Icons.networks
        root_name = public.Name.Icons.root
        with self._icon_archive() as zip_fp:
            self.__pixmap_cate_data[root_name] = self.__get_icon_from_zipfile(
                zip_fp=zip_fp, icon_lst=[net_dirname, root_name]
            )
            for cate in [x.lower() for x in cate_lst]:
                icon_lst = [net_dirname, cate]
                self.__pixmap_cate_data[cate] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst
                )

    def make_pixmap_thumbnail_data(
        self, all_data: list[AssetData] | None = None
    ) -> None:
        for data in all_data or []:
            directory, filename = (
                data.get("thumbnail_dirpath"),
                data.get("thumbnail_filename"),
            )
            self.__pixmap_thumbnail_data.set_path(
                data["hda_id"], directory / filename if directory and filename else None
            )

    def make_pixmap_hist_thumbnail_data(
        self, all_data: list[HistoryData] | None = None
    ) -> None:
        for data in all_data or []:
            directory, filename = data.get("thumb_dirpath"), data.get("thumb_filename")
            self.__pixmap_hist_thumbnail_data.set_path(
                data["hist_id"],
                directory / filename if directory and filename else None,
            )

    def get_houdini_icon(self, icon_lst: list[str] | None = None) -> QtGui.QPixmap:
        with self._icon_archive() as zip_fp:
            return self.__get_icon_from_zipfile(zip_fp=zip_fp, icon_lst=icon_lst)

    def get_category_icon(self, category: str | None = None) -> QtGui.QPixmap:
        with self._icon_archive() as zip_fp:
            icon_lst = [public.Name.Icons.networks, category]
            return self.__get_icon_from_zipfile(zip_fp=zip_fp, icon_lst=icon_lst)

    @contextmanager
    def _icon_archive(self) -> Iterator[Any]:
        if self.is_valid_zipfile():
            with ZipFile(self.__zip_filepath) as archive:
                yield archive
        else:
            yield None

    def __get_icon_from_zipfile(
        self, zip_fp: Any = None, icon_lst: list[str] | None = None
    ) -> QtGui.QPixmap:
        if not icon_lst:
            return QtGui.QPixmap(":/main/icons/blank.png")
        if public.IS_HOUDINI:
            try:
                return public.hou.qt.Icon("_".join(icon_lst)).pixmap(128, 128)
            except (RuntimeError, public.hou.Error):
                pass
        if zip_fp is None:
            return QtGui.QPixmap(":/main/icons/blank.png")
        icon_file_ext = public.Extensions.houdini_icons
        icon_filepath = "/".join([str(icon_lst[0]), str(icon_lst[1]) + icon_file_ext])
        try:
            contents = zip_fp.read(icon_filepath)
            img = QtGui.QImage.fromData(contents)
            pixmap = QtGui.QPixmap.fromImage(img)
            return pixmap
        except (KeyError, RuntimeError):
            icon_map = self.__icons_map.get("_".join(icon_lst))
            if icon_map is None:
                icon_filepath = "/".join(
                    [public.Name.Icons.desktop, public.Name.Icons.blank + icon_file_ext]
                )
            else:
                icon_map_lst = [
                    str(x.strip("_"))
                    for x in self.__pattern_icon_map.match(icon_map).groups()
                ]
                icon_filepath = "/".join(
                    [icon_map_lst[0], icon_map_lst[1] + icon_file_ext]
                )
            try:
                contents = zip_fp.read(icon_filepath)
                img = QtGui.QImage.fromData(contents)
                pixmap = QtGui.QPixmap.fromImage(img)
                return pixmap
            except (KeyError, RuntimeError):
                if icon_lst[0].lower() == public.Type.chop:
                    return QtGui.QPixmap(":/main/icons/chan.png")
                return QtGui.QPixmap(":/main/icons/blank.png")

    def __icons_mapping_from_file(self) -> None | dict[str, Any]:
        if not self.is_valid_zipfile():
            if not self.__zip_filepath.exists():
                log_handler.LogHandler.log_msg(
                    method=warning, msg="icons mapping file does not exist"
                )
            elif not is_zipfile(self.__zip_filepath.as_posix()):
                log_handler.LogHandler.log_msg(
                    method=warning, msg="it's not a zip file"
                )
            else:
                log_handler.LogHandler.log_msg(
                    method=warning, msg="unknown zip file error"
                )
            return None
        split_str = ":="
        pattern_split = compile(rf"{split_str}")
        pattern_del = compile(r"[\s;]")
        icons_dict = {}
        with (
            self._icon_archive() as zip_fp,
            zip_fp.open(public.Name.Icons.filename, "r") as fp,
        ):
            for line in fp:
                line = line.decode("utf-8")
                if pattern_split.search(line) is not None:
                    lst = [pattern_del.sub("", x) for x in line.split(f"{split_str}")]
                    icons_dict[lst[0]] = lst[1]

        if len(icons_dict):
            return icons_dict
        return None

    def is_valid_zipfile(self) -> bool:
        if self.__zip_filepath.exists():
            if is_zipfile(self.__zip_filepath.as_posix()):
                return True
        return False
