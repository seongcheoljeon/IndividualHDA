# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.17 17:58:39
# modified date:    
# description:      iHDA data import & export

import zipfile
import logging
import shutil
from imp import reload
from site import addsitedir

from PySide2.QtWidgets import QFileDialog
from PySide2.QtCore import QDateTime

import public
reload(public)
addsitedir(public.Paths.python_packages_dirpath.as_posix())

# third-party modules
import pathlib2

from libs import log_handler, ihda_system

reload(log_handler)
reload(ihda_system)


class DataStream(object):
    def __init__(self, userid=None, hda_base_dirpath=None, data_dirpath=None, parent=None):
        assert isinstance(hda_base_dirpath, pathlib2.Path)
        assert isinstance(data_dirpath, pathlib2.Path)
        self.__user = userid
        self.__hda_base_dirpath = hda_base_dirpath
        self.__data_dirpath = data_dirpath
        self.__parent = parent

    # 현재 데이터 백업하는 함수
    def create_backup_file(self):
        try:
            backup_dirpath = self.__data_dirpath / public.Name.IHDAData.backup_dirname
            if not backup_dirpath.exists():
                backup_dirpath.mkdir(parents=True)
            datetime_str = QDateTime.currentDateTime().toString('yyyy_MM_dd_hh_mm_ss')
            backup_filename = 'bak_data_{0}_{1}{2}'.format(
                datetime_str, public.Name.IHDAData.filename, public.Extensions.zip_file)
            backup_filepath = backup_dirpath / backup_filename
            tmp_bak_filepath = public.Paths.tmp_dirpath / backup_filename
            self.__compress_ihda_data(
                data_filepath=tmp_bak_filepath, is_print_log=False)
            ihda_system.IHDASystem.rename_file(
                src_filepath=tmp_bak_filepath, dst_filepath=backup_filepath, verbose=False)
            return backup_filepath
        except Exception as err:
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            log_handler.LogHandler.log_msg(method=logging.error, msg='creation of backup file failed')
            return None

    # .iHDAData/houdini 디렉토리 삭제하는 함수
    @staticmethod
    def remove_ihda_houdini_dir(hda_base_dirpath=None, data_dirpath=None):
        is_del = False
        old_dat_dirpath = data_dirpath / public.Name.houdini_name
        if old_dat_dirpath.exists():
            is_del = ihda_system.IHDASystem.remove_dir(dirpath=old_dat_dirpath, verbose=False)
        # 삭제 실패면
        if not is_del:
            log_handler.LogHandler.log_msg(method=logging.error, msg='the folder cannot be deleted')
            return False
        if not hda_base_dirpath.exists():
            hda_base_dirpath.mkdir(parents=True)
        return True

    def import_ihda_data(self):
        # 사용중인 DB 파일이 없다면 종료
        db_filepath = self.__data_dirpath / public.SQLite.db_filename
        if not db_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='DB file does not exist')
            return
        if self.__user is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='user information does not exist')
            return None
        start_dirpath = pathlib2.Path.home().as_posix()
        filter_str = 'iHDA file (*.zip *.ZIP)'
        data_filepath, _ = QFileDialog.getOpenFileName(
            self.__parent, 'Select Import iHDA Data File', start_dirpath, filter_str)
        if not len(data_filepath):
            return None
        data_filepath = pathlib2.Path(data_filepath)
        tmp_filepath = public.Paths.tmp_dirpath / data_filepath.name
        if tmp_filepath.exists():
            ihda_system.IHDASystem.remove_file(filepath=tmp_filepath, verbose=False)
        shutil.copyfile(data_filepath.as_posix(), tmp_filepath.as_posix())
        is_error = False
        # 후디니 temp 디렉토리에 압축 해제하여 임포트 가능한 데이터인지 확인 절차
        hou_tmp_dirpath = public.Paths.tmp_ihda_dirpath
        # 만약 존재하면 삭제 후 다시 생성
        if hou_tmp_dirpath.exists():
            shutil.rmtree(hou_tmp_dirpath.as_posix(), ignore_errors=True)
        if not hou_tmp_dirpath.exists():
            hou_tmp_dirpath.mkdir(parents=True)
        #
        with zipfile.ZipFile(tmp_filepath.as_posix()) as zip_fp:
            zip_namelist = zip_fp.namelist()
            if not len(zip_namelist):
                log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA data is empty')
                tmp_filepath.unlink()
                return None
            _db_fname = public.SQLite.db_filename
            if _db_fname not in zip_namelist:
                tmp_filepath.unlink()
                log_handler.LogHandler.log_msg(method=logging.error, msg='it\'s not iHDA data')
                return None
            info = zip_fp.getinfo(_db_fname)
            qdatetime = QDateTime(*info.date_time)
            log_handler.LogHandler.log_msg(
                method=logging.info,
                msg='time the iHDA data was created: {0}'.format(qdatetime.toString('yyyy-MM-dd hh:mm:ss')))
            log_handler.LogHandler.log_msg(method=logging.debug, msg='*** importing iHDA data ***')
            for dat in sorted(zip_namelist):
                zip_fp.extract(dat, hou_tmp_dirpath.as_posix())
                log_handler.LogHandler.log_msg(method=logging.info, msg=dat)
        # 악축 파일 삭제
        if tmp_filepath.exists():
            tmp_filepath.unlink()
        if is_error:
            log_handler.LogHandler.log_msg(method=logging.error, msg='decompression failed')
            return
        # houdini temp에 압축 푼 가져오려는 db 파일 경로
        hou_tmp_db_filepath = hou_tmp_dirpath / public.SQLite.db_filename
        if not hou_tmp_db_filepath.exists():
            if hou_tmp_dirpath.exists():
                shutil.rmtree(hou_tmp_dirpath.as_posix(), ignore_errors=True)
            return
        if public.SQLite.tmp_db_filepath.exists():
            is_done = ihda_system.IHDASystem.remove_file(filepath=public.SQLite.tmp_db_filepath, verbose=False)
            if not is_done:
                return
        # db파일은 houdini_temp로 옮긴다
        is_done = ihda_system.IHDASystem.rename_file(
            src_filepath=hou_tmp_db_filepath, dst_filepath=public.SQLite.tmp_db_filepath)
        if not is_done:
            return
        backup_filepath = self.create_backup_file()
        if backup_filepath is None:
            return
        if not public.SQLite.tmp_db_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='DB file was not copied')
            return
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='*** iHDA data import is complete ***')
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='backup path of existing iHDA data: {0}'.format(backup_filepath.as_posix()))
        log_handler.LogHandler.log_msg(method=logging.debug, msg='restart iHDA app')
        return backup_filepath

    def export_ihda_data(self):
        if self.__hda_base_dirpath is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA data directory is not set')
            return None
        if not self.__hda_base_dirpath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA data directory does not exist')
            return None
        start_dirpath = pathlib2.Path.home().as_posix()
        data_dirpath = QFileDialog.getExistingDirectory(
            self.__parent, 'Select Export Directory', start_dirpath)
        if not len(data_dirpath):
            return None
        datetime_str = QDateTime.currentDateTime().toString('yyyy_MM_dd_hh_mm_ss')
        data_dirpath = pathlib2.Path(data_dirpath)
        data_filename = '{0}_{1}{2}'.format(
            datetime_str, public.Name.IHDAData.filename, public.Extensions.zip_file)
        data_filepath = data_dirpath / data_filename
        if data_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA export data already exists')
            return None
        self.__compress_ihda_data(data_filepath=data_filepath)
        return data_dirpath

    def __compress_ihda_data(self, data_filepath=None, is_print_log=True):
        db_filepath = self.__data_dirpath / public.SQLite.db_filename
        if not db_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='DB file does not exist')
            return
        if is_print_log:
            log_handler.LogHandler.log_msg(method=logging.debug, msg='*** exporting iHDA data to the outside ***')
        with zipfile.ZipFile(data_filepath.as_posix(), 'w') as zip_fp:
            for filepath in sorted(self.__hda_base_dirpath.rglob('*')):
                if not filepath.is_file():
                    continue
                rel_filepath = filepath.relative_to(self.__hda_base_dirpath)
                zip_fp.write(filepath.as_posix(), rel_filepath.as_posix())
                if is_print_log:
                    log_handler.LogHandler.log_msg(method=logging.info, msg=rel_filepath.as_posix())
            rel_filepath = db_filepath.relative_to(db_filepath.parent)
            zip_fp.write(db_filepath.as_posix(), rel_filepath.as_posix())
            if is_print_log:
                log_handler.LogHandler.log_msg(method=logging.info, msg=rel_filepath.as_posix())
        if is_print_log:
            log_handler.LogHandler.log_msg(method=logging.debug, msg='*** iHDA data export is complete ***')


if __name__ == '__main__':
    pass
