# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.27 22:57:06
# modified date:    
# description:

import os
import shlex
import logging
from imp import reload
from shutil import rmtree
from site import addsitedir
from urllib2 import urlopen, URLError
from threading import Thread
from webbrowser import open_new
from subprocess import Popen, PIPE

import public
from libs import log_handler

reload(public)
addsitedir(public.Paths.python_packages_dirpath.as_posix())

import pathlib2

reload(log_handler)


class IHDASystem(object):
    def __init__(self):
        pass

    @staticmethod
    def open_with_terminal(cmd=''):
        return "gnome-terminal -e 'bash -c \"{command}; cd $OLDPATH; exec bash\"' &".format(command=cmd)

    @staticmethod
    def open_folder(dirpath=None):
        if dirpath is None:
            return
        assert isinstance(dirpath, pathlib2.Path)
        if not dirpath.is_dir():
            dirpath = dirpath.parent
        if not dirpath.is_dir():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='iHDA directory does not exists ({0})'.format(dirpath))
            return
        if public.is_windows():
            os.startfile(dirpath.as_posix())
        elif public.is_linux():
            os.system('xdg-open {0}'.format(dirpath.as_posix()))
        elif public.is_mac():
            os.system('open {0}'.format(dirpath.as_posix()))
        else:
            log_handler.LogHandler.log_msg(method=logging.error, msg='unknown OS System')
            return
        log_handler.LogHandler.log_msg(method=logging.info, msg='open HDA folder.')

    @staticmethod
    def remove_dir(dirpath=None, verbose=True):
        assert isinstance(dirpath, pathlib2.Path)
        if dirpath.exists() and dirpath.is_dir():
            try:
                rmtree(dirpath.as_posix())
                if verbose:
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg='{0} directory was deleted'.format(dirpath.as_posix()))
                return True
            except OSError as err:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='thumbnail or video files in "{0}" folder are open and cannot be performed'.format(
                        dirpath.as_posix()))
                return False
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg='{0} directory has already been deleted or does not exist'.format(dirpath.as_posix()))
        return False

    @staticmethod
    def remove_file(filepath=None, verbose=True):
        assert isinstance(filepath, pathlib2.Path)
        if filepath.exists() and filepath.is_file():
            try:
                filepath.unlink()
                if verbose:
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg='{0} file was deleted'.format(filepath.as_posix()))
                return True
            except Exception as err:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='"{0}" file is open and cannot be deleted'.format(filepath.as_posix()))
                return False
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg='{0} file has already been deleted or does not exist'.format(filepath.as_posix()))
        return False

    @staticmethod
    def rename_file(src_filepath=None, dst_filepath=None, verbose=True):
        assert isinstance(src_filepath, pathlib2.Path)
        assert isinstance(dst_filepath, pathlib2.Path)
        if (not src_filepath.exists() or not src_filepath.is_file()):
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='"{0}" file does not exist or is not in file format'.format(src_filepath.as_posix()))
            return False
        if dst_filepath.exists():
            is_del = IHDASystem.remove_file(filepath=dst_filepath, verbose=verbose)
            if not is_del:
                if verbose:
                    log_handler.LogHandler.log_msg(
                        method=logging.error,
                        msg='"{0}" file is open and cannot be deleted'.format(dst_filepath.as_posix()))
                return False
        try:
            src_filepath.rename(dst_filepath)
            if verbose:
                log_handler.LogHandler.log_msg(method=logging.info, msg='Finished renaming the file')
            return True
        except Exception as err:
            log_handler.LogHandler.log_msg(method=logging.error, msg='Failed to rename file')
        return False

    @staticmethod
    def is_network_connected():
        try:
            urlopen('http://216.58.192.142', timeout=1)
            return True
        except URLError as err:
            return False

    @staticmethod
    def open_browser(url=None):
        return open_new(url)

    @staticmethod
    def open_hipfile_using_thread(hip_filepath=None):
        if hip_filepath is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='the value of the houdini file path is null')
            return
        houfx_cmd = public.Paths.houdinifx_cmd
        assert isinstance(hip_filepath, pathlib2.Path)
        assert isinstance(houfx_cmd, pathlib2.Path)
        if not hip_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='"{0}" file not found'.format(hip_filepath.as_posix()))
            return
        if not houfx_cmd.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='houdini executable cannot be found')
            return
        log_handler.LogHandler.log_msg(method=logging.info, msg='"{0}" file open'.format(hip_filepath.as_posix()))
        t = Thread(target=IHDASystem.open_file_with_houdini, args=(hip_filepath, houfx_cmd))
        t.daemon = True
        t.start()

    @staticmethod
    def open_file_with_houdini(hip_filepath=None, houfx_cmd=None):
        cmd = '{0} {1}'.format(houfx_cmd.as_posix(), hip_filepath.as_posix())
        result = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
        out, err = result.communicate()
        out = out.decode('utf8')
        exitcode = result.returncode
        if exitcode != 0:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg='{0}, {1}, {2}'.format(exitcode, out.decode('utf8'), err.decode('utf8')))
            return
        return exitcode


if __name__ == '__main__':
    pass
