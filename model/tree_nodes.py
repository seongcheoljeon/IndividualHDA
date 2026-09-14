"""Tree node shared by the category, record and inside-node models."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore


class Node(QtCore.QObject):
    def __init__(
        self,
        node_name: str | None = None,
        node_depth: int | None = None,
        parent: Node | None = None,
    ) -> None:
        super().__init__()
        self.__name = node_name
        self.__depth = node_depth
        self._parent = parent
        self._children: list[Node] = []
        self.setParent(parent)

    def name(self) -> str | None:
        return self.__name

    def depth(self) -> int | None:
        return self.__depth

    def parent(self) -> Node | None:
        return self._parent

    def child(self, row: int) -> Any:
        return self._children[row]

    def insert_child(self, position: Any, child: Node) -> bool:
        if position < 0 or position > len(self._children):
            return False
        self._children.insert(position, child)
        child._parent = self
        return True

    def setParent(self, parent: Node | None) -> None:  # type: ignore[override]
        if parent is not None:
            self._parent = parent
            self._parent.append_child(self)
        else:
            self._parent = None

    def append_child(self, child: Node) -> None:
        self._children.append(child)

    def child_at_row(self, row: int) -> Node:
        return self._children[row]

    def row_of_child(self, child: Node) -> int:
        for idx, item in enumerate(self._children):
            if child == item:
                return idx
        return -1

    def remove_child(self, row: int) -> bool:
        value = self._children[row]
        self._children.remove(value)
        return True

    def __len__(self) -> int:
        return len(self._children)
