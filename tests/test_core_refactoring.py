from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from ihda_server.database_policy import DatabaseTimeouts
from libs.file_integrity import FileContent, measure_file
from libs.team.contracts import Blob
from libs.team.limits import HttpLimits


def test_file_content_value_equality_hash_and_immutability(tmp_path: Path) -> None:
    first = tmp_path / "first.hda"
    second = tmp_path / "renamed.hda"
    first.write_bytes(b"asset content")
    second.write_bytes(first.read_bytes())
    content = measure_file(first)
    assert content == measure_file(second)
    assert len({content, measure_file(second)}) == 1
    assert {content: "cached"}[measure_file(second)] == "cached"
    assert content != FileContent(content.digest, content.size + 1)
    assert content != (content.digest, content.size)
    with pytest.raises(FrozenInstanceError):
        content.size = 0  # type: ignore[misc]
    original, renamed = (
        Blob(content.digest, content.size, first.name),
        Blob(content.digest, content.size, second.name),
    )
    assert original != renamed  # different file references, identical contents
    assert original.content == renamed.content
    assert set(asdict(original)) == {"digest", "size", "filename"}


def test_measurement_cancellation_including_empty_files(tmp_path: Path) -> None:
    file = tmp_path / "empty"
    file.write_bytes(b"")
    assert measure_file(file) == FileContent(hashlib.sha256(b"").hexdigest(), 0)

    def cancel() -> None:
        raise RuntimeError("Cancelled")

    with pytest.raises(RuntimeError, match="Cancelled"):
        measure_file(file, cancel)


@pytest.mark.parametrize(
    "kwargs", [{"response_bytes": 0}, {"chunk_bytes": -1}, {"diagnostic_bytes": True}]
)
def test_invalid_http_policy(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        HttpLimits(**kwargs)


def test_database_timeouts_are_injectable_and_validated(tmp_path: Path) -> None:
    from ihda_server.database import make_engine

    policy = DatabaseTimeouts(connect_seconds=4, statement_ms=5000, lock_ms=1234)
    assert policy.postgres_options == "-c statement_timeout=5000 -c lock_timeout=1234"
    engine = make_engine("sqlite:///" + str(tmp_path / "policy.db"), timeouts=policy)
    try:
        with engine.connect() as connection:
            assert (
                connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 1234
            )
    finally:
        engine.dispose()
    with pytest.raises(ValueError):
        DatabaseTimeouts(statement_ms=-1)
    with pytest.raises(ValueError):
        DatabaseTimeouts(connect_seconds=0)


def test_http_policy_applies_response_size_limit() -> None:
    from io import BytesIO

    from libs.team.client import HttpTransport
    from libs.team.contracts import TeamError

    class Opener:
        def open(self, *args: Any, **kwargs: Any) -> BytesIO:
            return BytesIO(b'{"value":"long"}')

    transport = HttpTransport(
        "http://localhost", lambda: "test-token", limits=HttpLimits(response_bytes=4)
    )
    transport._opener = Opener()  # type: ignore[assignment]
    with pytest.raises(TeamError, match="too large"):
        transport.request("GET", "/test")


def test_copy_workflow_uses_journal_port_for_uncertain_replay() -> None:
    from libs.team.contracts import Command, Unavailable
    from libs.team.copy_workflow import CopyTransfer

    origin = {"library_uuid": str(uuid4()), "asset_uuid": str(uuid4())}
    blob = Blob(hashlib.sha256(b"hda").hexdigest(), 3, "water.hda")
    plan = {
        "values": {
            "name": "Water",
            "category": "sop",
            "note": "",
            "tags": [],
            "origin": origin,
            "versions": [
                {
                    "origin": {
                        "version_uuid": str(uuid4()),
                        "version": "1",
                        "created_at": "2026",
                        "created_by": "user",
                    },
                    "values": {"version": "1", "files": {"asset": asdict(blob)}},
                }
            ],
        },
        "paths": {},
        "warnings": [],
    }

    class Journal:
        def __init__(self) -> None:
            self.origin = origin
            self.state: dict[str, Any] | None = None
            self.held = False

        @contextmanager
        def locked(self) -> Iterator[None]:
            assert not self.held
            self.held = True
            try:
                yield
            finally:
                self.held = False

        def load(self) -> dict[str, Any] | None:
            assert self.held
            return self.state

        def save(self, state: dict[str, Any]) -> None:
            assert self.held
            self.state = json.loads(json.dumps(state))

        def discard_unsubmitted(self) -> None:
            raise NotImplementedError

    class Destination:
        identity = "test"

        def __init__(self) -> None:
            self.requests: list[str] = []

        def check(self, values: dict[str, Any]) -> dict[str, Any]:
            return {"source_match": None, "name_conflict": None}

        def has_blob(self, blob: dict[str, Any]) -> bool:
            return True

        def upload(self, path: Path) -> Blob:
            raise AssertionError("Existing content must be reused")

        def execute(self, command: Command) -> dict[str, Any]:
            self.requests.append(command.request_id)
            if len(self.requests) == 1:
                raise Unavailable("Lost reply")
            return {"id": 1, "name": "Water"}

    journal, destination = Journal(), Destination()
    workflow = CopyTransfer(destination, journal)
    with pytest.raises(Unavailable):
        workflow.run(plan)
    assert not journal.held
    assert workflow.run(plan)["name"] == "Water"
    assert destination.requests[0] == destination.requests[1]
    assert not journal.held


def test_copy_workflow_does_not_import_concrete_adapters() -> None:
    import ast

    module = Path(__file__).resolve().parents[1] / "libs/team/copy_workflow.py"
    imports = {
        node.module
        for node in ast.walk(ast.parse(module.read_text()))
        if isinstance(node, ast.ImportFrom)
    }
    assert not imports.intersection(
        {
            "libs.team.client",
            "libs.team.copy_journal",
            "libs.team.copy_destination",
            "libs.operation_journal",
            "sqlite3",
        }
    )
