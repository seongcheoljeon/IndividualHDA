"""Name validation and rename preview, independent of Qt."""

from __future__ import annotations

from typing import Protocol

from libs.asset_names import NameValidation as NameValidation
from libs.asset_names import validate_name as validate_name


class RenameView(Protocol):
    def show_validation(self, validation: NameValidation) -> None: ...


class RenamePresenter:
    def __init__(self, view: RenameView) -> None:
        self._view = view
        self.validation = NameValidation("", "Nothing was entered.")

    def edit(self, text: str, old_name: str) -> None:
        self.validation = validate_name(text, old_name)
        self._view.show_validation(self.validation)
