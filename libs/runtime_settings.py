"""Validated per-user operational defaults; independent of Qt and the host."""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Any

from libs.search_limits import (
    EXPLORER_PAGE_DEFAULT,
    EXPLORER_PAGE_MAX,
    TEAM_PAGE_DEFAULT,
    TEAM_PAGE_MAX,
)

RUNTIME_SETTINGS_KEY = "runtime"


@dataclass(frozen=True, slots=True)
class SettingSpec:
    label: str
    minimum: int
    maximum: int
    suffix: str
    description: str


RUNTIME_FIELDS = {
    "search_delay_ms": SettingSpec(
        "Browser search delay",
        1,
        5000,
        " ms",
        "Wait after typing before searching the browser and history.",
    ),
    "explorer_delay_ms": SettingSpec(
        "Explorer search delay",
        1,
        5000,
        " ms",
        "Wait after typing before searching Library Tools.",
    ),
    "sync_interval_seconds": SettingSpec(
        "Library refresh interval",
        1,
        300,
        " s",
        "How often to check the personal library for changes.",
    ),
    "team_timeout_seconds": SettingSpec(
        "Team request timeout",
        1,
        300,
        " s",
        "Socket timeout for team connections and file transfers.",
    ),
    "team_page_size": SettingSpec(
        "Team request page size",
        1,
        TEAM_PAGE_MAX,
        " items",
        "Assets fetched per server request; all pages still appear in the browser.",
    ),
    "explorer_page_size": SettingSpec(
        "Explorer page size",
        1,
        EXPLORER_PAGE_MAX,
        " items",
        "Assets fetched when loading the next Explorer page.",
    ),
    "maximum_node_batch": SettingSpec(
        "Maximum node batch",
        1,
        100,
        " nodes",
        "Maximum nodes registered or imported in one batch.",
    ),
    "warn_node_batch": SettingSpec(
        "Node batch warning",
        1,
        100,
        " nodes",
        "Ask for confirmation above this count; must not exceed the maximum.",
    ),
}


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    search_delay_ms: int = 200
    explorer_delay_ms: int = 250
    sync_interval_seconds: int = 10
    team_timeout_seconds: int = 30
    team_page_size: int = TEAM_PAGE_DEFAULT
    explorer_page_size: int = EXPLORER_PAGE_DEFAULT
    maximum_node_batch: int = 30
    warn_node_batch: int = 10

    def __post_init__(self) -> None:
        for name, spec in RUNTIME_FIELDS.items():
            value = getattr(self, name)
            if type(value) is not int or not spec.minimum <= value <= spec.maximum:
                raise ValueError(
                    f"{spec.label} must be an integer from {spec.minimum} to {spec.maximum}"
                )
        if self.warn_node_batch > self.maximum_node_batch:
            raise ValueError(
                "Node batch warning must not exceed the maximum node batch"
            )

    @classmethod
    def from_mapping(cls, value: Any) -> RuntimeSettings:
        defaults = cls()
        if value is None:
            return defaults
        if not isinstance(value, dict):
            logging.warning("Ignoring malformed runtime settings")
            return defaults
        values = {}
        for field in fields(cls):
            name = field.name
            fallback = getattr(defaults, name)
            candidate = value.get(name, fallback)
            spec = RUNTIME_FIELDS[name]
            if (
                type(candidate) is not int
                or not spec.minimum <= candidate <= spec.maximum
            ):
                logging.warning("Ignoring invalid runtime setting %s", name)
                candidate = fallback
            values[name] = candidate
        if values["warn_node_batch"] > values["maximum_node_batch"]:
            logging.warning("Ignoring inconsistent node batch settings")
            values["warn_node_batch"] = defaults.warn_node_batch
            values["maximum_node_batch"] = defaults.maximum_node_batch
        return cls(**values)


DEFAULT_RUNTIME = RuntimeSettings()
