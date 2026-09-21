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
    def show_draft(self, note: str, tags: Sequence[str]) -> None: ...
    def show_state(self, note_dirty: bool, tag_dirty: bool, saving: bool) -> None: ...
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
    tags: list[str]
    saved_note: str
    saved_tags: list[str]

    @property
    def note_dirty(self) -> bool:
        return self.note != self.saved_note

    @property
    def tags_dirty(self) -> bool:
        return self.tags != self.saved_tags

    @property
    def dirty(self) -> bool:
        return self.note_dirty or self.tags_dirty

    @property
    def dirty_fields(self) -> tuple[Field, ...]:
        fields: list[Field] = []
        if self.note_dirty:
            fields.append("note")
        if self.tags_dirty:
            fields.append("tag")
        return tuple(fields)


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
        # Autosave: leaving an asset saves it, and a save that lands while newer
        # edits exist is followed by another one. Off by default so explicit-save
        # callers (and tests of them) see exactly the writes they asked for.
        self.autosave = False

    def change_gateway(
        self, gateway: MetadataGateway | None, *, preserve_drafts: bool = False
    ) -> None:
        self._generation += 1
        self._gateway = gateway
        self._saving = False
        if not preserve_drafts:
            self._drafts.clear()
            self._asset_id = None
            self._view.show_draft("", [])
        self._state()

    def select(
        self, asset_id: int | None, note: str = "", tags: Sequence[str] = ()
    ) -> None:
        if self.autosave and self._asset_id not in (None, asset_id):
            self.save_pending()
        self._asset_id = asset_id
        if asset_id is None:
            self._view.show_draft("", [])
        else:
            draft = self._drafts.get(asset_id)
            if draft is None or not draft.dirty:
                draft = Draft(note, list(tags), note, list(tags))
                self._drafts[asset_id] = draft
            self._view.show_draft(draft.note, draft.tags)
        self._state()

    def edit(self, note: str, tags: Sequence[str]) -> None:
        if self._asset_id is not None:
            draft = self._drafts[self._asset_id]
            draft.note, draft.tags = note, list(tags)
        self._state()

    def forget(self, asset_id: int) -> None:
        self._drafts.pop(asset_id, None)
        if self._asset_id == asset_id:
            self.select(None)

    def _state(self) -> None:
        # Per field: the note and the tags have their own indicator, so one
        # "dirty" flag cannot say which one is unsaved.
        draft = self._drafts.get(self._asset_id) if self._asset_id is not None else None
        self._view.show_state(
            bool(draft and draft.note_dirty),
            bool(draft and draft.tags_dirty),
            self._saving,
        )

    def save(self, field: Field) -> None:
        """Explicit save of one field of the selected asset."""
        if self._asset_id is None:
            return
        self._save(self._asset_id, (field,))

    def save_pending(self) -> None:
        """Save whatever is dirty: the selected asset first, then any other draft."""
        candidates = [self._asset_id] if self._asset_id is not None else []
        candidates += [
            asset_id for asset_id in self._drafts if asset_id not in candidates
        ]
        for asset_id in candidates:
            fields = self._drafts[asset_id].dirty_fields
            if fields:
                self._save(asset_id, fields)
                return

    def _save(self, asset_id: int, fields: Sequence[Field]) -> None:
        gateway = self._gateway
        if self._saving or gateway is None or not fields:
            return
        self.write_generation += 1
        draft = self._drafts[asset_id]
        generation = self._generation
        note, tags = draft.note, normalize_tags(draft.tags)
        submitted_note, submitted_tags = draft.note, list(draft.tags)

        def operation() -> None:
            if "note" in fields:
                gateway.set_note(asset_id, note)
            if "tag" in fields:
                gateway.set_tags(asset_id, tags)

        def finished(error: Exception | None) -> None:
            if generation != self._generation:
                return
            self._saving = False
            if error is not None:
                self._view.show_error(str(error))
            elif self._drafts.get(asset_id) is draft:
                if "note" in fields:
                    draft.saved_note = submitted_note
                    self._view.saved(asset_id, "note", note)
                if "tag" in fields:
                    draft.saved_tags = submitted_tags
                    self._view.saved(asset_id, "tag", tags)
            self._state()
            # Only a success continues the chain: an error (a trashed asset, an
            # offline library) must not loop; the next edit re-arms autosave.
            if error is None and self.autosave:
                self.save_pending()

        self._saving = True
        self._state()
        try:
            if not self._executor.submit(operation, finished):
                finished(
                    RuntimeError("A save is already in progress. Try again shortly.")
                )
        except Exception as error:
            finished(error)
