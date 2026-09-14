"""Portable FFmpeg commands; arguments never pass through a shell."""

from __future__ import annotations

from typing import Any
import pathlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import uuid


class FFmpegAPI:
    @staticmethod
    def executable(name: str, directory: str | Path | None = None) -> str:
        filename = name + (".exe" if os.name == "nt" else "")
        if directory:
            root = Path(directory)
            for candidate in (root / "bin" / filename, root / filename):
                if candidate.is_file() and (
                    os.name == "nt" or os.access(candidate, os.X_OK)
                ):
                    return str(candidate)
        result = shutil.which(filename)
        if result:
            return result
        raise FileNotFoundError(
            f"{filename} was not found in the configured directory or PATH"
        )

    @staticmethod
    def image_sequence_command(
        ffmpeg_dirpath: pathlib.Path | None,
        image_seq: str | Path | None,
        output: str | Path | None,
        sf: int | None,
        num_frame: int | None,
        fps: float = 25,
        meta_data: dict[str, str] | None = None,
    ) -> list[str]:
        if image_seq is None or output is None or sf is None or num_frame is None:
            raise ValueError("Image sequence, output and frame range are required")
        if num_frame <= 0 or fps <= 0:
            raise ValueError("Frame count and frame rate must be positive")
        command = [
            FFmpegAPI.executable("ffmpeg", ffmpeg_dirpath),
            "-nostdin",
            "-y",
            "-framerate",
            str(fps),
            "-start_number",
            str(int(sf)),
            "-i",
            str(image_seq),
        ]
        for key, value in (meta_data or {}).items():
            command.extend(["-metadata", f"{key}={value}"])
        command.extend(
            [
                "-frames:v",
                str(int(num_frame)),
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                str(output),
            ]
        )
        return command

    @staticmethod
    def make_image_seq_to_video(
        ffmpeg_dirpath: pathlib.Path | None = None,
        image_seq: str | Path | None = None,
        output: str | Path | None = None,
        sf: int | None = None,
        num_frame: int | None = None,
        fps: float = 25,
        meta_data: dict[str, str] | None = None,
    ) -> int:
        if output is None:
            raise ValueError("Video output path is required")
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(
            f".{output.stem}-{uuid.uuid4().hex}{output.suffix}"
        )
        try:
            result = subprocess.run(
                FFmpegAPI.image_sequence_command(
                    ffmpeg_dirpath, image_seq, temporary, sf, num_frame, fps, meta_data
                ),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                temporary.replace(output)
            else:
                logging.error("FFmpeg failed: %s", result.stderr[-8192:])
            return result.returncode
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def play_video(
        ffmpeg_dirpath: pathlib.Path | None = None,
        video_filepath: pathlib.Path | None = None,
    ) -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            [
                FFmpegAPI.executable("ffplay", ffmpeg_dirpath),
                "-autoexit",
                str(video_filepath),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def video_info(
        ffmpeg_dirpath: pathlib.Path | None = None,
        video_filepath: pathlib.Path | None = None,
    ) -> dict[str, Any] | None:
        try:
            result = subprocess.run(
                [
                    FFmpegAPI.executable("ffprobe", ffmpeg_dirpath),
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(video_filepath),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=True,
            )
            return json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            logging.warning("Cannot inspect media %s: %s", video_filepath, error)
            return None
