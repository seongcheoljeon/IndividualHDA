"""Asset-browser widgets and Qt model presentation, built directly in Python."""

from __future__ import annotations

from functools import partial

from PySide6 import QtCore, QtGui, QtWidgets

import icons_rc  # noqa: F401 (register bundled icons)
from libs.browser_search import SearchRequest
from libs.qt_helpers import wildcard_expression
from model.proxy_filters import AssetProxyModel
from view.ihda_list_view import ListView
from view.ihda_table_view import TableView
from widgets.asset_browser.state import AssetViewMode
from widgets.ui_tokens import (
    COMPACT_MARGIN,
    PANEL_SPACING,
    SEARCH_SPACING,
    TOOLBAR_ICON_SIZE,
    TOOLBAR_SPACING,
)


class AssetBrowserView(QtWidgets.QWidget):
    text_changed = QtCore.Signal(str)
    options_changed = QtCore.Signal()
    asset_selected = QtCore.Signal(object)  # asset ID or None
    error_reported = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("widget__asset_browser")
        self._asset_proxy_models: tuple[AssetProxyModel, ...] = ()
        browser_layout = QtWidgets.QVBoxLayout(self)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(PANEL_SPACING)
        self.splitter__ihda_whole_vertical = QtWidgets.QSplitter(
            QtCore.Qt.Orientation.Vertical, self
        )
        self.splitter__ihda_whole_vertical.setObjectName(
            "splitter__ihda_whole_vertical"
        )
        self.splitter__ihda_whole_vertical.setHandleWidth(3)
        browser_layout.addWidget(self.splitter__ihda_whole_vertical)
        controls_widget = QtWidgets.QWidget(self.splitter__ihda_whole_vertical)
        controls_widget.setObjectName("widget__asset_browser_controls")
        layout = QtWidgets.QVBoxLayout(controls_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PANEL_SPACING)
        layout.addLayout(self._build_toolbar(controls_widget))
        layout.addLayout(self._build_search_row(controls_widget))
        self.label__search_status = QtWidgets.QLabel(controls_widget)
        self.label__search_status.setObjectName("label__search_status")
        self.label__search_status.hide()
        layout.addWidget(self.label__search_status)

        self.stackedWidget__hda = QtWidgets.QStackedWidget(
            self.splitter__ihda_whole_vertical
        )
        self.stackedWidget__hda.setObjectName("stackedWidget__hda")
        self.listView__hda = ListView(self)
        self.tableView__hda = TableView(self)
        self.listView__hda.setObjectName("listView__hda")
        self.tableView__hda.setObjectName("tableView__hda")
        self.verticalLayout__listview = self._page("page__hda_list", self.listView__hda)
        self.verticalLayout__tableview = self._page(
            "page__hda_table", self.tableView__hda
        )
        self.verticalLayout__listview.setObjectName("verticalLayout__listview")
        self.verticalLayout__tableview.setObjectName("verticalLayout__tableview")
        self.label__hda_count = QtWidgets.QLabel("0", self)
        self.label__hda_count.setObjectName("label__hda_count")
        self.label__hda_count.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        browser_layout.addWidget(self.label__hda_count)
        self._view_mode_buttons.idClicked.connect(self.set_view_mode)
        self.lineEdit__search_hda.textChanged.connect(self.text_changed)
        self.comboBox__search_type.currentIndexChanged.connect(self.options_changed)
        self.checkBox__casesensitive_hda.toggled.connect(self.options_changed)

    def _build_toolbar(
        self, controls_widget: QtWidgets.QWidget
    ) -> QtWidgets.QHBoxLayout:
        toolbar_layout = QtWidgets.QHBoxLayout()
        toolbar_layout.setContentsMargins(COMPACT_MARGIN, 0, COMPACT_MARGIN, 0)
        toolbar_layout.setSpacing(TOOLBAR_SPACING)
        self.pushButton__favorite_node = self._button(
            "favorite_node",
            "ic_favorite_border_white.png",
            "Shows Favorite Nodes",
            True,
        )
        self.pushButton__thumbnail = self._button(
            "thumbnail", "network_sop.png", "Shows Thumbnails iHDA", True
        )
        toolbar_layout.addWidget(self.pushButton__favorite_node)
        toolbar_layout.addWidget(self.pushButton__thumbnail)
        toolbar_layout.addStretch()
        self.comboBox__library_source = QtWidgets.QComboBox(controls_widget)
        self.comboBox__library_source.setObjectName("comboBox__library_source")
        self.comboBox__library_source.setToolTip("Active library")
        self.comboBox__library_source.setMaximumWidth(220)
        self.comboBox__library_source.addItem("Personal", "personal")
        self.comboBox__library_source.addItem("Connect team…", "connect")
        toolbar_layout.addWidget(self.comboBox__library_source)

        self.pushButton__zoomin = self._button(
            "zoomin", "ic_zoom_in_white.png", "Zoom In"
        )
        self.pushButton__zoomout = self._button(
            "zoomout", "ic_zoom_out_white.png", "Zoom Out"
        )
        toolbar_layout.addWidget(self.pushButton__zoomin)
        toolbar_layout.addWidget(self.pushButton__zoomout)
        self.doubleSpinBox__zoom = QtWidgets.QDoubleSpinBox(controls_widget)
        self.doubleSpinBox__zoom.setObjectName("doubleSpinBox__zoom")
        self.doubleSpinBox__zoom.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.doubleSpinBox__zoom.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.doubleSpinBox__zoom.setSuffix("%")
        self.doubleSpinBox__zoom.setDecimals(0)
        self.doubleSpinBox__zoom.setRange(10, 500)
        self.doubleSpinBox__zoom.setSingleStep(10)
        self.doubleSpinBox__zoom.setValue(100)
        toolbar_layout.addWidget(self.doubleSpinBox__zoom)
        separator = QtWidgets.QFrame(controls_widget)
        separator.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        toolbar_layout.addWidget(separator)
        self.pushButton__icon_mode = self._button(
            "icon_mode", "ic_widgets_white.png", "Icon View", True
        )
        self.pushButton__table_mode = self._button(
            "table_mode", "ic_format_list_numbered_white.png", "Table View", True
        )
        self._view_mode_buttons = QtWidgets.QButtonGroup(self)
        self._view_mode_buttons.addButton(
            self.pushButton__icon_mode, AssetViewMode.ICON
        )
        self._view_mode_buttons.addButton(
            self.pushButton__table_mode, AssetViewMode.TABLE
        )
        self.pushButton__icon_mode.setChecked(True)
        toolbar_layout.addWidget(self.pushButton__icon_mode)
        toolbar_layout.addWidget(self.pushButton__table_mode)

        return toolbar_layout

    def _build_search_row(
        self, controls_widget: QtWidgets.QWidget
    ) -> QtWidgets.QHBoxLayout:
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setContentsMargins(COMPACT_MARGIN, 0, COMPACT_MARGIN, 0)
        search_layout.setSpacing(SEARCH_SPACING)
        self.comboBox__search_type = QtWidgets.QComboBox(controls_widget)
        self.comboBox__search_type.setObjectName("comboBox__search_type")
        self.comboBox__search_type.setFrame(False)
        self.comboBox__search_type.setToolTip("Search Type")
        self.comboBox__search_type.addItems(["Name", "Tags", "Type", "Note", "All"])
        self.checkBox__casesensitive_hda = QtWidgets.QCheckBox(controls_widget)
        self.checkBox__casesensitive_hda.setObjectName("checkBox__casesensitive_hda")
        self.checkBox__casesensitive_hda.setToolTip("Word Case Sensitive")
        self.checkBox__casesensitive_hda.setIcon(
            QtGui.QIcon(":/main/icons/case_sensitive.png")
        )
        self.checkBox__casesensitive_hda.setIconSize(
            QtCore.QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.lineEdit__search_hda = QtWidgets.QLineEdit(controls_widget)
        self.lineEdit__search_hda.setObjectName("lineEdit__search_hda")
        self.lineEdit__search_hda.setFrame(False)
        self.lineEdit__search_hda.setPlaceholderText("ex) create_velocity")
        self.lineEdit__search_hda.setClearButtonEnabled(True)
        self.lineEdit__search_hda.setStatusTip("Please enter your search term")
        search_layout.addWidget(self.comboBox__search_type)
        search_layout.addWidget(self.checkBox__casesensitive_hda)
        search_layout.addWidget(self.lineEdit__search_hda)
        return search_layout

    def _button(
        self, name: str, icon: str, tip: str, checkable: bool = False
    ) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(self)
        button.setObjectName(f"pushButton__{name}")
        button.setIcon(QtGui.QIcon(f":/main/icons/{icon}"))
        button.setIconSize(QtCore.QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        button.setToolTip(tip)
        button.setStatusTip(tip)
        button.setFlat(True)
        button.setCheckable(checkable)
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        return button

    def _page(self, name: str, widget: QtWidgets.QWidget) -> QtWidgets.QVBoxLayout:
        page = QtWidgets.QWidget(self.stackedWidget__hda)
        page.setObjectName(name)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PANEL_SPACING)
        layout.addWidget(widget)
        self.stackedWidget__hda.addWidget(page)
        return layout

    def set_view_mode(self, mode: int) -> None:
        layout = {
            AssetViewMode.ICON: self.verticalLayout__listview,
            AssetViewMode.TABLE: self.verticalLayout__tableview,
        }[AssetViewMode(mode)]
        page = layout.parentWidget()
        if page is None:
            raise RuntimeError("Asset browser page is no longer attached")
        self.stackedWidget__hda.setCurrentWidget(page)

    def get_search_request(self) -> SearchRequest:
        return SearchRequest(
            self.lineEdit__search_hda.text(),
            self.comboBox__search_type.currentText(),
            self.checkBox__casesensitive_hda.isChecked(),
        )

    def bind_models(
        self, list_proxy: AssetProxyModel, table_proxy: AssetProxyModel
    ) -> None:
        self._asset_proxy_models = (list_proxy, table_proxy)
        # Keep model lifetimes tied to the browser, including headless embedding.
        for proxy_model in self._asset_proxy_models:
            if proxy_model.parent() is None:
                proxy_model.setParent(self)
            source_model = proxy_model.sourceModel()
            if source_model is not None and source_model.parent() is None:
                source_model.setParent(self)
        for widget, proxy in zip(
            (self.listView__hda, self.tableView__hda),
            self._asset_proxy_models,
            strict=True,
        ):
            if widget.model() is not proxy:
                widget.setModel(proxy)
            selection = widget.selectionModel()
            selection.selectionChanged.connect(partial(self._selection_changed, proxy))
            widget.clicked.connect(partial(self._selected, proxy))
            proxy.modelReset.connect(self.update_count)
            proxy.rowsInserted.connect(self.update_count)
            proxy.rowsRemoved.connect(self.update_count)
            proxy.layoutChanged.connect(self.update_count)
        self.update_count()

    def _selection_changed(
        self,
        proxy: AssetProxyModel,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ) -> None:
        indexes = selected.indexes()
        self._selected(proxy, indexes[0] if indexes else QtCore.QModelIndex())

    def _selected(self, proxy: AssetProxyModel, index: QtCore.QModelIndex) -> None:
        asset_id = (
            index.data(proxy.id_role)
            if index.isValid() and proxy.id_role is not None
            else None
        )
        self.asset_selected.emit(asset_id)

    def update_count(self) -> None:
        if self._asset_proxy_models:
            self.label__hda_count.setText(str(self._asset_proxy_models[0].rowCount()))

    def show_results(self, ids: frozenset[int]) -> None:
        for proxy in self._asset_proxy_models:
            proxy.setFilterRegularExpression("")
            proxy.set_id_filter(ids)
        self.update_count()

    def filter_text(self, request: SearchRequest) -> None:
        sensitivity = (
            QtCore.Qt.CaseSensitivity.CaseSensitive
            if request.case_sensitive
            else QtCore.Qt.CaseSensitivity.CaseInsensitive
        )
        for proxy in self._asset_proxy_models:
            proxy.set_search_field(request.field)
            proxy.set_id_filter(None)
            proxy.setFilterRegularExpression(
                wildcard_expression(request.text, sensitivity)
            )
        self.update_count()

    def show_busy(self, busy: bool) -> None:
        self.label__search_status.setText("Searching…" if busy else "")
        self.label__search_status.setVisible(busy)

    def show_error(self, message: str) -> None:
        self.label__search_status.setText(message)
        self.label__search_status.setVisible(bool(message))
        if message:
            self.error_reported.emit(message)
