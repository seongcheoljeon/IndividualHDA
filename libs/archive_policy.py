"""Resource limits for reading an archive, separate from its wire format."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    expanded_bytes: int = 100 * 1024**3
    entries: int = 1_000_000

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value <= 0
            for value in (self.expanded_bytes, self.entries)
        ):
            raise ValueError("Archive limits must be positive integers")
