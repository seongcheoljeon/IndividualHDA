"""Search an immutable remote snapshot using the panel's existing token syntax."""

from __future__ import annotations

import re
from copy import deepcopy
from threading import Event
from typing import Any

from libs.browser_search import SearchRequest


class DocumentSearch:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = deepcopy(documents)

    def search(self, request: SearchRequest, cancel: Event) -> list[int]:
        aliases = {
            "name": "Name",
            "tag": "Tags",
            "tags": "Tags",
            "type": "Type",
            "note": "Note",
        }
        tokens = []
        for token in request.text.split():
            prefix, separator, rest = token.partition(":")
            field = request.field
            if separator and rest and prefix.lower() in aliases:
                field, token = aliases[prefix.lower()], rest
            pattern = re.escape(token).replace(r"\*", ".*").replace(r"\?", ".")
            tokens.append(
                (
                    field,
                    re.compile(pattern, 0 if request.case_sensitive else re.IGNORECASE),
                )
            )
        matches = []
        for document in self._documents:
            if cancel.is_set():
                break
            metadata = document.get("metadata", {})
            fields = {
                "Name": [document["name"]],
                "Tags": document.get("tags", []),
                "Type": [metadata.get("node_type_name", "")],
                "Note": [document.get("note", "")],
            }
            fields["All"] = [
                value for values in fields.values() for value in values
            ] + [metadata.get("node_def_desc", "")]
            if all(
                any(pattern.search(value) for value in fields.get(field, fields["All"]))
                for field, pattern in tokens
            ):
                matches.append(document["id"])
        return matches
