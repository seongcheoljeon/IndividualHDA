"""Temporary compatibility boundary for the remaining main-window mixins.

Only this adapter installs legacy main-window aliases. New features use the
View and Presenter interfaces instead. Delete aliases as their consumers migrate.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6 import QtWidgets

from libs.asset_search import AssetSearch
from libs.browser_search import AssetSearchGateway, SearchRepository
from libs.debounce import DebouncedText
from model.proxy_filters import AssetProxyModel
from widgets.asset_browser.presenter import AssetBrowserPresenter
from widgets.asset_browser.view import AssetBrowserView


class AssetBrowserIntegration:
    def __init__(
        self,
        window: Any,
        executor: AssetSearch,
        gateway_factory: Callable[[SearchRepository], AssetSearchGateway],
    ) -> None:
        self.view = AssetBrowserView(window.widget__asset_browser_host)
        layout = QtWidgets.QVBoxLayout(window.widget__asset_browser_host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        # Keep the counter beside the existing tags/user footer.
        counter_layout = QtWidgets.QHBoxLayout(window.widget__asset_count_host)
        counter_layout.setContentsMargins(0, 0, 0, 0)
        counter_layout.addWidget(self.view.label__hda_count)
        self._gateway_factory = gateway_factory
        self.presenter = AssetBrowserPresenter(self.view, executor)
        self.debounce = DebouncedText(
            self.search,
            self.view,
            immediate=lambda: (
                window._ihda_list_model is not None
                and window._ihda_list_model.rowCount() < 1000
            ),
        )
        executor.results.connect(self.presenter.results)
        executor.failed.connect(self.presenter.failed)
        self.view.error_reported.connect(window._asset_search_failed_message)
        self._install_aliases(window)

    def _install_aliases(self, window: Any) -> None:
        aliases = {
            "splitter__ihda_whole_vertical": self.view.splitter__ihda_whole_vertical,
            "stackedWidget__hda": self.view.stackedWidget__hda,
            "verticalLayout__listview": self.view.verticalLayout__listview,
            "verticalLayout__tableview": self.view.verticalLayout__tableview,
            "pushButton__favorite_node": self.view.pushButton__favorite_node,
            "pushButton__thumbnail": self.view.pushButton__thumbnail,
            "pushButton__zoomin": self.view.pushButton__zoomin,
            "pushButton__zoomout": self.view.pushButton__zoomout,
            "doubleSpinBox__zoom": self.view.doubleSpinBox__zoom,
            "pushButton__icon_mode": self.view.pushButton__icon_mode,
            "pushButton__table_mode": self.view.pushButton__table_mode,
            "comboBox__search_type": self.view.comboBox__search_type,
            "checkBox__casesensitive_hda": self.view.checkBox__casesensitive_hda,
            "lineEdit__search_hda": self.view.lineEdit__search_hda,
            "label__hda_count": self.view.label__hda_count,
        }
        for name, widget in aliases.items():
            setattr(window, name, widget)

    def connect(self, window: Any) -> None:
        self.view.bind_models(
            window._ihda_list_proxy_model, window._ihda_table_proxy_model
        )
        self.view.text_changed.connect(self._text_changed)
        self.view.options_changed.connect(self.refresh)
        self.view.asset_selected.connect(
            lambda asset_id: self._selected(window, asset_id)
        )
        # Host actions still operate on the existing custom views and selection.
        for widget in (self.view.listView__hda, self.view.tableView__hda):
            widget.doubleClicked.connect(window._slot_hda_double_clicked)
            widget.customContextMenuRequested.connect(window._build_context_ihda_menu)
            widget.signal.signal_object.connect(window._slot_drop_node_into_hda_view)
            widget.signal.mouse_signal_object.connect(
                window._slot_mouse_move_event_on_houdini
            )

    def _selected(self, window: Any, asset_id: int | None) -> None:
        if asset_id is None:
            return
        widgets = (self.view.listView__hda, self.view.tableView__hda)
        active = widgets[self.view.stackedWidget__hda.currentIndex()]
        for widget in (active, *widgets):
            model = widget.model()
            if not isinstance(model, AssetProxyModel) or model.id_role is None:
                continue
            for index in widget.selectionModel().selectedIndexes():
                if index.data(model.id_role) == asset_id:
                    window._slot_on_hda_item_clicked(index)
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
