"""Client-side HTTP resource policy.

Protocol caps that client and server validate together live in
libs.team.contracts; these are local resource choices for the transport.
"""

from __future__ import annotations

from dataclasses import dataclass

from libs.file_integrity import FILE_READ_CHUNK_BYTES
from libs.runtime_settings import DEFAULT_RUNTIME

DEFAULT_HTTP_TIMEOUT_SECONDS = float(DEFAULT_RUNTIME.team_timeout_seconds)


@dataclass(frozen=True, slots=True)
class HttpLimits:
    response_bytes: int = 16 * 1024 * 1024
    diagnostic_bytes: int = 64 * 1024
    chunk_bytes: int = FILE_READ_CHUNK_BYTES

    def __post_init__(self) -> None:
        for value in (self.response_bytes, self.diagnostic_bytes, self.chunk_bytes):
            if type(value) is not int or value <= 0:
                raise ValueError("HTTP resource limits must be positive integers")
