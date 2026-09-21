"""What a registration asks the user for, and whether the answer is usable.

Shared by the personal update prompt and the team file registration; no Qt.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation

from libs.asset_names import validate_name

Taken = Callable[[str, str], str | None]  # (name, category) -> why it is unavailable


@dataclass(frozen=True)
class RegistrationRequest:
    name: str
    category: str
    version: str
    description: str = ""

    def normalized(self) -> RegistrationRequest:
        return replace(
            self,
            name=self.name.strip().replace(" ", "_"),
            category=self.category.strip(),
            version=self.version.strip(),
            description=self.description.strip(),
        )


def bump_version(version: str) -> str:
    """The next minor version: 1.0 -> 1.1, 2.9 -> 3.0; unparsable input -> 1.0."""
    try:
        return str(Decimal(version.strip()) + Decimal("0.1"))
    except (InvalidOperation, ValueError, AttributeError):
        return "1.0"


def validate(request: RegistrationRequest, *, taken: Taken | None = None) -> list[str]:
    """Every reason the request cannot be registered yet; empty means go."""
    request = request.normalized()
    errors: list[str] = []
    check = validate_name(request.name, old_name="")
    if not check.valid:
        errors.append(check.error)
    if not request.category:
        errors.append("Choose a category.")
    try:
        if Decimal(request.version) <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        errors.append("Version must be a number like 1.0.")
    if taken is not None and check.valid and request.category:
        reason = taken(request.name, request.category)
        if reason:
            errors.append(reason)
    return errors
