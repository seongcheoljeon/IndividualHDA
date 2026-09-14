from __future__ import annotations

import errno
import logging

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.27 22:57:06
# modified date:
# description:
import os
import pathlib
import tempfile
from shutil import copy2, rmtree
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from webbrowser import open_new

import public
from libs import log_handler


class IHDASystem:
    def __init__(self) -> None:
        pass

    @staticmethod
    def open_with_terminal(cmd: str = "") -> Any:
        return f"gnome-terminal -e 'bash -c \"{cmd}; cd $OLDPATH; exec bash\"' &"

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
                msg=f"iHDA directory does not exists ({dirpath})",
            )
            return
        if public.is_windows():
            os.startfile(dirpath.as_posix())  # type: ignore[attr-defined]  # Windows only
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
                        msg=f"{dirpath.as_posix()} directory was deleted",
                    )
                return True
            except OSError:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg=f'thumbnail or video files in "{dirpath.as_posix()}" folder are open and cannot be performed',
                )
                return False
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg=f"{dirpath.as_posix()} directory has already been deleted or does not exist",
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
                        msg=f"{filepath.as_posix()} file was deleted",
                    )
                return True
            except Exception:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg=f'"{filepath.as_posix()}" file is open and cannot be deleted',
                )
                return False
        if verbose:
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg=f"{filepath.as_posix()} file has already been deleted or does not exist",
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
                    msg=f'"{src_filepath.as_posix()}" file does not exist or is not in file format',
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
                descriptor, staged_name = tempfile.mkstemp(
                    prefix=".ihda-move-", dir=dst_filepath.parent
                )
                os.close(descriptor)
                staged = pathlib.Path(staged_name)
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
        except URLError:
            return False

    @staticmethod
    def open_browser(url: str | None = None) -> Any:
        return open_new(url or "")

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
                msg=f'"{hip_filepath.as_posix()}" file not found',
            )
            return
        if not houfx_cmd.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="houdini executable cannot be found"
            )
            return
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f'"{hip_filepath.as_posix()}" file open'
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
