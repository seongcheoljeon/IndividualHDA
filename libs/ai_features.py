"""AI feature A: suggest a note and tags for an asset. Pure functions, no Qt/HOM.

The prompt never carries file paths, user names, hosts or hip locations; it is
built from asset metadata already stored in the library plus the thumbnail.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from libs.ai_provider import AIProvider, Prompt
from libs.asset_contracts import AssetData
from libs.tags import normalize_tags

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_VOCABULARY = 40
MAX_TAGS = 12
MAX_ANSWER_TOKENS = 400  # two sentences plus tags in JSON; stops a runaway answer

SYSTEM = (
    "You describe Houdini digital assets for a studio asset library. "
    "Answer with exactly one fenced ```json block and nothing else."
)


@dataclass(frozen=True, slots=True)
class Description:
    summary: str = ""
    tags: tuple[str, ...] = ()


def structure_from_asset(
    asset: AssetData,
    *,
    children: Mapping[str, int] | None = None,
    parameters: Sequence[str] = (),
) -> dict[str, Any]:
    """What the library already knows about the node; safe to send as-is."""
    return {
        "type": asset.node_type_name,
        "category": asset.hda_cate,
        "definition": asset.node_def_desc,
        "is_network": bool(asset.is_network),
        "is_sub_network": bool(asset.is_sub_network),
        "inputs": len(asset.node_input_connections or ()),
        "outputs": len(asset.node_output_connections or ()),
        "children": dict(children or {}),  # supplied by a host snapshot when available
        "parameters": list(parameters),
    }


def build_describe_prompt(
    name: str,
    structure: dict[str, Any],
    *,
    existing_note: str = "",
    existing_tags: Sequence[str] = (),
    vocabulary: Sequence[str] = (),
    language: str = "en",
    image: bytes | None = None,
) -> Prompt:
    lines = [
        f"Asset: {name}",
        f"Category: {structure.get('category', '')}   Node type: {structure.get('type', '')}",
    ]
    if structure.get("definition"):
        lines.append(f"Definition comment: {structure['definition']}")
    lines.append(
        f"Network: {structure.get('is_network')}, sub-network: {structure.get('is_sub_network')}, "
        f"inputs: {structure.get('inputs', 0)}, outputs: {structure.get('outputs', 0)}"
    )
    children = structure.get("children") or {}
    if children:
        counted = ", ".join(f"{k}: {v}" for k, v in sorted(children.items()))
        lines.append(f"Child node types (type: count): {counted}")
    if structure.get("parameters"):
        lines.append(
            "Parameters: " + ", ".join(str(p) for p in structure["parameters"])
        )
    if existing_note.strip():
        lines.append(f"Existing note: {existing_note.strip()}")
    if existing_tags:
        lines.append("Existing tags: " + ", ".join(existing_tags))
    if vocabulary:
        shown = ", ".join(list(vocabulary)[:MAX_VOCABULARY])
        lines.append(
            f"Studio tag vocabulary (reuse these words when they fit): {shown}"
        )
    if image is not None:
        lines.append("The attached image is the asset's preview thumbnail.")
    lines.append(
        'Return {"summary": "at most two sentences in language '
        f"'{language}' describing what the asset does and when to use it\", "
        '"tags": ["3 to 8 short tags, lowercase, use _ instead of spaces, no #"]}'
    )
    return Prompt(
        text="\n".join(lines),
        system=SYSTEM,
        images=(image,) if image is not None else (),
        max_tokens=MAX_ANSWER_TOKENS,
    )


def _extract_json(text: str) -> Any:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            excerpt = " ".join(text.split())[:120]
            raise ValueError(
                "no JSON object in the model answer"
                + (f": {excerpt!r}" if excerpt else " (the answer was empty)")
            )
        candidate = text[start : end + 1]
    return json.loads(candidate)


def parse_describe(text: str) -> Description:
    """Tolerant of fences, chatter around the JSON, and tags given as one string."""
    try:
        data = _extract_json(text)
    except ValueError as error:
        raise ValueError(f"could not read the model answer: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("model answer is not a JSON object")
    summary = str(data.get("summary", "")).strip()
    raw_tags = data.get("tags", [])
    tags = normalize_tags(
        raw_tags if isinstance(raw_tags, str) else [str(t) for t in raw_tags]
    )
    tags = [t.lower().replace(" ", "_") for t in tags][:MAX_TAGS]
    return Description(summary=summary, tags=tuple(tags))


def read_thumbnail(path: Path | None) -> bytes | None:
    if path is None or not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
        return None
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff"):
        return data
    return None


def describe_asset(
    provider: AIProvider,
    asset: AssetData,
    *,
    thumbnail: Path | None = None,
    vocabulary: Sequence[str] = (),
    language: str = "en",
    structure: dict[str, Any] | None = None,
) -> Description:
    """Runs on a worker thread: read the image, ask the model, parse the answer."""
    prompt = build_describe_prompt(
        str(asset.hda_name),
        structure or structure_from_asset(asset),
        existing_note=str(asset.hda_note or ""),
        existing_tags=list(asset.hda_tags or []),
        vocabulary=vocabulary,
        language=language,
        image=read_thumbnail(thumbnail),
    )
    return parse_describe(provider.complete(prompt))
