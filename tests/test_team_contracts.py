"""The Operation literal is the single list of team operations."""

from __future__ import annotations

from typing import get_args

import pytest

from libs.team.contracts import Command, Operation, TeamError


def test_every_declared_operation_passes_the_unknown_operation_gate() -> None:
    for operation in get_args(Operation):
        try:
            Command(operation, asset_id=1, expected_revision=1).validate()
        except TeamError as error:
            # Field validation may still complain; the name itself must be known.
            assert "Unknown operation" not in str(error), operation


def test_undeclared_operations_are_rejected() -> None:
    with pytest.raises(TeamError, match="Unknown operation"):
        Command("bogus", asset_id=1, expected_revision=1).validate()  # type: ignore[arg-type]
