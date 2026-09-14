"""Ollama server management over its HTTP API; stdlib only, no Qt or HOM.

Used by the Local AI Models dialog: detect the server, list installed models,
pull a model with progress, and pick a sensible default for the machine.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import platform
import shutil
import subprocess
import threading
import urllib.error
import urllib.request

from libs.ai_backends import AIError, _open, normalize_endpoint

DEFAULT_ENDPOINT = "http://localhost:11434"
DOWNLOAD_PAGE = "https://ollama.com/download"
_run = subprocess.run  # test seam


@dataclass(frozen=True, slots=True)
class InstalledModel:
    name: str
    size_bytes: int
    parameter_size: str = ""


@dataclass(frozen=True, slots=True)
class ModelChoice:
    name: str
    download_gb: float
    min_vram_gb: float
    vision: bool
    note: str


# Verified against https://ollama.com/library on 2026-09-14. All support image
# input and multilingual (incl. Korean) text; sizes are the default quantization.
RECOMMENDED: tuple[ModelChoice, ...] = (
    ModelChoice("qwen3-vl:4b", 3.3, 6, True, "Small and fast; laptops, 6 GB GPUs"),
    ModelChoice("qwen3-vl:8b", 6.1, 8, True, "Balanced default for 8-12 GB GPUs"),
    ModelChoice("gemma4:12b", 7.6, 12, True, "Best quality under 16 GB; 256K context"),
    ModelChoice(
        "gemma4:26b", 19.0, 24, True, "Workstation class; MoE, fast for its size"
    ),
)
FALLBACK_MODEL = "qwen3-vl:8b"


def endpoint_url(endpoint: str) -> str:
    return normalize_endpoint(endpoint, DEFAULT_ENDPOINT)


def _get_json(url: str, timeout: float) -> dict:
    with _open(urllib.request.Request(url), timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result if isinstance(result, dict) else {}


def version(endpoint: str, timeout: float = 2.0) -> str | None:
    """Server version string, or None when nothing answers (never raises)."""
    try:
        return str(
            _get_json(f"{endpoint_url(endpoint)}/api/version", timeout).get(
                "version", ""
            )
        )
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def installed_models(endpoint: str, timeout: float = 5.0) -> list[InstalledModel]:
    try:
        payload = _get_json(f"{endpoint_url(endpoint)}/api/tags", timeout)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
        raise AIError(f"could not list models: {error}") from error
    models = []
    for item in payload.get("models") or []:
        details = item.get("details") or {}
        models.append(
            InstalledModel(
                name=str(item.get("name", "")),
                size_bytes=int(item.get("size") or 0),
                parameter_size=str(details.get("parameter_size", "")),
            )
        )
    return sorted(models, key=lambda m: m.name)


def pull(
    endpoint: str,
    model: str,
    *,
    progress: Callable[[str, int, int], None],
    cancel: threading.Event,
    timeout: float = 30.0,
) -> bool:
    """Download ``model``; returns False if cancelled. Ollama keeps finished layers,
    so a later pull of the same model resumes."""
    request = urllib.request.Request(
        f"{endpoint_url(endpoint)}/api/pull",
        data=json.dumps({"model": model, "stream": True}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _open(request, timeout=timeout) as response:
            for raw in response:  # NDJSON, one status object per line
                if cancel.is_set():
                    return False  # closing the response aborts the server side
                if not raw.strip():
                    continue
                event = json.loads(raw.decode("utf-8"))
                if "error" in event:
                    raise AIError(str(event["error"]))
                status = str(event.get("status", ""))
                progress(
                    status,
                    int(event.get("completed") or 0),
                    int(event.get("total") or 0),
                )
                if status == "success":
                    return True
    except urllib.error.HTTPError as error:
        raise AIError(
            f"HTTP {error.code}: {error.read()[:300].decode('utf-8', 'replace')}"
        ) from error
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        raise AIError(f"download failed: {error}") from error
    raise AIError("download ended before the server reported success")


def detect_vram_gb() -> float | None:
    """Largest NVIDIA GPU memory, macOS unified memory, or None when unknown."""
    system = platform.system()
    try:
        if system == "Darwin":
            out = _run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            # Apple Silicon shares RAM with the GPU; leave room for Houdini itself.
            return round(int(out.stdout.strip()) / 1024**3 * 0.75, 1)
        smi = shutil.which("nvidia-smi") or (
            r"C:\Windows\System32\nvidia-smi.exe" if system == "Windows" else None
        )
        if smi is None:
            return None
        out = _run(
            [smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        values = [float(line) for line in out.stdout.split() if line.strip().isdigit()]
        return round(max(values) / 1024, 1) if values else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def choose_recommended(vram_gb: float | None) -> str:
    if vram_gb is None:
        return FALLBACK_MODEL
    fitting = [choice for choice in RECOMMENDED if choice.min_vram_gb <= vram_gb]
    return (fitting[-1] if fitting else RECOMMENDED[0]).name


def install_hint() -> str:
    return {
        "Windows": "winget install Ollama.Ollama",
        "Darwin": "brew install ollama   (then run: ollama serve)",
    }.get(platform.system(), "curl -fsSL https://ollama.com/install.sh | sh")
