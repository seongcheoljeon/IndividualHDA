from __future__ import annotations

import io
import json
import threading
import urllib.error
from typing import Any

import pytest

from libs import ai_backends, ollama
from libs.ai_backends import AIError, OllamaProvider, probe
from libs.ai_provider import AISettings, Prompt

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 8


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def opener(routes: dict[str, Any], calls: list[Any]) -> Any:
    def _open(request: Any, timeout: float = 0) -> FakeResponse:
        url = request.full_url if hasattr(request, "full_url") else request
        calls.append((url, request.data if hasattr(request, "data") else None, timeout))
        body = routes[url]
        if isinstance(body, Exception):
            raise body
        return FakeResponse(
            body if isinstance(body, bytes) else json.dumps(body).encode()
        )

    return _open


def test_version_and_installed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    routes = {
        "http://host:11434/api/version": {"version": "0.12.1"},
        "http://host:11434/api/tags": {
            "models": [
                {"name": "z:1b", "size": 10, "details": {"parameter_size": "1B"}},
                {"name": "a:4b", "size": 3_300_000_000},
            ]
        },
    }
    monkeypatch.setattr(ollama, "_open", opener(routes, calls))
    assert ollama.version("http://host:11434/") == "0.12.1"  # trailing slash stripped
    models = ollama.installed_models("http://host:11434")
    assert [m.name for m in models] == ["a:4b", "z:1b"]
    assert models[1].parameter_size == "1B" and models[0].size_bytes == 3_300_000_000
    down = {
        "http://host:11434/api/version": urllib.error.URLError("down"),
        "http://host:11434/api/tags": urllib.error.URLError("down"),
    }
    monkeypatch.setattr(ollama, "_open", opener(down, calls))
    assert ollama.version("http://host:11434") is None
    with pytest.raises(AIError):
        ollama.installed_models("http://host:11434")


def test_pull_streams_progress_and_handles_cancel_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Any] = []
    stream = b"\n".join(
        json.dumps(e).encode()
        for e in [
            {"status": "pulling manifest"},
            {"status": "pulling abc", "digest": "abc", "total": 100, "completed": 40},
            {"status": "pulling abc", "digest": "abc", "total": 100, "completed": 100},
            {"status": "success"},
        ]
    )
    monkeypatch.setattr(
        ollama, "_open", opener({"http://h:11434/api/pull": stream}, calls)
    )
    seen: list[tuple[str, int, int]] = []
    assert ollama.pull(
        "http://h:11434",
        "m:1",
        progress=lambda *a: seen.append(a),
        cancel=threading.Event(),
    )
    assert seen == [
        ("pulling manifest", 0, 0),
        ("pulling abc", 40, 100),
        ("pulling abc", 100, 100),
        ("success", 0, 0),
    ]
    assert json.loads(calls[-1][1]) == {"model": "m:1", "stream": True}

    cancel = threading.Event()
    cancel.set()
    seen.clear()
    assert (
        ollama.pull(
            "http://h:11434", "m:1", progress=lambda *a: seen.append(a), cancel=cancel
        )
        is False
    )
    assert seen == []

    error_stream = json.dumps(
        {"error": "pull model manifest: file does not exist"}
    ).encode()
    monkeypatch.setattr(
        ollama, "_open", opener({"http://h:11434/api/pull": error_stream}, calls)
    )
    with pytest.raises(AIError, match="does not exist"):
        ollama.pull(
            "http://h:11434", "nope", progress=lambda *a: None, cancel=threading.Event()
        )


def test_vram_detection_and_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> Any:
        class Out:
            stdout = "8192\n24576\n" if "nvidia-smi" in args[0] else str(32 * 1024**3)

        return Out()

    monkeypatch.setattr(ollama, "_run", fake_run)
    monkeypatch.setattr(ollama.platform, "system", lambda: "Linux")
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    assert ollama.detect_vram_gb() == 24.0
    monkeypatch.setattr(ollama.platform, "system", lambda: "Darwin")
    assert ollama.detect_vram_gb() == 24.0  # 32 GB unified memory * 0.75
    monkeypatch.setattr(ollama.platform, "system", lambda: "Linux")
    monkeypatch.setattr(ollama.shutil, "which", lambda name: None)
    assert ollama.detect_vram_gb() is None
    assert ollama.choose_recommended(None) == ollama.FALLBACK_MODEL
    assert ollama.choose_recommended(4) == "qwen3-vl:4b"
    assert ollama.choose_recommended(12) == "gemma4:12b"
    assert ollama.choose_recommended(48) == "gemma4:26b"
    assert ollama.install_hint()


def test_ollama_provider_request_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    reply = b"\n".join(
        json.dumps(chunk).encode()
        for chunk in (
            {"message": {"role": "assistant", "content": "O"}, "done": False},
            {"message": {"role": "assistant", "content": "K"}, "done": False},
            {
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "load_duration": 24_500_000_000,
                "total_duration": 26_000_000_000,
                "prompt_eval_count": 900,
                "eval_count": 3,
                "eval_duration": 1_500_000_000,
            },
        )
    )
    monkeypatch.setattr(
        ai_backends, "_open", opener({"http://h:11434/api/chat": reply}, calls)
    )
    provider = OllamaProvider(
        AISettings(kind="local", endpoint="http://h:11434/", model="qwen3-vl:8b")
    )
    text = provider.complete(Prompt("describe", system="be brief", images=(PNG,)))
    assert text == "OK"
    body = json.loads(calls[-1][1])
    assert body["model"] == "qwen3-vl:8b" and body["stream"] is True
    assert body["think"] is False and "options" not in body
    assert provider.last_timings == {
        "load": 24.5,
        "total": 26.0,
        "prompt_tokens": 900.0,
        "tokens": 3.0,
        "tokens_per_s": 2.0,
    }
    assert body["messages"][0] == {"role": "system", "content": "be brief"}
    assert body["messages"][1]["content"] == "describe"
    assert body["messages"][1]["images"][0].startswith("iVBORw0KGgo")
    assert calls[-1][2] == ai_backends.TIMEOUT_SEC
    assert probe(provider) == (
        "OK  (model load 24.5 s, total 26.0 s, 3 tokens at 2.0 tok/s)"
    )
    assert json.loads(calls[-1][1])["options"] == {"num_predict": 8}

    error = json.dumps({"error": "model 'x' not found"}).encode()
    monkeypatch.setattr(
        ai_backends, "_open", opener({"http://h:11434/api/chat": error}, calls)
    )
    with pytest.raises(AIError, match="not found"):
        provider.complete(Prompt("x"))
    monkeypatch.setattr(
        ai_backends,
        "_open",
        opener({"http://h:11434/api/chat": TimeoutError("timed out")}, calls),
    )
    with pytest.raises(AIError, match="request failed: timed out"):
        provider.complete(Prompt("x"))
    # A stream that keeps trickling past the overall ceiling is abandoned.
    trickle = b"\n".join(
        json.dumps({"message": {"content": "."}, "done": False}).encode()
        for _ in range(3)
    )
    monkeypatch.setattr(
        ai_backends, "_open", opener({"http://h:11434/api/chat": trickle}, calls)
    )
    clock = iter([0.0, 0.0, 400.0, 400.0, 400.0])
    monkeypatch.setattr(ai_backends.time, "monotonic", lambda: next(clock))
    with pytest.raises(AIError, match="gave up after 300 s"):
        provider.complete(Prompt("x"))
    with pytest.raises(AIError, match="PNG and JPEG"):
        provider.complete(Prompt("x", images=(b"gif89a",)))
    with pytest.raises(AIError, match="choose a model"):
        OllamaProvider(AISettings(kind="local")).complete(Prompt("x"))
    http_error = urllib.error.HTTPError(
        "u", 404, "nf", {}, io.BytesIO(b"model not found")
    )
    monkeypatch.setattr(
        ai_backends, "_open", opener({"http://h:11434/api/chat": http_error}, calls)
    )
    with pytest.raises(AIError, match="HTTP 404") as info:
        provider.complete(Prompt("x"))
    assert info.value.status == 404
