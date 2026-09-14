from __future__ import annotations

from typing import Any
import pathlib

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.27 22:57:06
# modified date:
# description:

import os
import errno
import tempfile
from shutil import copy2
import logging
from shutil import rmtree
from urllib.request import urlopen
from urllib.error import URLError
from threading import Thread
from webbrowser import open_new
from subprocess import Popen, DEVNULL

import public
from libs import log_handler


class IHDASystem(object):
    def __init__(self) -> None:
        pass

    @staticmethod
    def open_with_terminal(cmd: str = "") -> Any:
        return "gnome-terminal -e 'bash -c \"{command}; cd $OLDPATH; exec bash\"' &".format(
            command=cmd
        )

    @staticmethod
    def open_folder(dirpath: pathlib.Path | None = None) -> None:
        if dirpath is None:
            return
        assert isinstance(dirpath, pathlib.Path)
        if not dirpath.is_dir():
            dirpath = dirpath.parent
        if not dirpath.is_dir():
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="iHDA directory does not exists ({0})".format(dirpath),
            )
            return
        if public.is_windows():
            os.startfile(dirpath.as_posix())
        elif public.is_linux():
            Popen(["xdg-open", str(dirpath)])
        elif public.is_mac():
            Popen(["open", str(dirpath)])
        else:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="unknown OS System"
            )
            return
        log_handler.LogHandler.log_msg(method=logging.info, msg="open HDA folder.")

    @staticmethod
    def remove_dir(dirpath: pathlib.Path | None = None, verbose: bool = True) -> bool:
        assert isinstance(dirpath, pathlib.Path)
        if dirpath.exists() and dirpath.is_dir():
            try:
                rmtree(dirpath.as_posix())
                if verbose:
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg="{0} directory was deleted".format(dirpath.as_posix()),
                    )
                return True
            except OSError as err:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='thumbnail or video files in "{0}" folder are open and cannot be performed'.format(
                        dirpath.as_posix()
                    ),
                )
                return False
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="{0} directory has already been deleted or does not exist".format(
                    dirpath.as_posix()
                ),
            )
        return False

    @staticmethod
    def remove_file(filepath: pathlib.Path | None = None, verbose: bool = True) -> bool:
        assert isinstance(filepath, pathlib.Path)
        if filepath.exists() and filepath.is_file():
            try:
                filepath.unlink()
                if verbose:
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg="{0} file was deleted".format(filepath.as_posix()),
                    )
                return True
            except Exception as err:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='"{0}" file is open and cannot be deleted'.format(
                        filepath.as_posix()
                    ),
                )
                return False
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="{0} file has already been deleted or does not exist".format(
                    filepath.as_posix()
                ),
            )
        return False

    @staticmethod
    def rename_file(
        src_filepath: pathlib.Path | None = None,
        dst_filepath: pathlib.Path | None = None,
        verbose: bool = True,
    ) -> bool:
        assert isinstance(src_filepath, pathlib.Path)
        assert isinstance(dst_filepath, pathlib.Path)
        if not src_filepath.exists() or not src_filepath.is_file():
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='"{0}" file does not exist or is not in file format'.format(
                        src_filepath.as_posix()
                    ),
                )
            return False
        if src_filepath.resolve() == dst_filepath.resolve():
            return True
        try:
            try:
                src_filepath.replace(dst_filepath)
            except OSError as error:
                if error.errno != errno.EXDEV:
                    raise
                descriptor, staged = tempfile.mkstemp(
                    prefix=".ihda-move-", dir=dst_filepath.parent
                )
                os.close(descriptor)
                staged = pathlib.Path(staged)
                try:
                    copy2(src_filepath, staged)
                    staged.replace(dst_filepath)
                    src_filepath.unlink()
                finally:
                    staged.unlink(missing_ok=True)
            if verbose:
                logging.info("Finished renaming the file")
            return True
        except OSError as error:
            logging.error("Failed to rename file: %s", error)
            return False

    @staticmethod
    def is_network_connected() -> bool:
        try:
            urlopen("http://216.58.192.142", timeout=1)
            return True
        except URLError as err:
            return False

    @staticmethod
    def open_browser(url: str | None = None) -> Any:
        return open_new(url)

    @staticmethod
    def open_hipfile_using_thread(hip_filepath: pathlib.Path | None = None) -> None:
        if hip_filepath is None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="the value of the houdini file path is null"
            )
            return
        houfx_cmd = public.Paths.houdinifx_cmd
        assert isinstance(hip_filepath, pathlib.Path)
        assert isinstance(houfx_cmd, pathlib.Path)
        if not hip_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg='"{0}" file not found'.format(hip_filepath.as_posix()),
            )
            return
        if not houfx_cmd.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="houdini executable cannot be found"
            )
            return
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='"{0}" file open'.format(hip_filepath.as_posix())
        )
        t = Thread(
            target=IHDASystem.open_file_with_houdini, args=(hip_filepath, houfx_cmd)
        )
        t.daemon = True
        t.start()

    @staticmethod
    def open_file_with_houdini(
        hip_filepath: pathlib.Path | None = None, houfx_cmd: Any = None
    ) -> Any:
        return Popen(
            [str(houfx_cmd), str(hip_filepath)], stdout=DEVNULL, stderr=DEVNULL
        )


if __name__ == "__main__":
    pass
