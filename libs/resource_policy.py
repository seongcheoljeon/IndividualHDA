"""Internal, injectable resource choices. These are not persisted user settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CallbackPolicy:
    retry_delay_ms: int = 50

    def __post_init__(self) -> None:
        if (
            type(self.retry_delay_ms) is not int
            or not 0 < self.retry_delay_ms <= 2_147_483_647
        ):
            raise ValueError("Callback delay must be a positive Qt-compatible integer")


@dataclass(frozen=True, slots=True)
class MediaPolicy:
    probe_timeout_seconds: int = 20

    def __post_init__(self) -> None:
        if (
            type(self.probe_timeout_seconds) is not int
            or not 0 < self.probe_timeout_seconds <= 2_147_483
        ):
            raise ValueError(
                "Media timeout must be positive and fit a Qt millisecond timer"
            )


@dataclass(frozen=True, slots=True)
class ThumbnailPolicy:
    capacity: int = 256
    byte_limit: int = 64 * 1024 * 1024
    decode_edge: int = 1024
    workers: int = 2
    pending: int = 32

    def __post_init__(self) -> None:
        if any(
            type(v) is not int or v <= 0
            for v in (
                self.capacity,
                self.byte_limit,
                self.decode_edge,
                self.workers,
                self.pending,
            )
        ):
            raise ValueError("Thumbnail resource limits must be positive integers")
