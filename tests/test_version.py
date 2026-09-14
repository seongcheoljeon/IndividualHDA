"""The version has one source of truth and every place that shows it agrees."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import public

ROOT = Path(__file__).resolve().parents[1]


def test_version_literals_agree() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    assert public.Value.current_ver == f"v{version}"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## {re.escape(version)}\b", changelog, re.M), (
        "CHANGELOG lacks the release heading"
    )
    import main

    assert main.__version__ == public.Value.current_ver


def test_package_file_has_no_machine_specific_path() -> None:
    package = json.loads(
        (ROOT / "packages" / "IndividualHDA.json").read_text(encoding="utf-8")
    )
    root = package["env"][0]["IHDA_ROOT"]
    assert root == "/path/to/IndividualHDA", root
    assert package["hpath"] == "$IHDA_ROOT" and package["enable"] is True
