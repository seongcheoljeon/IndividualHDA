"""Run repository checks identically on Windows, macOS and Linux."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "suite", choices=("core", "qt", "server", "postgres", "all", "lint")
    )
    parser.add_argument("--coverage", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
    if args.suite == "lint":
        commands = [
            ("ruff", "check", "."),
            ("ruff", "format", "--check", "."),
            ("mypy",),
        ]
    else:
        command = ["pytest", "-q", "--suite", args.suite]
        if args.coverage:
            if args.suite != "all":
                parser.error("--coverage requires the full suite")
            command += [
                "--cov=" + name
                for name in (
                    "ihda_server",
                    "libs",
                    "model",
                    "view",
                    "widgets",
                    "main",
                    "public",
                    "ui_settings",
                )
            ]
            command += [
                "--cov-report=term",
                "--cov-report=xml",
                "--cov-fail-under=60",
                "--junitxml=pytest-report.xml",
            ]
        commands = [tuple(command)]
    for invocation in commands:
        result = subprocess.run(
            [sys.executable, "-m", *invocation], cwd=root, env=environment, check=False
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
