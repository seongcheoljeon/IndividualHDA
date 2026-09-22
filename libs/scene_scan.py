"""What a scan of the current HIP file found: plain data, no Houdini, no Qt.

``scan_ihda_nodes`` (libs/houdini/assets.py) walks the scene once and returns
only the nodes that are iHDA instances or have one below them. Models and tests
consume these records; nothing downstream needs ``hou``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class IhdaMark:
    """The identity an imported node carries in its comment."""

    hda_id: int
    name: str
    version: str


@dataclass(frozen=True)
class ScannedNode:
    path: str
    name: str
    type_name: str
    category: str
    description: str = ""
    icon_paths: tuple[str, ...] = ()
    created: str = ""
    modified: str = ""
    mark: IhdaMark | None = None
    children: tuple[ScannedNode, ...] = field(default_factory=tuple)


def count_marks(nodes: Iterable[ScannedNode]) -> int:
    """iHDA instances in the tree, at any depth."""
    total = 0
    for node in nodes:
        total += (node.mark is not None) + count_marks(node.children)
    return total


def marked_nodes(nodes: Iterable[ScannedNode]) -> list[ScannedNode]:
    """Every node with a mark, depth first."""
    found: list[ScannedNode] = []
    for node in nodes:
        if node.mark is not None:
            found.append(node)
        found.extend(marked_nodes(node.children))
    return found
