"""Concrete AI backends over the standard library; no Qt or HOM imports.

Every request carries a timeout and never retries: the user clicks again. API
keys are read from the environment at call time and never logged.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from libs.ai_provider import AIProvider, AISettings, Prompt

TIMEOUT_SEC = 60.0

# Local servers must not be routed through a studio HTTP proxy.
_open = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


class AIError(RuntimeError):
    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


def normalize_endpoint(endpoint: str, default: str) -> str:
    return (endpoint.strip() or default).rstrip("/")


def mime_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise AIError("only PNG and JPEG images can be sent to the model")


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = TIMEOUT_SEC,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with _open(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        excerpt = error.read()[:500].decode("utf-8", "replace")
        raise AIError(f"HTTP {error.code}: {excerpt}", status=error.code) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AIError(f"request failed: {error}") from error
    try:
        result = json.loads(raw.decode("utf-8"))
    except ValueError as error:
        raise AIError("response was not JSON") from error
    if not isinstance(result, dict):
        raise AIError("unexpected response shape")
    return result


class OllamaProvider:
    """Ollama /api/chat; images travel as base64 on the user message."""

    def __init__(self, settings: AISettings) -> None:
        self.endpoint = normalize_endpoint(settings.endpoint, "http://localhost:11434")
        self.model = settings.model.strip()

    def complete(self, prompt: Prompt) -> str:
        if not self.model:
            raise AIError("choose a model in Preferences (AI) first")
        for image in prompt.images:
            mime_type(image)  # reject unsupported bytes before uploading them
        user: dict[str, Any] = {"role": "user", "content": prompt.text}
        if prompt.images:
            user["images"] = [
                base64.b64encode(i).decode("ascii") for i in prompt.images
            ]
        messages: list[dict[str, Any]] = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append(user)
        result = post_json(
            f"{self.endpoint}/api/chat",
            {"model": self.model, "stream": False, "messages": messages},
        )
        if "error" in result:
            raise AIError(str(result["error"]))
        message = result.get("message") or {}
        return str(message.get("content", ""))


def probe(provider: AIProvider) -> str:
    """Round trip a tiny prompt; returns the first characters of the answer."""
    return provider.complete(Prompt("Reply with the single word OK.")).strip()[:40]
