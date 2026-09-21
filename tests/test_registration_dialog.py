"""The registration form gates Register on validity; the team action uses it."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtWidgets

from libs.registration_request import RegistrationRequest
from widgets.registration_dialog import RegistrationDialog


def test_dialog_validates_as_you_type_and_locks_identity_for_versions(app: Any) -> None:
    dialog = RegistrationDialog(
        None,
        title="Register asset",
        request=RegistrationRequest("water", "sop", "1.0"),
        categories=["obj", "sop"],
        taken=lambda name, cate: "taken" if name == "fire" else None,
        file=Path("/tmp/water.hda"),
    )
    assert dialog.pushButton__register.isEnabled() and dialog.label__errors.isHidden()
    assert dialog.pushButton__register.text() == "Register"
    assert [dialog.comboBox__category.itemText(i) for i in range(2)] == ["obj", "sop"]
    dialog.lineEdit__name.setText("fire")
    assert not dialog.pushButton__register.isEnabled()
    assert dialog.label__errors.text() == "taken"
    dialog.lineEdit__name.setText("1fire")
    dialog.lineEdit__version.setText("x")
    assert dialog.label__errors.text().splitlines() == [
        "The first character cannot be a number.",
        "Version must be a number like 1.0.",
    ]
    dialog.accept()  # ignored while invalid
    assert dialog.result() == 0
    dialog.lineEdit__name.setText("fire presets")
    dialog.lineEdit__version.setText("2.0")
    dialog.plainTextEdit__description.setPlainText(" added smoke ")
    assert dialog.request() == RegistrationRequest(
        "fire_presets", "sop", "2.0", "added smoke"
    )
    dialog.accept()
    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted

    version = RegistrationDialog(
        None,
        title="New version",
        request=RegistrationRequest("Water", "sop", "1.1"),
        lock_identity=True,
    )
    assert version.pushButton__register.text() == "Update"
    assert (
        version.lineEdit__name.isReadOnly()
        and not version.comboBox__category.isEnabled()
    )
    assert version.request().version == "1.1"


@pytest.mark.parametrize("new_version", [False, True])
def test_team_register_file_uses_the_form(
    app: Any, monkeypatch: pytest.MonkeyPatch, new_version: bool
) -> None:
    from widgets.team_library import actions as module

    window = QtWidgets.QWidget()
    registered: list[Any] = []
    rows = [SimpleNamespace(hda_name="Water", hda_cate="sop")]
    library = SimpleNamespace(
        presenter=SimpleNamespace(register=lambda *a, **k: registered.append((a, k))),
        writable=True,
        busy=False,
        bindings=SimpleNamespace(
            parent=window,
            selection=SimpleNamespace(
                state=SimpleNamespace(
                    asset=SimpleNamespace(
                        name="Water",
                        cate="sop",
                        data=SimpleNamespace(hda_version="1.0"),
                    )
                )
            ),
            models=SimpleNamespace(assets=SimpleNamespace(rows=rows)),
        ),
    )
    actions = module.MainAssetActions(library)  # type: ignore[arg-type]
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *a, **k: ("/tmp/fire.hda", "")
    )
    seen: list[RegistrationDialog] = []

    def fake_exec(self: RegistrationDialog) -> int:
        seen.append(self)
        if not new_version:
            assert self.pushButton__register.isEnabled()  # "fire" is new
            self.lineEdit__name.setText("Water")
            assert not self.pushButton__register.isEnabled()  # duplicate
            assert (
                self.label__errors.text()
                == "That name already exists in this category."
            )
            self.lineEdit__name.setText("fire")
        self.plainTextEdit__description.setPlainText("desc")
        return int(QtWidgets.QDialog.DialogCode.Accepted)

    monkeypatch.setattr(RegistrationDialog, "exec", fake_exec)
    actions.register_file(new_version=new_version)
    assert len(seen) == 1
    (path, name, category, version, metadata), kwargs = registered[0]
    assert path == Path("/tmp/fire.hda") and metadata == {}
    assert kwargs == {"new_version": new_version, "description": "desc"}
    if new_version:
        assert (name, category, version) == ("Water", "sop", "1.1")
        assert seen[0].lineEdit__name.isReadOnly()
    else:
        assert (name, category, version) == ("fire", "sop", "1.0")
