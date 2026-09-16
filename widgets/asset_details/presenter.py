"""Per-asset drafts and immutable saves; independent of Qt and storage adapters."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from libs.tags import normalize_tags

Field = Literal["note", "tag"]


class MetadataGateway(Protocol):
    def set_note(self, asset_id: int, note: str) -> None: ...
    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None: ...


class DetailsView(Protocol):
    def show_draft(self, note: str, tags: str) -> None: ...
    def show_state(self, dirty: bool, saving: bool) -> None: ...
    def show_error(self, message: str) -> None: ...
    def saved(self, asset_id: int, field: Field, value: str | list[str]) -> None: ...


class SaveExecutor(Protocol):
    def submit(
        self,
        operation: Callable[[], None],
        finished: Callable[[Exception | None], None],
    ) -> bool: ...


@dataclass
class Draft:
    note: str
    tags: str
    saved_note: str
    saved_tags: str

    @property
    def dirty(self) -> bool:
        return self.note != self.saved_note or self.tags != self.saved_tags


class AssetDetailsPresenter:
    def __init__(self, view: DetailsView, executor: SaveExecutor) -> None:
        self._view = view
        self._executor = executor
        self._gateway: MetadataGateway | None = None
        self._drafts: dict[int, Draft] = {}
        self._asset_id: int | None = None
        self._generation = 0
        self._saving = False
        self.write_generation = 0

    def change_gateway(
        self, gateway: MetadataGateway | None, *, preserve_drafts: bool = False
    ) -> None:
        self._generation += 1
        self._gateway = gateway
        self._saving = False
        if not preserve_drafts:
            self._drafts.clear()
            self._asset_id = None
            self._view.show_draft("", "")
        self._state()

    def select(
        self, asset_id: int | None, note: str = "", tags: Sequence[str] = ()
    ) -> None:
        self._asset_id = asset_id
        if asset_id is None:
            self._view.show_draft("", "")
        else:
            tag_text = " ".join(f"#{tag}" for tag in sorted(tags))
            draft = self._drafts.get(asset_id)
            if draft is None or not draft.dirty:
                draft = Draft(note, tag_text, note, tag_text)
                self._drafts[asset_id] = draft
            self._view.show_draft(draft.note, draft.tags)
        self._state()

    def edit(self, note: str, tags: str) -> None:
        if self._asset_id is not None:
            draft = self._drafts[self._asset_id]
            draft.note, draft.tags = note, tags
        self._state()

    def forget(self, asset_id: int) -> None:
        self._drafts.pop(asset_id, None)
        if self._asset_id == asset_id:
            self.select(None)

    def _state(self) -> None:
        draft = self._drafts.get(self._asset_id) if self._asset_id is not None else None
        self._view.show_state(bool(draft and draft.dirty), self._saving)

    def save(self, field: Field) -> None:
        gateway, asset_id = self._gateway, self._asset_id
        if self._saving or gateway is None or asset_id is None:
            return
        self.write_generation += 1
        draft = self._drafts[asset_id]
        generation = self._generation
        note, tags = draft.note, sorted(normalize_tags(draft.tags))
        submitted_text = draft.note if field == "note" else draft.tags

        def operation() -> None:
            if field == "note":
                gateway.set_note(asset_id, note)
            else:
                gateway.set_tags(asset_id, tags)

        def finished(error: Exception | None) -> None:
            if generation != self._generation:
                return
            self._saving = False
            if error is not None:
                self._view.show_error(str(error))
            elif self._drafts.get(asset_id) is draft:
                if field == "note":
                    draft.saved_note = submitted_text
                else:
                    draft.saved_tags = submitted_text
                self._view.saved(asset_id, field, note if field == "note" else tags)
            self._state()

        self._saving = True
        self._state()
        try:
            if not self._executor.submit(operation, finished):
                finished(
                    RuntimeError("A save is already in progress. Try again shortly.")
                )
        except Exception as error:
            finished(error)
