"""AI backend contract; no Qt or HOM imports.

Every future feature (asset description/tags, natural-language search, effect
generation from text or images) is a function layered on ``AIProvider.complete``.
Real backends must use only the standard library (``urllib.request``) and always
pass a timeout; nothing is installed into Houdini's Python.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from libs.ai_defaults import OLLAMA_ENDPOINT, OLLAMA_MODEL

KINDS = ("none", "local", "anthropic", "openai")

# Which AISettings fields each backend needs; the Preference dialog enables only
# these and a backend must not read anything else. Placeholders are hints only.
FIELDS: dict[str, tuple[str, ...]] = {
    "none": (),
    "local": ("endpoint", "model"),
    "anthropic": ("model", "api_key_env"),
    "openai": ("endpoint", "model", "api_key_env"),
}
PLACEHOLDERS: dict[str, dict[str, str]] = {
    "local": {"endpoint": OLLAMA_ENDPOINT, "model": OLLAMA_MODEL},
    "anthropic": {"model": "claude-sonnet-5", "api_key_env": "ANTHROPIC_API_KEY"},
    "openai": {
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
    },
}


@dataclass(frozen=True, slots=True)
class AISettings:
    kind: str = "none"
    endpoint: str = ""  # e.g. http://localhost:11434 for a local server
    model: str = ""
    api_key_env: str = ""  # NAME of the environment variable holding the key


@dataclass(frozen=True, slots=True)
class Prompt:
    text: str
    system: str = ""
    images: tuple[bytes, ...] = ()  # encoded image bytes for multimodal backends
    max_tokens: int | None = None  # output cap; None lets the backend decide


class AIProvider(Protocol):
    # progress: called once per streamed chunk with the running token count, on
    # the worker thread. Raising from it aborts the request -- that is how the
    # panel cancels.
    def complete(
        self, prompt: Prompt, *, progress: Callable[[int], None] | None = None
    ) -> str: ...


class NullProvider:
    """Default backend: every request completes immediately with no text."""

    def complete(
        self, prompt: Prompt, *, progress: Callable[[int], None] | None = None
    ) -> str:
        return ""


def make_provider(settings: AISettings) -> AIProvider:
    if settings.kind == "local":
        from libs.ai_backends import OllamaProvider  # local import: no cycle

        return OllamaProvider(settings)
    # ponytail: anthropic/openai resolve to Null until implemented (Phase 3b).
    return NullProvider()
