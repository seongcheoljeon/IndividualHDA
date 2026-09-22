from __future__ import annotations

import pathlib
from collections.abc import Sequence

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.21 02:29:45
# modified date:
# description:      iHDA icons
from typing import Any, Protocol

from PySide6 import QtGui

# third-party modules
from libs import keys
from libs.asset_contracts import AssetData, HistoryData, HistoryThumbnail
from libs.houdini_api import HoudiniAPI
from libs.resource_policy import ThumbnailPolicy
from libs.thumbnail_cache import ThumbnailCache
from libs.ui_icons import Icon

BLANK_ICON = ":/main/icons/blank.png"
CHANNEL_ICON = ":/main/icons/chan.png"


def _host_pixmap(icon_lst: list[str] | None = None) -> QtGui.QPixmap:
    """A Houdini node icon, or a bundled stand-in outside Houdini.

    Houdini serves icons through ``hou.qt.Icon``; the panel used to read
    ``$HH/help/icons.zip`` instead, which has not existed since Houdini 19 moved
    it and newer builds keep their UI icons in an SVG cache. Nothing is read
    from disk here.
    """
    if not icon_lst:
        return QtGui.QPixmap(BLANK_ICON)
    pixmap = HoudiniAPI.host_icon("_".join(str(part) for part in icon_lst))
    if pixmap is not None and not pixmap.isNull():
        return pixmap
    if str(icon_lst[0]).lower() == keys.Type.chop:
        return QtGui.QPixmap(CHANNEL_ICON)
    return QtGui.QPixmap(BLANK_ICON)


class IconProvider(Protocol):
    """Pixmaps for nodes the caches do not know: resolved from Houdini icon names."""

    def get_houdini_icon(self, icon_lst: list[str] | None = None) -> QtGui.QPixmap: ...
    def get_category_icon(self, category: str | None = None) -> QtGui.QPixmap: ...


class IHDAIcons:
    def __init__(
        self, *, thumbnail_policy: ThumbnailPolicy = ThumbnailPolicy()
    ) -> None:
        self.__default_pixmap = QtGui.QPixmap(Icon.NO_IMG_AVAILABLE)
        self.__pixmap_ihda_data: dict[int, QtGui.QPixmap] = {}
        self.__pixmap_cate_data: dict[str, QtGui.QPixmap] = {}
        self.__pixmap_thumbnail_data = ThumbnailCache(
            self.__default_pixmap, policy=thumbnail_policy
        )
        self.__pixmap_hist_thumbnail_data = ThumbnailCache(
            self.__default_pixmap, policy=thumbnail_policy
        )

    def __del__(self) -> None:
        del self.__pixmap_ihda_data
        del self.__pixmap_cate_data
        del self.__pixmap_thumbnail_data
        del self.__pixmap_hist_thumbnail_data

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
        if hkey_id is not None and hkey_id in self.__pixmap_thumbnail_data:
            del self.__pixmap_thumbnail_data[hkey_id]

    def remove_pixmap_hist_thumbnail_data(self, hist_id: int | None = None) -> None:
        if hist_id is not None and hist_id in self.__pixmap_hist_thumbnail_data:
            del self.__pixmap_hist_thumbnail_data[hist_id]

    def add_pixmap_ihda_data(
        self, hkey_id: int | None = None, icon_lst: list[str] | None = None
    ) -> None:
        if hkey_id is not None and hkey_id not in self.__pixmap_ihda_data:
            self.__pixmap_ihda_data[hkey_id] = _host_pixmap(icon_lst)

    def add_pixmap_cate_data(self, category: str | None = None) -> None:
        if category is not None and category not in self.__pixmap_cate_data:
            self.__pixmap_cate_data[category] = _host_pixmap(
                [keys.Name.Icons.networks, category]
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
        for info in icon_info:
            self.__pixmap_ihda_data[info.asset_id] = _host_pixmap(list(info.icon))

    def make_pixmap_cate_data(self, cate_lst: Any = None) -> None:
        if cate_lst is None:
            return
        net_dirname = keys.Name.Icons.networks
        root_name = keys.Name.Icons.root
        self.__pixmap_cate_data[root_name] = _host_pixmap([net_dirname, root_name])
        for cate in [x.lower() for x in cate_lst]:
            self.__pixmap_cate_data[cate] = _host_pixmap([net_dirname, cate])

    def make_pixmap_thumbnail_data(
        self, all_data: list[AssetData] | None = None
    ) -> None:
        for data in all_data or []:
            directory, filename = (
                data.thumbnail_dirpath,
                data.thumbnail_filename,
            )
            self.__pixmap_thumbnail_data.set_path(
                data.hda_id, directory / filename if directory and filename else None
            )

    def make_pixmap_hist_thumbnail_data(
        self, all_data: Sequence[HistoryThumbnail | HistoryData] | None = None
    ) -> None:
        for data in all_data or []:
            directory, filename = data.thumb_dirpath, data.thumb_filename
            self.__pixmap_hist_thumbnail_data.set_path(
                data.hist_id,
                directory / filename if directory and filename else None,
            )

    def get_houdini_icon(self, icon_lst: list[str] | None = None) -> QtGui.QPixmap:
        return _host_pixmap(icon_lst)

    def get_category_icon(self, category: str | None = None) -> QtGui.QPixmap:
        return _host_pixmap([keys.Name.Icons.networks, category or ""])
