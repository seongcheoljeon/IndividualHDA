"""Exercise the contributor entry point in a fresh process and isolated settings."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_sample_panel_starts_and_closes_without_changing_user_settings(
    tmp_path: Path,
) -> None:
    settings = tmp_path / "user-settings"
    settings.mkdir()
    sentinel = settings / "sentinel.json"
    sentinel.write_text('{"keep": true}')
    environment = dict(
        os.environ, IHDA_CONFIG_DIR=str(settings), QT_QPA_PLATFORM="offscreen"
    )
    result = subprocess.run(
        [sys.executable, "-m", "tools.dev_app", "--smoke"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(settings.iterdir()) == [sentinel]
    assert sentinel.read_text() == '{"keep": true}'
