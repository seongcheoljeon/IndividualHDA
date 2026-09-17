"""Injectable panel timing and batch limits; defaults preserve existing behavior."""

from dataclasses import dataclass

from libs.browser_search import SearchPolicy
from libs.runtime_settings import DEFAULT_RUNTIME


@dataclass(frozen=True, slots=True)
class PanelPolicy:
    sync_interval_ms: int = DEFAULT_RUNTIME.sync_interval_seconds * 1000
    search: SearchPolicy = SearchPolicy()
    maximum_node_batch: int = DEFAULT_RUNTIME.maximum_node_batch
    warn_node_batch: int = DEFAULT_RUNTIME.warn_node_batch

    def __post_init__(self) -> None:
        for name in ("sync_interval_ms", "maximum_node_batch", "warn_node_batch"):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= 2_147_483_647:
                raise ValueError(f"{name} must be a positive Qt-compatible integer")
        if self.warn_node_batch > self.maximum_node_batch:
            raise ValueError("Batch warning cannot exceed the maximum batch size")
