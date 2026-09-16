"""Validated connection/query timeout policy, supplied at engine construction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatabaseTimeouts:
    connect_seconds: int = 10
    statement_ms: int = 30_000
    lock_ms: int = 15_000

    def __post_init__(self) -> None:
        for value in (self.connect_seconds, self.statement_ms, self.lock_ms):
            if type(value) is not int or value < 0:
                raise ValueError("Database timeouts must be nonnegative integers")
        if self.connect_seconds == 0:
            raise ValueError("Database connection timeout must be positive")

    @property
    def postgres_options(self) -> str:
        return (
            f"-c statement_timeout={self.statement_ms} -c lock_timeout={self.lock_ms}"
        )
