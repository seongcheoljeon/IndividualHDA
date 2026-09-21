"""Line and tag differences for the team conflict review; stdlib only."""

from __future__ import annotations

from collections.abc import Sequence
from difflib import SequenceMatcher
from html import escape

# (tag, left line, right line); tag is one of equal / replace / delete / insert.
LineOp = tuple[str, str, str]


def line_ops(left: str, right: str) -> list[LineOp]:
    """Align two texts line by line; a replace pads the shorter side with ''."""
    a, b = left.splitlines(), right.splitlines()
    ops: list[LineOp] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(
        None, a, b, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            ops.extend(("equal", line, line) for line in a[i1:i2])
        elif tag == "delete":
            ops.extend(("delete", line, "") for line in a[i1:i2])
        elif tag == "insert":
            ops.extend(("insert", "", line) for line in b[j1:j2])
        else:
            lefts, rights = a[i1:i2], b[j1:j2]
            for k in range(max(len(lefts), len(rights))):
                ops.append(
                    (
                        "replace",
                        lefts[k] if k < len(lefts) else "",
                        rights[k] if k < len(rights) else "",
                    )
                )
    return ops


def render_html(ops: Sequence[LineOp], side: str, *, changed: str) -> str:
    """One side of the diff as HTML; changed lines get the ``changed`` background."""
    marks = {"left": {"delete", "replace"}, "right": {"insert", "replace"}}[side]
    rows = []
    for tag, left, right in ops:
        line = left if side == "left" else right
        text = escape(line) or "&nbsp;"
        style = f' style="background: {changed};"' if tag in marks else ""
        rows.append(f"<div{style}>{text}</div>")
    return "".join(rows)


def tag_diff(
    mine: Sequence[str], theirs: Sequence[str]
) -> tuple[list[str], list[str], list[str]]:
    """(only in mine, only in theirs, in both); case-insensitive, order kept."""
    mine_keys = {tag.casefold() for tag in mine}
    their_keys = {tag.casefold() for tag in theirs}
    added = [tag for tag in mine if tag.casefold() not in their_keys]
    removed = [tag for tag in theirs if tag.casefold() not in mine_keys]
    common = [tag for tag in mine if tag.casefold() in their_keys]
    return added, removed, common
