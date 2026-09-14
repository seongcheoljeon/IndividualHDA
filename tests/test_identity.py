from __future__ import annotations

import getpass

import pytest

from libs import identity


def test_current_user_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHDA_USER", " jeon ")
    assert identity.current_user() == "jeon"
    monkeypatch.setenv("IHDA_USER", "")
    assert identity.current_user() == getpass.getuser()


def test_local_user_adopts_single_existing_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IHDA_USER", "jeon")
    assert identity.resolve_local_user(["anonymous"]) == "anonymous"
    assert identity.resolve_local_user([]) == "jeon"
    assert identity.resolve_local_user(["a", "jeon"]) == "jeon"
    assert identity.resolve_local_user(["b", "a"]) == "a"
