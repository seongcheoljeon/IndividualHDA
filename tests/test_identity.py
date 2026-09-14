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


def test_library_context_from_preference(tmp_path: object) -> None:
    from pathlib import Path
    from types import SimpleNamespace

    from libs.domain import LibraryContext

    invalid = SimpleNamespace(is_data_valid=False, data_dirpath=Path("x"))
    assert LibraryContext.from_preference(invalid, "jeon") is None
    valid = SimpleNamespace(is_data_valid=True, data_dirpath=Path(str(tmp_path)))
    context = LibraryContext.from_preference(valid, "jeon")
    assert context is not None
    assert context.db_filepath == Path(str(tmp_path)) / "ihda.db"
    assert context.hda_base_dirpath == context.asset_root / "jeon"
    assert context.asset_root.is_relative_to(context.data_dirpath)
