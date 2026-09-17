"""SQLite connection policy, independent of Qt and server database settings."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class SQLitePolicy:
    connect_timeout_seconds: float = 5.0
    busy_timeout_ms: int = 5000

    def __post_init__(self) -> None:
        value = self.connect_timeout_seconds
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise ValueError("SQLite connection timeout must be finite and positive")
        if (
            type(self.busy_timeout_ms) is not int
            or not 0 <= self.busy_timeout_ms <= 2_147_483_647
        ):
            raise ValueError("SQLite busy timeout must be a nonnegative 32-bit integer")
