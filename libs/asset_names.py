"""Shared asset-name validation; independent of dialogs and storage."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NameValidation:
    name: str
    error: str = ""

    @property
    def valid(self) -> bool:
        return not self.error


def validate_name(text: str, old_name: str) -> NameValidation:
    name = text.replace(" ", "_")
    error = ""
    if not name:
        error = "Nothing was entered."
    elif name == old_name:
        error = "Same as the current iHDA name."
    elif name.isdigit():
        error = "The name cannot consist entirely of numbers."
    elif name.startswith("_"):
        error = "The first character cannot be _(underscore)."
    elif name[0].isdigit():
        error = "The first character cannot be a number."
    elif name.startswith("."):
        error = "The first character cannot be .(full stop)."
    elif len(name) < 3:
        error = "Must be at least 3 characters."
    elif len(name) > 254:
        error = "Must be at most 254 characters."
    elif match := re.match(r"^[^a-zA-Z0-9_]", name):
        error = (
            f"The first character cannot contain special characters. ({match.group()})"
        )
    elif match := re.search(r"[^a-zA-Z0-9.\-_]", name):
        error = f"There should be no special characters between the names. ({match.group()})"
    return NameValidation(name, error)
