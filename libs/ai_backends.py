"""Concrete AI backends over the standard library; no Qt or HOM imports.

Every request carries a timeout and never retries: the user clicks again. API
keys are read from the environment at call time and never logged.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Iterator
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


def stream_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = TIMEOUT_SEC,
) -> Iterator[dict[str, Any]]:
    """POST and yield one object per NDJSON line.

    The socket timeout applies between lines, so a slow generation or a model
    that is still loading does not fail as long as the server keeps talking; a
    server that went silent for ``timeout`` seconds does.
    """
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with _open(request, timeout=timeout) as response:
            for raw in response:
                if not raw.strip():
                    continue
                try:
                    event = json.loads(raw.decode("utf-8"))
                except ValueError as error:
                    raise AIError("response was not JSON") from error
                if not isinstance(event, dict):
                    raise AIError("unexpected response shape")
                yield event
    except urllib.error.HTTPError as error:
        excerpt = error.read()[:500].decode("utf-8", "replace")
        raise AIError(f"HTTP {error.code}: {excerpt}", status=error.code) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AIError(f"request failed: {error}") from error


class OllamaProvider:
    """Ollama /api/chat, streamed; images travel as base64 on the user message.

    ``think`` is sent as false: thinking models (qwen3, gemma4) otherwise reason
    at length before a one-word or JSON answer, and Ollama only rejects
    ``think: true`` on models without the capability (server/routes.go).
    """

    def __init__(self, settings: AISettings) -> None:
        self.endpoint = normalize_endpoint(settings.endpoint, "http://localhost:11434")
        self.model = settings.model.strip()
        # Seconds from the final chunk of the last call: "load" and "total".
        self.last_timings: dict[str, float] = {}

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
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "think": False,
            "messages": messages,
        }
        if prompt.max_tokens is not None:
            payload["options"] = {"num_predict": prompt.max_tokens}
        parts: list[str] = []
        self.last_timings = {}
        for event in stream_json(f"{self.endpoint}/api/chat", payload):
            if "error" in event:
                raise AIError(str(event["error"]))
            parts.append(str((event.get("message") or {}).get("content", "")))
            if event.get("done"):
                for key, field in (
                    ("load", "load_duration"),
                    ("total", "total_duration"),
                ):
                    if isinstance(event.get(field), int | float):
                        self.last_timings[key] = float(event[field]) / 1e9
                break
        return "".join(parts)


def probe(provider: AIProvider) -> str:
    """Round trip a tiny prompt; the answer's first characters plus timings.

    The timing suffix tells a user whether a slow test was the model loading
    into GPU memory (first call, or after Ollama's 5 minute keep_alive) or the
    generation itself.
    """
    answer = provider.complete(
        Prompt("Reply with the single word OK.", max_tokens=8)
    ).strip()[:40]
    timings = getattr(provider, "last_timings", None) or {}
    if "total" in timings:
        load = timings.get("load", 0.0)
        answer += f"  (model load {load:.1f} s, total {timings['total']:.1f} s)"
    return answer
