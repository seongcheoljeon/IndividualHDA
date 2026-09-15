"""Concrete AI backends over the standard library; no Qt or HOM imports.

Every request carries a timeout and never retries: the user clicks again. API
keys are read from the environment at call time and never logged.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from libs.ai_provider import AIProvider, AISettings, Prompt

TIMEOUT_SEC = 60.0  # silence between chunks
# Whole-request ceiling for a stream that keeps trickling: a model offloaded to
# the CPU can answer at one token per second and would otherwise never finish
# from the user's point of view.
TOTAL_TIMEOUT_SEC = 300.0

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
    total_timeout: float = TOTAL_TIMEOUT_SEC,
) -> Iterator[dict[str, Any]]:
    """POST and yield one object per NDJSON line.

    The socket timeout applies between lines, so a slow generation or a model
    that is still loading does not fail as long as the server keeps talking; a
    server that went silent for ``timeout`` seconds does, and so does a stream
    still running after ``total_timeout`` seconds.
    """
    deadline = time.monotonic() + total_timeout
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
                if time.monotonic() > deadline:
                    raise AIError(
                        f"gave up after {total_timeout:.0f} s; the model answers too "
                        "slowly (GPU memory shared with Houdini? try a smaller model)"
                    )
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
        # From the final chunk of the last call: "load" and "total" seconds,
        # "prompt_tokens", "tokens" and "tokens_per_s" (Ollama API: eval_count /
        # eval_duration * 1e9).
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
                self.last_timings = _timings(event)
                break
        return "".join(parts)


def _timings(event: dict[str, Any]) -> dict[str, float]:
    def number(field: str) -> float | None:
        value = event.get(field)
        return float(value) if isinstance(value, int | float) else None

    timings: dict[str, float] = {}
    for key, field in (("load", "load_duration"), ("total", "total_duration")):
        seconds = number(field)
        if seconds is not None:
            timings[key] = seconds / 1e9
    prompt_tokens, tokens, eval_ns = (
        number("prompt_eval_count"),
        number("eval_count"),
        number("eval_duration"),
    )
    if prompt_tokens is not None:
        timings["prompt_tokens"] = prompt_tokens
    if tokens is not None:
        timings["tokens"] = tokens
        if eval_ns:
            timings["tokens_per_s"] = tokens / eval_ns * 1e9
    return timings


def format_timings(timings: dict[str, float]) -> str:
    """One line for logs and status labels; empty when nothing was reported."""
    if "total" not in timings:
        return ""
    parts = [
        f"model load {timings.get('load', 0.0):.1f} s",
        f"total {timings['total']:.1f} s",
    ]
    if "tokens_per_s" in timings:
        parts.append(
            f"{timings['tokens']:.0f} tokens at {timings['tokens_per_s']:.1f} tok/s"
        )
    return ", ".join(parts)


def probe(provider: AIProvider) -> str:
    """Round trip a tiny prompt; the answer's first characters plus timings.

    The timing suffix tells a user whether a slow test was the model loading
    into GPU memory (first call, or after Ollama's 5 minute keep_alive) or the
    generation itself.
    """
    answer = provider.complete(
        Prompt("Reply with the single word OK.", max_tokens=8)
    ).strip()[:40]
    summary = format_timings(getattr(provider, "last_timings", None) or {})
    return f"{answer}  ({summary})" if summary else answer
