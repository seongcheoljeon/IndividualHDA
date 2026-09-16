"""Model action availability, independent of Qt and Ollama transport."""

from __future__ import annotations

from collections.abc import Set
from dataclasses import dataclass


def installed_name(name: str) -> str:
    return name if ":" in name else f"{name}:latest"


@dataclass(frozen=True)
class ModelActions:
    installed: bool
    download: bool
    use: bool
    remove: bool
    download_default: bool


class LocalModelsPresenter:
    def actions(
        self,
        model: str,
        installed: Set[str],
        connected: bool,
        busy: bool,
        removable: bool,
    ) -> ModelActions:
        exists = bool(model) and installed_name(model) in installed
        return ModelActions(
            exists,
            bool(model) and connected and not busy,
            exists and not busy,
            removable and not busy,
            bool(model) and not exists and not busy,
        )
