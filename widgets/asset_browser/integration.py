"""Compose the asset browser; retain persisted control names in the panel layout."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6 import QtWidgets

from libs.asset_search import AssetSearch
from libs.browser_search import AssetSearchGateway, SearchPolicy, SearchRepository
from libs.debounce import DebouncedText
from model.proxy_filters import AssetProxyModel
from widgets.asset_browser.presenter import AssetBrowserPresenter
from widgets.asset_browser.view import AssetBrowserView


@dataclass(frozen=True, slots=True, kw_only=True)
class BrowserBindings:
    host: QtWidgets.QWidget
    counter_host: QtWidgets.QWidget
    row_count: Callable[[], int]
    failed: Callable[[str], None]


@dataclass(frozen=True, slots=True, kw_only=True)
class BrowserActions:
    selected: Callable[[Any], None]
    double_clicked: Callable[[Any], None]
    context_menu: Callable[[Any], None]
    dropped: Callable[[Any], None]
    mouse_moved: Callable[[Any], None]


class AssetBrowserIntegration:
    def __init__(
        self,
        bindings: BrowserBindings,
        executor: AssetSearch,
        gateway_factory: Callable[[SearchRepository], AssetSearchGateway],
        *,
        search_policy: SearchPolicy = SearchPolicy(),
    ) -> None:
        self.view = AssetBrowserView(bindings.host)
        layout = QtWidgets.QVBoxLayout(bindings.host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        # Keep the counter beside the existing tags/user footer.
        counter_layout = QtWidgets.QHBoxLayout(bindings.counter_host)
        counter_layout.setContentsMargins(0, 0, 0, 0)
        counter_layout.addWidget(self.view.label__hda_count)
        self._gateway_factory = gateway_factory
        self.presenter = AssetBrowserPresenter(self.view, executor)
        self.debounce = DebouncedText(
            self.search,
            self.view,
            delay=search_policy.delay_ms,
            immediate=lambda: bindings.row_count() < search_policy.immediate_rows,
        )
        executor.results.connect(self.presenter.results)
        executor.failed.connect(self.presenter.failed)
        self.view.error_reported.connect(bindings.failed)

    def connect(
        self,
        list_model: AssetProxyModel,
        table_model: AssetProxyModel,
        actions: BrowserActions,
    ) -> None:
        self.view.bind_models(list_model, table_model)
        self.view.text_changed.connect(self._text_changed)
        self.view.options_changed.connect(self.refresh)
        self.view.asset_selected.connect(
            lambda asset_id: self._selected(actions.selected, asset_id)
        )
        # Host actions still operate on the existing custom views and selection.
        for widget in (self.view.listView__hda, self.view.tableView__hda):
            widget.doubleClicked.connect(actions.double_clicked)
            widget.customContextMenuRequested.connect(actions.context_menu)
            widget.signal.signal_object.connect(actions.dropped)
            widget.signal.mouse_signal_object.connect(actions.mouse_moved)

    def _selected(self, selected: Callable[[Any], None], asset_id: int | None) -> None:
        if asset_id is None:
            return
        widgets = (self.view.listView__hda, self.view.tableView__hda)
        active = (
            self.view.tableView__hda
            if self.view.stackedWidget__hda.currentWidget()
            is self.view.verticalLayout__tableview.parentWidget()
            else self.view.listView__hda
        )
        for widget in (active, *widgets):
            model = widget.model()
            if not isinstance(model, AssetProxyModel) or model.id_role is None:
                continue
            for index in widget.selectionModel().selectedIndexes():
                if index.data(model.id_role) == asset_id:
                    selected(index)
                    return

    def _text_changed(self, text: str) -> None:
        self.presenter.invalidate()
        if not text.strip():
            self.refresh()
        else:
            self.debounce.submit(text)

    def search(self, text: str) -> None:
        # The current controls are authoritative; debounce never replays old options.
        self.presenter.search(self.view.get_search_request())

    def refresh(self) -> None:
        self.debounce.timer.stop()
        self.search(self.view.lineEdit__search_hda.text())

    def change_repository(self, repository: SearchRepository | None) -> None:
        self.debounce.timer.stop()
        gateway = self._gateway_factory(repository) if repository is not None else None
        self.presenter.change_gateway(gateway)

    def close(self) -> None:
        self.debounce.timer.stop()
        self.presenter.close()
