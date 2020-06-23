# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.21 02:29:45
# modified date:    
# description:      iHDA icons

from re import compile
from imp import reload
from site import addsitedir
from logging import warning
from zipfile import ZipFile, is_zipfile
import logging

from PySide2 import QtGui

import public

reload(public)

addsitedir(public.Paths.python_packages_dirpath.as_posix())

# third-party modules
import pathlib2

from libs import log_handler

reload(log_handler)


class IHDAIcons(object):
    def __init__(self):
        self.__zip_filepath = public.Paths.hh_dirpath / 'help' / 'icons.zip'
        if not self.__zip_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='icon zip file does not exist')
        self.__pattern_icon_map = compile(r'(?P<dirname>^[A-Z_]+)(?P<filename>.+)')
        self.__default_pixmap = QtGui.QPixmap(':/main/icons/no_img_available.png')
        self.__pixmap_ihda_data = dict()
        self.__pixmap_cate_data = dict()
        self.__pixmap_thumbnail_data = dict()
        self.__pixmap_hist_thumbnail_data = dict()
        self.__icons_map = self.__icons_mapping_from_file()

    def __del__(self):
        del self.__pixmap_ihda_data
        del self.__pixmap_cate_data
        del self.__pixmap_thumbnail_data
        del self.__pixmap_hist_thumbnail_data
        del self.__icons_map

    @property
    def pixmap_ihda_data(self):
        return self.__pixmap_ihda_data

    @property
    def pixmap_cate_data(self):
        return self.__pixmap_cate_data

    @property
    def pixmap_thumbnail_data(self):
        return self.__pixmap_thumbnail_data

    @property
    def pixmap_hist_thumbnail_data(self):
        return self.__pixmap_hist_thumbnail_data

    def remove_pixmap_ihda_data(self, hkey_id=None):
        if hkey_id in self.__pixmap_ihda_data:
            del self.__pixmap_ihda_data[hkey_id]

    def remove_pixmap_cate_data(self, category=None):
        if category in self.__pixmap_cate_data:
            del self.__pixmap_cate_data[category]

    def remove_pixmap_thumbnail_data(self, hkey_id=None):
        if hkey_id in self.__pixmap_thumbnail_data:
            del self.__pixmap_thumbnail_data[hkey_id]

    def remove_pixmap_hist_thumbnail_data(self, hist_id=None):
        if hist_id in self.__pixmap_hist_thumbnail_data:
            del self.__pixmap_hist_thumbnail_data[hist_id]

    def clear_pixmap_hist_thumbnail_data(self):
        del self.__pixmap_hist_thumbnail_data
        self.__pixmap_hist_thumbnail_data = dict()

    def add_pixmap_ihda_data(self, hkey_id=None, icon_lst=None):
        if hkey_id not in self.__pixmap_ihda_data:
            with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
                self.__pixmap_ihda_data[hkey_id] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst)

    def add_pixmap_cate_data(self, category=None):
        if category not in self.__pixmap_cate_data:
            with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
                net_dirname = public.Name.Icons.networks
                icon_lst = [net_dirname, category]
                self.__pixmap_cate_data[category] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst)

    def add_pixmap_thumbnail_data(self, hkey_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        self.__pixmap_thumbnail_data[hkey_id] = QtGui.QPixmap(thumb_filepath.as_posix())

    def add_pixmap_hist_thumbnail_data(self, hist_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        self.__pixmap_hist_thumbnail_data[hist_id] = QtGui.QPixmap(thumb_filepath.as_posix())

    def update_pixmap_thumbnail_data(self, hkey_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        thumb_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
        if hkey_id in self.__pixmap_thumbnail_data:
            self.__pixmap_thumbnail_data.update({hkey_id: thumb_pixmap})
        else:
            self.__pixmap_thumbnail_data[hkey_id] = thumb_pixmap

    def update_pixmap_hist_thumbnail_data(self, hist_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        thumb_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
        if hist_id in self.__pixmap_hist_thumbnail_data:
            self.__pixmap_hist_thumbnail_data.update({hist_id: thumb_pixmap})
        else:
            self.__pixmap_hist_thumbnail_data[hist_id] = thumb_pixmap

    def make_pixmap_ihda_data(self, icon_info=None):
        if icon_info is None:
            return
        with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
            for info in icon_info:
                hkey_id, icon_lst = info
                self.__pixmap_ihda_data[hkey_id] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst)

    def make_pixmap_cate_data(self, cate_lst=None):
        if cate_lst is None:
            return
        net_dirname = public.Name.Icons.networks
        root_name = public.Name.Icons.root
        with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
            self.__pixmap_cate_data[root_name] = self.__get_icon_from_zipfile(
                zip_fp=zip_fp, icon_lst=[net_dirname, root_name])
            for cate in map(lambda x: x.lower(), cate_lst):
                icon_lst = [net_dirname, cate]
                self.__pixmap_cate_data[cate] = self.__get_icon_from_zipfile(
                    zip_fp=zip_fp, icon_lst=icon_lst)

    def make_pixmap_thumbnail_data(self, all_data=None):
        for data in all_data:
            hkey_id = data.get(public.Key.hda_id)
            thumb_filepath = data.get(public.Key.thumbnail_dirpath) / data.get(public.Key.thumbnail_filename)
            if not thumb_filepath.exists():
                thumbnail_pixmap = self.__default_pixmap
            else:
                thumbnail_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
            self.__pixmap_thumbnail_data[hkey_id] = thumbnail_pixmap

    def make_pixmap_hist_thumbnail_data(self, all_data=None):
        for data in all_data:
            hist_id = data.get(public.Key.History.hist_id)
            thumb_filepath = data.get(public.Key.History.thumb_dirpath) / data.get(public.Key.History.thumb_filename)
            if not thumb_filepath.exists():
                thumbnail_pixmap = self.__default_pixmap
            else:
                thumbnail_pixmap = QtGui.QPixmap(thumb_filepath.as_posix())
            self.__pixmap_hist_thumbnail_data[hist_id] = thumbnail_pixmap

    def get_houdini_icon(self, icon_lst=None):
        with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
            return self.__get_icon_from_zipfile(zip_fp=zip_fp, icon_lst=icon_lst)

    def get_category_icon(self, category=None):
        with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
            icon_lst = [public.Name.Icons.networks, category]
            return self.__get_icon_from_zipfile(zip_fp=zip_fp, icon_lst=icon_lst)

    def __get_icon_from_zipfile(self, zip_fp=None, icon_lst=None):
        if icon_lst is None:
            return QtGui.QPixmap(':/main/icons/blank.png')
        icon_file_ext = public.Extensions.houdini_icons
        icon_filepath = '/'.join([str(icon_lst[0]), str(icon_lst[1]) + icon_file_ext])
        try:
            contents = zip_fp.read(icon_filepath)
            img = QtGui.QImage.fromData(contents)
            pixmap = QtGui.QPixmap.fromImage(img)
            return pixmap
        except (KeyError, RuntimeError) as err:
            icon_map = self.__icons_map.get('_'.join(icon_lst))
            if icon_map is None:
                icon_filepath = '/'.join([public.Name.Icons.desktop, public.Name.Icons.blank + icon_file_ext])
            else:
                icon_map_lst = map(lambda x: str(x.strip('_')), self.__pattern_icon_map.match(icon_map).groups())
                icon_filepath = '/'.join([icon_map_lst[0], icon_map_lst[1] + icon_file_ext])
            try:
                contents = zip_fp.read(icon_filepath)
                img = QtGui.QImage.fromData(contents)
                pixmap = QtGui.QPixmap.fromImage(img)
                return pixmap
            except (KeyError, RuntimeError) as err:
                if icon_lst[0].lower() == public.Type.chop:
                    return QtGui.QPixmap(':/main/icons/chan.png')
                return QtGui.QPixmap(':/main/icons/blank.png')

    def __icons_mapping_from_file(self):
        if not self.is_valid_zipfile():
            if not self.__zip_filepath.exists():
                log_handler.LogHandler.log_msg(method=warning, msg='icons mapping file does not exist')
            elif not is_zipfile(self.__zip_filepath.as_posix()):
                log_handler.LogHandler.log_msg(method=warning, msg='it\'s not a zip file')
            else:
                log_handler.LogHandler.log_msg(method=warning, msg='unknown zip file error')
            return None
        split_str = ':='
        pattern_split = compile(r'{0}'.format(split_str))
        pattern_del = compile(r'[\s;]')
        icons_dict = dict()
        with ZipFile(self.__zip_filepath.as_posix()) as zip_fp:
            with zip_fp.open(public.Name.Icons.filename, 'r') as fp:
                for line in fp:
                    if pattern_split.search(line) is not None:
                        lst = map(lambda x: pattern_del.sub('', x), line.split('{0}'.format(split_str)))
                        icons_dict[lst[0]] = lst[1]
        if len(icons_dict):
            return icons_dict
        return None

    def is_valid_zipfile(self):
        if self.__zip_filepath.exists():
            if is_zipfile(self.__zip_filepath.as_posix()):
                return True
        return False
