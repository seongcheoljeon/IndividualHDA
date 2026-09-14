"""SideFX asset expansion on the GUI thread, followed by pure file comparison."""

from __future__ import annotations
import difflib
import hashlib
from pathlib import Path
from typing import Any


def expand_asset(path: Path, destination: Path) -> dict[str, str]:
    import hou
    from PySide6.QtCore import QCoreApplication, QThread

    app = QCoreApplication.instance()
    if app is not None and QThread.currentThread() != app.thread():
        raise RuntimeError("HOM inspection must run on the GUI thread")
    if not path.is_file():
        raise FileNotFoundError(path)
    definitions = hou.hda.definitionsInFile(str(path))
    if not definitions:
        raise ValueError("File contains no asset definitions")
    # parmTemplateGroup() requires an installed type in Houdini 21. Read the
    # saved interface section instead so comparison never installs definitions.
    parameters = {}
    for definition in definitions:
        section = definition.sections().get("DialogScript")
        parameters[definition.nodeTypeName()] = (
            section.contents() if section is not None else "[No DialogScript section]"
        )
    hou.hda.expandToDirectory(str(path), str(destination))
    return parameters


def compare_expanded(
    left: Path,
    right: Path,
    left_meta: dict[str, Any],
    right_meta: dict[str, Any],
    left_parms: dict[str, str],
    right_parms: dict[str, str],
) -> str:
    report = ["VERSION METADATA"]
    for field in (
        "version",
        "comment",
        "note",
        "node_type_name",
        "node_category",
        "houdini_version",
        "node_old_path",
    ):
        a, b = left_meta.get(field), right_meta.get(field)
        if a != b:
            report.append(f"{field}: {a!r} → {b!r}")
    report.append("\nPARAMETER INTERFACE")
    report.extend(
        difflib.unified_diff(
            "\n".join(
                f"{key}\n{value}" for key, value in sorted(left_parms.items())
            ).splitlines(),
            "\n".join(
                f"{key}\n{value}" for key, value in sorted(right_parms.items())
            ).splitlines(),
            fromfile="Left",
            tofile="Right",
            lineterm="",
        )
    )
    report.append("\nNODE CONTENTS AND SECTIONS")
    files_left = {
        p.relative_to(left).as_posix(): p for p in left.rglob("*") if p.is_file()
    }
    files_right = {
        p.relative_to(right).as_posix(): p for p in right.rglob("*") if p.is_file()
    }
    for name in sorted(files_left.keys() | files_right.keys()):
        if name not in files_left or name not in files_right:
            report.append(("Added: " if name in files_right else "Removed: ") + name)
            continue
        a, b = files_left[name].read_bytes(), files_right[name].read_bytes()
        if a == b:
            continue
        report.append(f"Changed: {name}")
        if len(a) + len(b) <= 2 * 1024 * 1024 and b"\0" not in a + b:
            lines = list(
                difflib.unified_diff(
                    a.decode("utf-8", errors="replace").splitlines(),
                    b.decode("utf-8", errors="replace").splitlines(),
                    fromfile="Left/" + name,
                    tofile="Right/" + name,
                    lineterm="",
                )
            )
            report.extend(lines[:2000])
            if len(lines) > 2000:
                report.append("[Diff truncated to 2000 lines for this section]")
        else:
            report.append(
                f"Binary/large section: {len(a)} → {len(b)} bytes; SHA256 {hashlib.sha256(a).hexdigest()} → {hashlib.sha256(b).hexdigest()}"
            )
    return "\n".join(report)
