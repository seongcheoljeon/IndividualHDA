from __future__ import annotations

from typing import Any
import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_test_config = tempfile.TemporaryDirectory(prefix="ihda-tests-")
os.environ["IHDA_CONFIG_DIR"] = _test_config.name

import pytest


@pytest.fixture(scope="session")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
