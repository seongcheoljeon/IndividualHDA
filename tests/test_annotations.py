"""Keep annotations on maintained code when adding new features."""

from __future__ import annotations

import ast
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_maintained_function_signatures_are_annotated() -> None:
    missing: list[str] = []
    sources = {
        str(path.relative_to(ROOT)): path.read_text(encoding="utf-8")
        for path in ROOT.rglob("*.py")
        if not any(
            part in (".venv", ".git", "tests") for part in path.relative_to(ROOT).parts
        )
        and not path.name.endswith(("_ui.py", "_rc.py"))
    }
    panel = ROOT / "python_panels" / "individualHDA.pypanel"
    sources[panel.name] = ET.parse(panel).findtext(".//script") or ""
    for filename, source in sources.items():
        # Also rejects syntax introduced after Houdini 21's Python 3.11.
        tree = ast.parse(source, filename=filename, feature_version=(3, 11))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.returns is None:
                missing.append(f"{filename}:{node.lineno}: {node.name} return")
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            args += [
                arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None
            ]
            for arg in args:
                if arg.arg not in ("self", "cls") and arg.annotation is None:
                    missing.append(f"{filename}:{node.lineno}: {node.name}({arg.arg})")
    assert not missing, "\n".join(missing)
