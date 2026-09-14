"""Generated Designer modules must match their .ui sources (regenerate, never hand-edit)."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
UIC = shutil.which("pyside6-uic")


def _body(text: str) -> str:
    # Drop the leading comment block (our header + uic's version banner).
    lines = text.splitlines()
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).rstrip()


@pytest.mark.skipif(UIC is None, reason="pyside6-uic not on PATH")
@pytest.mark.parametrize("ui", sorted(ROOT.rglob("*.ui")), ids=lambda p: p.name)
def test_generated_module_matches_ui(ui: Path) -> None:
    committed = ui.with_name(ui.stem + "_ui.py").read_text(encoding="utf-8")
    generated = subprocess.run(
        [str(UIC), str(ui)], check=True, capture_output=True, text=True
    ).stdout
    if ui.parent != ROOT:  # widget packages import their rc module relatively
        generated = re.sub(
            r"^import (\w+_rc)$", r"from . import \1", generated, flags=re.M
        )
    assert _body(committed) == _body(generated), (
        f"{ui.name} drifted: run pyside6-uic and keep the relative rc import"
    )
