"""Who is using the library. No Qt, HOM or database imports."""

from __future__ import annotations

import getpass
import os
from collections.abc import Sequence


def current_user() -> str:
    """Studio pipelines set IHDA_USER; otherwise the OS login name."""
    return os.environ.get("IHDA_USER", "").strip() or getpass.getuser()


def resolve_local_user(existing: Sequence[str]) -> str:
    """A local SQLite library belongs to one person: adopt its existing user row.

    Libraries created before identity existed hold a single "anonymous" row; keeping
    that name means no data migration and no orphaned assets. A fresh library gets
    the current user. Several rows only happen for hand-edited databases: prefer
    the current user if present, else the first one.
    """
    if len(existing) == 1:
        return existing[0]
    user = current_user()
    if not existing or user in existing:
        return user
    return sorted(existing)[0]
