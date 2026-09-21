"""Tag normalization shared by UI, local storage and future HTTP adapters."""

from __future__ import annotations

import re
from collections.abc import Iterable

_TAG_SEPARATORS = re.compile(r"[#,\r\n]+")


def tag_text(tags: Iterable[str]) -> str:
    """The editor form of a tag list: ``#a #b`` in the list's own order."""
    return " ".join(f"#{tag}" for tag in tags)


def normalize_tags(tags: str | Iterable[str] | None) -> list[str]:
    """Split on #, comma or newline; strip; drop empties and case-insensitive repeats.

    Order of first appearance is kept. Tags never contain "#" because tag_info stores
    them "#"-joined (asset_tags is derived from that column by triggers).
    """
    if not tags:
        return []
    parts = [tags] if isinstance(tags, str) else list(tags)
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        for tag in _TAG_SEPARATORS.split(str(part)):
            tag = tag.strip()
            if not tag or tag.casefold() in seen:
                continue
            seen.add(tag.casefold())
            result.append(tag)
    return result
