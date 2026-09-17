"""Validate named records at storage/JSON boundaries; application code uses attributes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from pathlib import Path
from types import UnionType
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

Record = TypeVar("Record")


def decode_record(record_type: type[Record], document: Mapping[str, Any]) -> Record:
    if not isinstance(document, Mapping):
        raise ValueError(f"{record_type.__name__} requires named fields")
    hints = get_type_hints(record_type)
    unknown = document.keys() - hints.keys()
    if unknown:
        raise ValueError(f"Unknown {record_type.__name__} fields: {sorted(unknown)}")
    values = {key: _value(hints[key], value, key) for key, value in document.items()}
    try:
        return record_type(**values)
    except TypeError as error:
        raise ValueError(f"Invalid {record_type.__name__}: {error}") from error


def _value(expected: Any, value: Any, field: str) -> Any:
    origin, arguments = get_origin(expected), get_args(expected)
    if origin is UnionType:
        for option in arguments:
            try:
                return _value(option, value, field)
            except ValueError:
                pass
    elif expected is Any:
        return value
    elif expected is type(None) and value is None:
        return None
    elif expected is Path and isinstance(value, (str, Path)):
        return Path(value)
    elif origin is tuple and isinstance(value, (list, tuple)):
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return tuple(_value(arguments[0], item, field) for item in value)
    elif (
        isinstance(expected, type)
        and is_dataclass(expected)
        and isinstance(value, Mapping)
    ):
        return decode_record(expected, value)
    elif isinstance(expected, type) and type(value) is expected:
        return value
    elif expected is float and type(value) is int:
        return (
            value  # preserve JSON number spelling for historical operation fingerprints
        )
    raise ValueError(f"Invalid type for {field}: expected {expected}")


def record_document(record: Any) -> dict[str, Any]:
    """JSON-safe named document; serialization is intentionally explicit."""

    def encode(value: Any) -> Any:
        if isinstance(value, Path):
            return str(value)
        if is_dataclass(value):
            return {
                field.name: encode(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, (tuple, list)):
            return [encode(item) for item in value]
        if isinstance(value, Mapping):
            return {key: encode(item) for key, item in value.items()}
        return value

    if not is_dataclass(record) or isinstance(record, type):
        raise TypeError("Expected a record instance")
    return encode(record)
