"""Trash commands depend only on the storage capabilities they use."""

from __future__ import annotations

from libs.contracts import AssetDeletionRepository, HistoryDeletionRepository


def delete_asset(repository: AssetDeletionRepository, asset_id: int) -> None:
    repository.trash_asset(asset_id)


def delete_history(
    repository: HistoryDeletionRepository, asset_id: int, history_id: int
) -> None:
    repository.trash_history(asset_id, history_id)
