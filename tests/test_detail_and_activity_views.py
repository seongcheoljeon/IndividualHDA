"""Detail dialog renders escaped key/value rows; activity is a table model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtWidgets

import icons_rc  # noqa: F401  (the fallback thumbnail lives in the main resources)


def test_detail_view_escapes_values_and_offers_copy_buttons(
    app: Any, monkeypatch: Any
) -> None:
    from widgets.detail_view import detail_view as module
    from widgets.detail_view.presenter import DetailContent

    copied: list[str] = []
    monkeypatch.setattr(module, "copy_to_clipboard", copied.append)
    dialog = module.DetailView()
    dialog.show_content(
        DetailContent(
            (("HDA NAME", "<b>Water</b>"), ("HDA VERSION", "1.0")),
            None,
            {"Name": "<b>Water</b>", "Version": "1.0"},
        )
    )
    html = dialog.textBrowser__detail.toHtml()
    assert "&lt;b&gt;Water&lt;/b&gt;" in html and "<b>Water</b>" not in html
    assert dialog.textBrowser__detail.toPlainText().strip().startswith("HDA NAME")
    assert dialog.pushButton__copy_name.isEnabled()
    assert not dialog.pushButton__copy_path.isEnabled()
    dialog.pushButton__copy_name.click()
    dialog.pushButton__copy_path.click()  # disabled: nothing happens
    dialog.pushButton__copy_version.click()
    assert copied == ["<b>Water</b>", "1.0"]
    pixmap = dialog.label__pixmap.pixmap()
    assert not pixmap.isNull() and pixmap.width() <= 600 and pixmap.height() <= 600
    dialog.close()
    dialog.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_activity_model_exposes_rows_and_headers(app: Any) -> None:
    from widgets.library_metadata.activity_model import HEADERS, ActivityModel

    model = ActivityModel()
    assert model.rowCount() == 0 and model.columnCount() == len(HEADERS)
    model.set_rows(
        [("t1", "Kim", "Renamed", "rename"), ("1.0", "", "File", "a.ihda · ok")]
    )
    assert model.rowCount() == 2
    assert model.index(0, 2).data() == "Renamed"
    assert model.index(1, 3).data(QtCore.Qt.ItemDataRole.ToolTipRole) == "a.ihda · ok"
    assert [
        model.headerData(i, QtCore.Qt.Orientation.Horizontal) for i in range(4)
    ] == list(HEADERS)
    assert model.index(0, 0).data(QtCore.Qt.ItemDataRole.DecorationRole) is None
    view = QtWidgets.QTableView()
    view.setModel(model)
    assert view.model().rowCount() == 2
    _ = Path  # keep the import meaningful for readers extending with file rows
