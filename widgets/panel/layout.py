"""Code-built MainWindow layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import (
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QCursor,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTextBrowser,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import icons_rc  # noqa: F401 (register bundled icons)
from libs.ui_icons import Icon
from widgets.layout_helpers import main_window_text, make_font, size_policy
from widgets.panel.layout_category import build_category_panel
from widgets.panel.layout_history import (
    build_history_page,
)
from widgets.panel.layout_inside_nodes import build_inside_nodes
from widgets.panel.layout_scene_records import build_scene_records
from widgets.tag_editor import TagEditor
from widgets.ui_tokens import TOOLBAR_ICON_SIZE


class MainWindowLayout:
    # Persisted control names whose widgets are constructed by AssetBrowserView.
    splitter__ihda_whole_vertical: QtWidgets.QSplitter
    stackedWidget__hda: QtWidgets.QStackedWidget
    verticalLayout__listview: QtWidgets.QVBoxLayout
    verticalLayout__tableview: QtWidgets.QVBoxLayout
    pushButton__favorite_node: QtWidgets.QPushButton
    pushButton__thumbnail: QtWidgets.QPushButton
    pushButton__zoomin: QtWidgets.QPushButton
    pushButton__zoomout: QtWidgets.QPushButton
    doubleSpinBox__zoom: QtWidgets.QDoubleSpinBox
    pushButton__icon_mode: QtWidgets.QPushButton
    pushButton__table_mode: QtWidgets.QPushButton
    comboBox__search_type: QtWidgets.QComboBox
    checkBox__casesensitive_hda: QtWidgets.QCheckBox
    lineEdit__search_hda: QtWidgets.QLineEdit
    label__hda_count: QtWidgets.QLabel
    pushButton__ai_suggest: QtWidgets.QPushButton
    pushButton__ai_cancel: QtWidgets.QPushButton
    label__ai_status: QtWidgets.QLabel
    actionOpen_Log_Folder: QAction
    actionLocal_AI_Models: QAction

    # Widgets built by the page modules (layout_*.py); declared here so they are
    # members of the layout like the ones built in this file.
    checkBox__casesensitive_cate: QCheckBox
    checkBox__casesensitive_hda_hist: QCheckBox
    checkBox__hda_inside_connect_to_view: QCheckBox
    checkBox__hist_search_date: QCheckBox
    checkBox__record_only_current_hipfile: QCheckBox
    checkBox__record_only_current_ihda: QCheckBox
    comboBox__hda_inside_node: QComboBox
    comboBox__hist_ihda_node: QComboBox
    comboBox__search_field_hist: QComboBox
    dateEdit__hist_search_end: QDateEdit
    dateEdit__hist_search_start: QDateEdit
    horizontalLayout__category_count: QHBoxLayout
    horizontalLayout__category_search: QHBoxLayout
    horizontalLayout__history_count: QHBoxLayout
    horizontalLayout__history_date_filter: QHBoxLayout
    horizontalLayout__history_date_range: QHBoxLayout
    horizontalLayout__history_footer: QHBoxLayout
    horizontalLayout__history_query: QHBoxLayout
    horizontalLayout__history_search: QHBoxLayout
    horizontalLayout__inside_count: QHBoxLayout
    horizontalLayout__inside_search: QHBoxLayout
    horizontalLayout__scene_record_count: QHBoxLayout
    horizontalLayout__scene_record_search: QHBoxLayout
    label__cate_count: QLabel
    label__cate_count_suffix: QLabel
    label__found_hda_inside_hipfile: QLabel
    label__found_hda_inside_hipfile_count: QLabel
    label__hist_cnt: QLabel
    label__hist_cnt_suffix: QLabel
    line__history_filters: QFrame
    pushButton__hist_reset_filters: QPushButton
    label__hist_tag_pixmap: QLabel
    label__hist_tags: QLabel
    label__join_str: QLabel
    label__loc_record_count: QLabel
    label__loc_record_count_suffix: QLabel
    lineEdit__search_cate: QLineEdit
    lineEdit__search_found_hda_inside_node: QLineEdit
    lineEdit__search_hda_hist: QLineEdit
    lineEdit__search_record: QLineEdit
    page__category: QWidget
    page__hda_inside_hipfile: QWidget
    page__hda_loc_record: QWidget
    page__history: QWidget
    pushButton__cleanup_hda_record: QPushButton
    pushButton__hda_inside_node_refresh: QPushButton
    spacer__category_count: QSpacerItem
    spacer__history_footer: QSpacerItem
    spacer__history_search: QSpacerItem
    spacer__history_search_end: QSpacerItem
    spacer__history_search_middle: QSpacerItem
    spacer__inside_count: QSpacerItem
    spacer__inside_search: QSpacerItem
    spacer__scene_record_count: QSpacerItem
    spacer__scene_record_search: QSpacerItem
    splitter__cate_whole_vertical: QSplitter
    splitter__ihda_hist_whole_vertical: QSplitter
    stackedWidget__category: QStackedWidget
    verticalLayout__category: QVBoxLayout
    verticalLayout__category_page: QVBoxLayout
    verticalLayout__category_panel: QVBoxLayout
    verticalLayout__hda_inside_node: QVBoxLayout
    verticalLayout__hda_loc_record: QVBoxLayout
    verticalLayout__history: QVBoxLayout
    verticalLayout__history_content: QVBoxLayout
    verticalLayout__history_page: QVBoxLayout
    verticalLayout__inside_content: QVBoxLayout
    verticalLayout__inside_page: QVBoxLayout
    verticalLayout__scene_record_content: QVBoxLayout
    verticalLayout__scene_record_page: QVBoxLayout
    widget__category_panel: QWidget
    widget__category_search: QWidget
    widget__history_search: QWidget
    widget__history_view: QWidget

    def build_ui(self, window: QMainWindow) -> None:
        self._configure_window(window)
        self._build_application_actions(window)
        self._build_workspace_actions(window)
        self._build_houdini_actions(window)
        self._build_support_actions(window)
        self._build_shell(window)
        build_category_panel(self, window)
        self._build_browser_host(window)
        self._build_details_toolbar(window)
        self._build_note_and_tags(window)
        build_scene_records(self, window)
        build_inside_nodes(self, window)
        self._build_media_hosts(window)
        build_history_page(self, window)
        self._build_debug_console(window)
        self._build_menus_and_toolbar(window)

    def _configure_window(self, window: QMainWindow) -> None:
        if not window.objectName():
            window.setObjectName("MainWindow__individualHDA")
        window.resize(1472, 863)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(Icon.VIEWPORT_LOGO_TRANS))
        window.setWindowTitle(main_window_text("Individual HDA"))

    def _build_application_actions(self, window: QMainWindow) -> None:
        self.actionQuit = QAction(window)
        self.actionQuit.setObjectName("actionQuit")
        self.actionQuit.setIcon(QIcon(Icon.IC_CLEAR_WHITE))
        self.actionQuit.setText(main_window_text("Quit"))
        self.actionReload = QAction(window)
        self.actionReload.setObjectName("actionReload")
        self.actionReload.setIcon(QIcon(Icon.IC_REFRESH_WHITE))
        self.actionReload.setText(main_window_text("Reload"))
        self.actionReload.setToolTip(
            main_window_text("Reload the library from storage")
        )
        self.actionHelp = QAction(window)
        self.actionHelp.setObjectName("actionHelp")
        self.actionHelp.setIcon(QIcon(":/main/icons/ic_help_white.png"))
        self.actionHelp.setText(main_window_text("Help"))
        self.actionAbout = QAction(window)
        self.actionAbout.setObjectName("actionAbout")
        self.actionAbout.setIcon(QIcon(":/main/icons/ic_info_outline_white.png"))
        self.actionAbout.setText(main_window_text("About"))
        self.actionReset = QAction(window)
        self.actionReset.setObjectName("actionReset")
        self.actionReset.setIcon(QIcon(Icon.IC_RESTORE_PAGE_WHITE))
        self.actionReset.setText(main_window_text("Reset"))
        self.actionReset.setStatusTip(main_window_text("Initialize the property"))
        self.actionOpen_the_hda_directory = QAction(window)
        self.actionOpen_the_hda_directory.setObjectName("actionOpen_the_hda_directory")
        self.actionOpen_the_hda_directory.setIcon(QIcon(Icon.IC_FOLDER_WHITE))
        self.actionOpen_the_hda_directory.setText(
            main_window_text("Open the HDA directory...")
        )
        self.actionOpen_the_hda_directory.setStatusTip(
            main_window_text("Open the HDA directory path.")
        )
        self.actionLogin = QAction(window)
        self.actionLogin.setObjectName("actionLogin")
        self.actionLogin.setIcon(QIcon(":/main/icons/ic_account_box_white.png"))
        self.actionLogin.setText(main_window_text("Login"))
        self.actionLogout = QAction(window)
        self.actionLogout.setObjectName("actionLogout")
        self.actionLogout.setIcon(QIcon(":/main/icons/ic_account_box_white.png"))
        self.actionLogout.setText(main_window_text("Logout"))
        self.actionSubmit_a_Bug_Report = QAction(window)
        self.actionSubmit_a_Bug_Report.setObjectName("actionSubmit_a_Bug_Report")
        self.actionSubmit_a_Bug_Report.setIcon(QIcon(":/main/icons/ic_email_white.png"))
        self.actionSubmit_a_Bug_Report.setText(main_window_text("Submit a Bug Report"))
        self.actionSubmit_Feedback = QAction(window)
        self.actionSubmit_Feedback.setObjectName("actionSubmit_Feedback")
        self.actionSubmit_Feedback.setIcon(QIcon(":/main/icons/ic_send_white.png"))
        self.actionSubmit_Feedback.setText(main_window_text("Submit Feedback"))

    def _build_workspace_actions(self, window: QMainWindow) -> None:
        self.actioniHDA = QAction(window)
        self.actioniHDA.setObjectName("actioniHDA")
        self.actioniHDA.setCheckable(True)
        self.actioniHDA.setChecked(True)
        self.actioniHDA.setIcon(QIcon(Icon.HOUDINI_LOGO_WHITE))
        self.actioniHDA.setText(main_window_text("iHDA"))
        self.actioniHDA.setStatusTip(main_window_text("Show iHDA window."))
        self.actionVideo_Player = QAction(window)
        self.actionVideo_Player.setObjectName("actionVideo_Player")
        self.actionVideo_Player.setCheckable(True)
        self.actionVideo_Player.setIcon(QIcon(Icon.IC_MOVIE_WHITE))
        self.actionVideo_Player.setText(main_window_text("Video Player"))
        self.actionVideo_Player.setStatusTip(
            main_window_text("Show video player window.")
        )
        self.actionWeb = QAction(window)
        self.actionWeb.setObjectName("actionWeb")
        self.actionWeb.setCheckable(True)
        self.actionWeb.setIcon(QIcon(":/main/icons/ic_language_white.png"))
        self.actionWeb.setText(main_window_text("Web"))
        self.actionWeb.setStatusTip(main_window_text("Show web window."))
        self.actionCreate_Account = QAction(window)
        self.actionCreate_Account.setObjectName("actionCreate_Account")
        self.actionCreate_Account.setIcon(QIcon(":/main/icons/ic_group_white.png"))
        self.actionCreate_Account.setText(main_window_text("Create Account"))
        self.actionPreference = QAction(window)
        self.actionPreference.setObjectName("actionPreference")
        self.actionPreference.setIcon(QIcon(Icon.IC_BUILD_WHITE))
        self.actionPreference.setText(main_window_text("Preference"))
        self.actionPreference.setStatusTip(main_window_text("Setting iHDA preference."))
        self.actionImport_Data = QAction(window)
        self.actionImport_Data.setObjectName("actionImport_Data")
        self.actionImport_Data.setIcon(QIcon(":/main/icons/ic_unarchive_white.png"))
        self.actionImport_Data.setText(main_window_text("Import Data"))
        self.actionImport_Data.setStatusTip(main_window_text("Import iHDA data."))
        self.actionExport_Data = QAction(window)
        self.actionExport_Data.setObjectName("actionExport_Data")
        self.actionExport_Data.setIcon(QIcon(Icon.IC_ARCHIVE_WHITE))
        self.actionExport_Data.setText(main_window_text("Export Data"))
        self.actionExport_Data.setStatusTip(main_window_text("Export iHDA data."))
        self.actionDownload_FFmpeg = QAction(window)
        self.actionDownload_FFmpeg.setObjectName("actionDownload_FFmpeg")
        self.actionDownload_FFmpeg.setIcon(QIcon(":/main/icons/ic_language_white.png"))
        self.actionDownload_FFmpeg.setText(main_window_text("Download FFmpeg"))
        self.actionDownload_FFmpeg.setStatusTip(
            main_window_text("Go to the ffmpeg download site.")
        )
        self.actionHistory = QAction(window)
        self.actionHistory.setObjectName("actionHistory")
        self.actionHistory.setCheckable(True)
        self.actionHistory.setIcon(QIcon(Icon.IC_QUERY_BUILDER_WHITE))
        self.actionHistory.setText(main_window_text("History"))
        self.actionHistory.setStatusTip(main_window_text("Show iHDA history"))
        self.actionUpdate = QAction(window)
        self.actionUpdate.setObjectName("actionUpdate")
        self.actionUpdate.setIcon(QIcon(":/main/icons/ic_new_releases_white.png"))
        self.actionUpdate.setText(main_window_text("Update..."))
        self.actionFFmpeg = QAction(window)
        self.actionFFmpeg.setObjectName("actionFFmpeg")
        self.actionFFmpeg.setIcon(QIcon(Icon.IC_MOVIE_WHITE))
        self.actionFFmpeg.setText(main_window_text("FFmpeg"))
        self.actionFFmpeg.setToolTip(main_window_text("Download FFmpeg"))
        self.actionCodec = QAction(window)
        self.actionCodec.setObjectName("actionCodec")
        self.actionCodec.setIcon(QIcon(":/main/icons/cube.png"))
        self.actionCodec.setText(main_window_text("Codec"))
        self.actionCodec.setToolTip(main_window_text("Download Codec"))
        self.actionDelete_All = QAction(window)
        self.actionDelete_All.setObjectName("actionDelete_All")
        self.actionDelete_All.setIcon(QIcon(Icon.IC_DELETE_FOREVER_WHITE))
        self.actionDelete_All.setText(main_window_text("Delete All"))
        self.actionDelete_All.setStatusTip(main_window_text("Delete all iHDA history."))

    def _build_houdini_actions(self, window: QMainWindow) -> None:
        self.actionUnpack_Subnet = QAction(window)
        self.actionUnpack_Subnet.setObjectName("actionUnpack_Subnet")
        self.actionUnpack_Subnet.setCheckable(True)
        self.actionUnpack_Subnet.setIcon(QIcon(":/main/icons/unpack_subnet.png"))
        self.actionUnpack_Subnet.setText(main_window_text("Unpack Subnet"))
        self.actionUnpack_Subnet.setStatusTip(
            main_window_text("When you import a node, you unpack it and import it")
        )
        self.actionSticky_Note = QAction(window)
        self.actionSticky_Note.setObjectName("actionSticky_Note")
        self.actionSticky_Note.setCheckable(True)
        self.actionSticky_Note.setIcon(QIcon(":/main/icons/network_sticky.png"))
        self.actionSticky_Note.setText(main_window_text("Sticky Note"))
        self.actionSticky_Note.setToolTip(main_window_text("Note to Sticky Note"))
        self.actionSticky_Note.setStatusTip(
            main_window_text("Apply iHDA note contents to houdini sticky note")
        )
        self.actionComment = QAction(window)
        self.actionComment.setObjectName("actionComment")
        self.actionComment.setCheckable(True)
        self.actionComment.setIcon(QIcon(":/main/icons/ic_comment_white.png"))
        self.actionComment.setText(main_window_text("Comment"))
        self.actionComment.setToolTip(main_window_text("Houdini Node Comment"))
        self.actionComment.setStatusTip(
            main_window_text(
                "If true, simple iHDA information is entered as Houdini node description."
            )
        )
        self.actionNode_Synchronization = QAction(window)
        self.actionNode_Synchronization.setObjectName("actionNode_Synchronization")
        self.actionNode_Synchronization.setCheckable(True)
        self.actionNode_Synchronization.setIcon(
            QIcon(":/main/icons/ic_swap_vert_white.png")
        )
        self.actionNode_Synchronization.setText(
            main_window_text("Node Synchronization")
        )
        self.actionNode_Synchronization.setStatusTip(
            main_window_text(
                "When activated, the Houdini node and iHDA app are synchronized."
            )
        )
        self.actionNull = QAction(window)
        self.actionNull.setObjectName("actionNull")
        self.actionNull.setCheckable(True)
        self.actionNull.setChecked(True)
        self.actionNull.setIcon(QIcon(Icon.IC_CLEAR_WHITE))
        self.actionNull.setText(main_window_text("Null"))
        self.actionNull.setToolTip(main_window_text("Do not connect"))
        self.actionNull.setStatusTip(
            main_window_text(
                "It does not connect the node even if there is node connection information."
            )
        )
        self.actionInput = QAction(window)
        self.actionInput.setObjectName("actionInput")
        self.actionInput.setCheckable(True)
        self.actionInput.setIcon(
            QIcon(":/main/icons/ic_vertical_align_bottom_white.png")
        )
        self.actionInput.setText(main_window_text("Input"))
        self.actionInput.setToolTip(main_window_text("Input connection"))
        self.actionInput.setStatusTip(
            main_window_text("Connect only inputs from nodes")
        )
        self.actionOuput = QAction(window)
        self.actionOuput.setObjectName("actionOuput")
        self.actionOuput.setCheckable(True)
        self.actionOuput.setIcon(QIcon(":/main/icons/ic_vertical_align_top_white.png"))
        self.actionOuput.setText(main_window_text("Ouput"))
        self.actionOuput.setToolTip(main_window_text("Ouput connection"))
        self.actionOuput.setStatusTip(
            main_window_text("Connect only the output of the nodes.")
        )
        self.actionBoth = QAction(window)
        self.actionBoth.setObjectName("actionBoth")
        self.actionBoth.setCheckable(True)
        self.actionBoth.setIcon(
            QIcon(":/main/icons/ic_vertical_align_center_white.png")
        )
        self.actionBoth.setText(main_window_text("Both"))
        self.actionBoth.setToolTip(main_window_text("Both connections"))
        self.actionBoth.setStatusTip(
            main_window_text("Connect both input and output of nodes.")
        )
        self.actionCategory_Synchronization = QAction(window)
        self.actionCategory_Synchronization.setObjectName(
            "actionCategory_Synchronization"
        )
        self.actionCategory_Synchronization.setCheckable(True)
        self.actionCategory_Synchronization.setIcon(QIcon(Icon.IC_SWAP_HORIZ_WHITE))
        self.actionCategory_Synchronization.setText(
            main_window_text("Category Synchronization")
        )
        self.actionCategory_Synchronization.setToolTip(
            main_window_text("Category Synchronization")
        )
        self.actionCategory_Synchronization.setStatusTip(
            main_window_text(
                "Synchronize houdini category with current HDA category in real time"
            )
        )
        self.actionCleanup = QAction(window)
        self.actionCleanup.setObjectName("actionCleanup")
        self.actionCleanup.setIcon(QIcon(Icon.CLEAR))
        self.actionCleanup.setText(main_window_text("Clean up"))
        self.actionCleanup.setStatusTip(
            main_window_text("Clean up unnecessary data from the database.")
        )
        self.actionAutomatic_Name_Change = QAction(window)
        self.actionAutomatic_Name_Change.setObjectName("actionAutomatic_Name_Change")
        self.actionAutomatic_Name_Change.setCheckable(True)
        self.actionAutomatic_Name_Change.setChecked(True)
        self.actionAutomatic_Name_Change.setIcon(
            QIcon(":/main/icons/ic_text_format_white.png")
        )
        self.actionAutomatic_Name_Change.setText(
            main_window_text("Automatic Name Change")
        )
        self.actionAutomatic_Name_Change.setToolTip(
            main_window_text("Houdini node name is changed automatically")
        )
        self.actionAutomatic_Name_Change.setStatusTip(
            main_window_text(
                "When you select this option, the name that can cause errors when registering Houdini nodes to the iHDA app is automatically changed."
            )
        )

    def _build_support_actions(self, window: QMainWindow) -> None:
        self.actionSystem_Info = QAction(window)
        self.actionSystem_Info.setObjectName("actionSystem_Info")
        self.actionSystem_Info.setIcon(QIcon(":/main/icons/ic_fingerprint_white.png"))
        self.actionSystem_Info.setText(main_window_text("System Info"))
        self.actionSystem_Info.setToolTip(
            main_window_text("Current System Information")
        )
        self.actionSystem_Info.setStatusTip(
            main_window_text("Display current computer system information.")
        )
        self.actionLicense_Registration = QAction(window)
        self.actionLicense_Registration.setObjectName("actionLicense_Registration")
        self.actionLicense_Registration.setIcon(QIcon(Icon.IC_CHROME_READER_MODE_WHITE))
        self.actionLicense_Registration.setText(
            main_window_text("License Registration...")
        )
        self.actionLicense_Registration.setStatusTip(
            main_window_text("Register your iHDA license.")
        )
        self.actionDonate = QAction(window)
        self.actionDonate.setObjectName("actionDonate")
        self.actionDonate.setIcon(
            QIcon(":/main/icons/ic_sentiment_satisfied_white.png")
        )
        self.actionDonate.setText(main_window_text("Donate"))
        self.actionDonate.setStatusTip(
            main_window_text("Donate. I need your help to make a better program.")
        )

    def _build_shell(self, window: QMainWindow) -> None:
        self.centralwidget = QWidget(window)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout__main = QVBoxLayout(self.centralwidget)
        self.verticalLayout__main.setSpacing(1)
        self.verticalLayout__main.setObjectName("verticalLayout__main")
        self.verticalLayout__main.setContentsMargins(1, 1, 1, 1)
        self.splitter__whole_vertical = QSplitter(self.centralwidget)
        self.splitter__whole_vertical.setObjectName("splitter__whole_vertical")
        self.splitter__whole_vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__whole_vertical.setHandleWidth(3)
        self.stackedWidget__whole = QStackedWidget(self.splitter__whole_vertical)
        self.stackedWidget__whole.setObjectName("stackedWidget__whole")
        self.page__ihda = QWidget()
        self.page__ihda.setObjectName("page__ihda")
        self.verticalLayout__library_page = QVBoxLayout(self.page__ihda)
        self.verticalLayout__library_page.setSpacing(1)
        self.verticalLayout__library_page.setObjectName("verticalLayout__library_page")
        self.verticalLayout__library_page.setContentsMargins(1, 1, 1, 1)
        self.splitter__whole_horizontal = QSplitter(self.page__ihda)
        self.splitter__whole_horizontal.setObjectName("splitter__whole_horizontal")
        self.splitter__whole_horizontal.setOrientation(Qt.Orientation.Horizontal)
        self.splitter__whole_horizontal.setHandleWidth(3)

    def _build_browser_host(self, window: QMainWindow) -> None:
        self.widget__asset_panel = QWidget(self.splitter__whole_horizontal)
        self.widget__asset_panel.setObjectName("widget__asset_panel")
        self.verticalLayout__asset_panel = QVBoxLayout(self.widget__asset_panel)
        self.verticalLayout__asset_panel.setSpacing(1)
        self.verticalLayout__asset_panel.setObjectName("verticalLayout__asset_panel")
        self.verticalLayout__asset_panel.setContentsMargins(0, 0, 0, 0)
        self.widget__asset_browser_host = QWidget(self.widget__asset_panel)
        self.widget__asset_browser_host.setObjectName("widget__asset_browser_host")
        self.verticalLayout__asset_panel.addWidget(self.widget__asset_browser_host)
        self.horizontalLayout__asset_footer = QHBoxLayout()
        self.horizontalLayout__asset_footer.setSpacing(1)
        self.horizontalLayout__asset_footer.setObjectName(
            "horizontalLayout__asset_footer"
        )
        self.horizontalLayout__asset_footer.setContentsMargins(3, -1, 3, -1)
        self.horizontalLayout__asset_tags = QHBoxLayout()
        self.horizontalLayout__asset_tags.setSpacing(8)
        self.horizontalLayout__asset_tags.setObjectName("horizontalLayout__asset_tags")
        self.label__tag_pixmap = QLabel(self.widget__asset_panel)
        self.label__tag_pixmap.setObjectName("label__tag_pixmap")
        self.label__tag_pixmap.setSizePolicy(
            size_policy(
                self.label__tag_pixmap,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__tag_pixmap.setMaximumSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.label__tag_pixmap.setPixmap(QPixmap(Icon.IC_BOOKMARK_WHITE))
        self.label__tag_pixmap.setScaledContents(True)
        self.label__tag_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__tag_pixmap.setText("")
        self.horizontalLayout__asset_tags.addWidget(self.label__tag_pixmap)
        self.label__tags = QLabel(self.widget__asset_panel)
        self.label__tags.setObjectName("label__tags")
        self.label__tags.setStyleSheet("color: palette(link);")
        self.label__tags.setText("")
        self.horizontalLayout__asset_tags.addWidget(self.label__tags)
        self.horizontalLayout__asset_footer.addLayout(self.horizontalLayout__asset_tags)
        self.spacer__asset_footer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__asset_footer.addItem(self.spacer__asset_footer)
        self.label__logged_id_pixmap = QLabel(self.widget__asset_panel)
        self.label__logged_id_pixmap.setObjectName("label__logged_id_pixmap")
        self.label__logged_id_pixmap.setSizePolicy(
            size_policy(
                self.label__logged_id_pixmap,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__logged_id_pixmap.setMaximumSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.label__logged_id_pixmap.setPixmap(
            QPixmap(":/main/icons/ic_account_box_white.png")
        )
        self.label__logged_id_pixmap.setScaledContents(True)
        self.label__logged_id_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__logged_id_pixmap.setText("")
        self.horizontalLayout__asset_footer.addWidget(self.label__logged_id_pixmap)
        self.label__logged_id = QLabel(self.widget__asset_panel)
        self.label__logged_id.setObjectName("label__logged_id")
        self.label__logged_id.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__logged_id.setToolTip(main_window_text("Logged ID"))
        self.label__logged_id.setStatusTip(
            main_window_text("Displays the logged-in ID")
        )
        self.label__logged_id.setText("")
        self.horizontalLayout__asset_footer.addWidget(self.label__logged_id)
        self.spacer__asset_footer_end = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__asset_footer.addItem(self.spacer__asset_footer_end)
        self.horizontalLayout__asset_count = QHBoxLayout()
        self.horizontalLayout__asset_count.setSpacing(3)
        self.horizontalLayout__asset_count.setObjectName(
            "horizontalLayout__asset_count"
        )
        self.widget__asset_count_host = QWidget(self.widget__asset_panel)
        self.widget__asset_count_host.setObjectName("widget__asset_count_host")
        self.horizontalLayout__asset_count.addWidget(self.widget__asset_count_host)
        self.label__hda_count_suffix = QLabel(self.widget__asset_panel)
        self.label__hda_count_suffix.setObjectName("label__hda_count_suffix")
        self.label__hda_count_suffix.setText(main_window_text("iHDA(s)"))
        self.horizontalLayout__asset_count.addWidget(self.label__hda_count_suffix)
        self.horizontalLayout__asset_footer.addLayout(
            self.horizontalLayout__asset_count
        )
        self.verticalLayout__asset_panel.addLayout(self.horizontalLayout__asset_footer)
        self.splitter__whole_horizontal.addWidget(self.widget__asset_panel)

    def _build_details_toolbar(self, window: QMainWindow) -> None:
        self.splitter__hda_info_whole_vertical = QSplitter(
            self.splitter__whole_horizontal
        )
        self.splitter__hda_info_whole_vertical.setObjectName(
            "splitter__hda_info_whole_vertical"
        )
        self.splitter__hda_info_whole_vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__hda_info_whole_vertical.setHandleWidth(3)
        self.frame__hda_info = QFrame(self.splitter__hda_info_whole_vertical)
        self.frame__hda_info.setObjectName("frame__hda_info")
        self.frame__hda_info.setFrameShape(QFrame.Shape.NoFrame)
        self.frame__hda_info.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout__detail_navigation = QHBoxLayout(self.frame__hda_info)
        self.horizontalLayout__detail_navigation.setSpacing(3)
        self.horizontalLayout__detail_navigation.setObjectName(
            "horizontalLayout__detail_navigation"
        )
        self.horizontalLayout__detail_navigation.setContentsMargins(3, 1, 3, 1)
        self.pushButton__hda_info = QPushButton(self.frame__hda_info)
        self.pushButton__hda_info.setObjectName("pushButton__hda_info")
        self.pushButton__hda_info.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__hda_info.setIcon(QIcon(Icon.IC_BORDER_COLOR_WHITE))
        self.pushButton__hda_info.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__hda_info.setCheckable(True)
        self.pushButton__hda_info.setChecked(True)
        self.pushButton__hda_info.setAutoExclusive(True)
        self.pushButton__hda_info.setFlat(True)
        self.pushButton__hda_info.setToolTip(main_window_text("iHDA Info View"))
        self.pushButton__hda_info.setStatusTip(
            main_window_text("iHDA notes and tag information.")
        )
        self.pushButton__hda_info.setText("")
        self.horizontalLayout__detail_navigation.addWidget(self.pushButton__hda_info)
        self.pushButton__hda_loc_record = QPushButton(self.frame__hda_info)
        self.pushButton__hda_loc_record.setObjectName("pushButton__hda_loc_record")
        self.pushButton__hda_loc_record.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__hda_loc_record.setIcon(
            QIcon(":/main/icons/ic_place_white.png")
        )
        self.pushButton__hda_loc_record.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__hda_loc_record.setCheckable(True)
        self.pushButton__hda_loc_record.setAutoExclusive(True)
        self.pushButton__hda_loc_record.setFlat(True)
        self.pushButton__hda_loc_record.setToolTip(
            main_window_text("iHDA Location Record View")
        )
        self.pushButton__hda_loc_record.setStatusTip(
            main_window_text("Record iHDA location of current HIP file.")
        )
        self.pushButton__hda_loc_record.setText("")
        self.horizontalLayout__detail_navigation.addWidget(
            self.pushButton__hda_loc_record
        )
        self.pushButton__hda_inside_node_view = QPushButton(self.frame__hda_info)
        self.pushButton__hda_inside_node_view.setObjectName(
            "pushButton__hda_inside_node_view"
        )
        self.pushButton__hda_inside_node_view.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__hda_inside_node_view.setIcon(QIcon(Icon.IC_FIND_IN_PAGE_WHITE))
        self.pushButton__hda_inside_node_view.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__hda_inside_node_view.setCheckable(True)
        self.pushButton__hda_inside_node_view.setAutoExclusive(True)
        self.pushButton__hda_inside_node_view.setFlat(True)
        self.pushButton__hda_inside_node_view.setToolTip(
            main_window_text("iHDA Inside Node View")
        )
        self.pushButton__hda_inside_node_view.setStatusTip(
            main_window_text("Find the iHDA node in the current HIP file.")
        )
        self.pushButton__hda_inside_node_view.setText("")
        self.horizontalLayout__detail_navigation.addWidget(
            self.pushButton__hda_inside_node_view
        )
        self.spacer__detail_navigation = QSpacerItem(
            133, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__detail_navigation.addItem(self.spacer__detail_navigation)
        self.pushButton__donate = QPushButton(self.frame__hda_info)
        self.pushButton__donate.setObjectName("pushButton__donate")
        self.pushButton__donate.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__donate.setIcon(
            QIcon(":/main/icons/ic_sentiment_satisfied_white.png")
        )
        self.pushButton__donate.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.pushButton__donate.setFlat(True)
        self.pushButton__donate.setToolTip(main_window_text("Donate..."))
        self.pushButton__donate.setStatusTip(
            main_window_text("Donate. I need your help to make a better program.")
        )
        self.pushButton__donate.setText("")
        self.horizontalLayout__detail_navigation.addWidget(self.pushButton__donate)
        self.splitter__hda_info_whole_vertical.addWidget(self.frame__hda_info)
        self.stackedWidget__hda_infos = QStackedWidget(
            self.splitter__hda_info_whole_vertical
        )
        self.stackedWidget__hda_infos.setObjectName("stackedWidget__hda_infos")

    def _build_note_and_tags(self, window: QMainWindow) -> None:
        self.page__hda_info = QWidget()
        self.page__hda_info.setObjectName("page__hda_info")
        self.verticalLayout__detail_page = QVBoxLayout(self.page__hda_info)
        self.verticalLayout__detail_page.setSpacing(1)
        self.verticalLayout__detail_page.setObjectName("verticalLayout__detail_page")
        self.verticalLayout__detail_page.setContentsMargins(1, 1, 1, 1)
        self.splitter__hda_info_vertical = QSplitter(self.page__hda_info)
        self.splitter__hda_info_vertical.setObjectName("splitter__hda_info_vertical")
        self.splitter__hda_info_vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__hda_info_vertical.setHandleWidth(3)
        self.widget__note_editor = QWidget(self.splitter__hda_info_vertical)
        self.widget__note_editor.setObjectName("widget__note_editor")
        self.verticalLayout__note_editor = QVBoxLayout(self.widget__note_editor)
        self.verticalLayout__note_editor.setSpacing(1)
        self.verticalLayout__note_editor.setObjectName("verticalLayout__note_editor")
        self.verticalLayout__note_editor.setContentsMargins(1, 1, 1, 1)
        self.textEdit__note = QTextEdit(self.widget__note_editor)
        self.textEdit__note.setObjectName("textEdit__note")
        self.textEdit__note.setFrameShape(QFrame.Shape.NoFrame)
        self.textEdit__note.setTabStopDistance(40.0)
        self.textEdit__note.setStatusTip(
            main_window_text("Please enter a note for that HDA")
        )
        self.textEdit__note.setPlaceholderText(
            main_window_text("This is a note to write the selected iHDA.")
        )
        self.verticalLayout__note_editor.addWidget(self.textEdit__note)
        # Read-only Markdown rendering of the note; swapped in by the toggle below.
        self.textBrowser__note_preview = QTextBrowser(self.widget__note_editor)
        self.textBrowser__note_preview.setObjectName("textBrowser__note_preview")
        self.textBrowser__note_preview.setFrameShape(QFrame.Shape.NoFrame)
        self.textBrowser__note_preview.setOpenExternalLinks(True)
        self.textBrowser__note_preview.setVisible(False)
        self.verticalLayout__note_editor.addWidget(self.textBrowser__note_preview)
        self.label__metadata_status = QLabel(self.widget__note_editor)
        self.label__metadata_status.setObjectName("label__metadata_status")
        self.verticalLayout__note_editor.addWidget(self.label__metadata_status)
        self.horizontalLayout__note_actions = QHBoxLayout()
        self.horizontalLayout__note_actions.setSpacing(3)
        self.horizontalLayout__note_actions.setObjectName(
            "horizontalLayout__note_actions"
        )
        self.horizontalLayout__note_actions.setContentsMargins(3, -1, 3, -1)
        self.toolButton__note_preview = QToolButton(self.widget__note_editor)
        self.toolButton__note_preview.setObjectName("toolButton__note_preview")
        self.toolButton__note_preview.setCheckable(True)
        self.toolButton__note_preview.setAutoRaise(True)
        self.toolButton__note_preview.setIcon(QIcon(Icon.IC_CHROME_READER_MODE_WHITE))
        self.toolButton__note_preview.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.toolButton__note_preview.setToolTip(
            main_window_text("Preview the note as Markdown")
        )
        self.toolButton__note_preview.setStatusTip(
            main_window_text("Toggle between editing and a rendered Markdown view")
        )
        self.horizontalLayout__note_actions.addWidget(self.toolButton__note_preview)
        self.spacer__note_actions = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__note_actions.addItem(self.spacer__note_actions)
        self.pushButton__metadata_save = QPushButton(self.widget__note_editor)
        self.pushButton__metadata_save.setObjectName("pushButton__metadata_save")
        self.pushButton__metadata_save.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__metadata_save.setIcon(QIcon(Icon.IC_SAVE_WHITE))
        self.pushButton__metadata_save.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__metadata_save.setFlat(True)
        self.pushButton__metadata_save.setToolTip(
            main_window_text("Save note and tags (Ctrl+S)")
        )
        self.pushButton__metadata_save.setStatusTip(
            main_window_text("Save the note and tags of the selected iHDA node")
        )
        self.pushButton__metadata_save.setText("")
        self.horizontalLayout__note_actions.addWidget(self.pushButton__metadata_save)
        self.verticalLayout__note_editor.addLayout(self.horizontalLayout__note_actions)
        self.splitter__hda_info_vertical.addWidget(self.widget__note_editor)
        self._build_tag_editor(window)

    def _build_tag_editor(self, window: QMainWindow) -> None:
        self.widget__tag_editor = QWidget(self.splitter__hda_info_vertical)
        self.widget__tag_editor.setObjectName("widget__tag_editor")
        self.verticalLayout__tag_editor = QVBoxLayout(self.widget__tag_editor)
        self.verticalLayout__tag_editor.setSpacing(1)
        self.verticalLayout__tag_editor.setObjectName("verticalLayout__tag_editor")
        self.verticalLayout__tag_editor.setContentsMargins(1, 1, 1, 1)
        self.textEdit__tag = TagEditor(self.widget__tag_editor)
        self.textEdit__tag.setObjectName("textEdit__tag")
        self.textEdit__tag.setStatusTip(
            main_window_text("Please enter a tag for that HDA")
        )
        self.textEdit__tag.setPlaceholderText(
            main_window_text("Add a tag and press Enter")
        )
        self.verticalLayout__tag_editor.addWidget(self.textEdit__tag)
        self.label__tag_status = QLabel(self.widget__tag_editor)
        self.label__tag_status.setObjectName("label__tag_status")
        self.verticalLayout__tag_editor.addWidget(self.label__tag_status)
        self.horizontalLayout__tag_actions = QHBoxLayout()
        self.horizontalLayout__tag_actions.setSpacing(3)
        self.horizontalLayout__tag_actions.setObjectName(
            "horizontalLayout__tag_actions"
        )
        self.horizontalLayout__tag_actions.setContentsMargins(3, -1, 3, -1)
        self.spacer__tag_actions = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__tag_actions.addItem(self.spacer__tag_actions)
        self.verticalLayout__tag_editor.addLayout(self.horizontalLayout__tag_actions)
        self.splitter__hda_info_vertical.addWidget(self.widget__tag_editor)
        self.verticalLayout__detail_page.addWidget(self.splitter__hda_info_vertical)
        self.stackedWidget__hda_infos.addWidget(self.page__hda_info)

    def _build_media_hosts(self, window: QMainWindow) -> None:
        self.page__video_player = QWidget()
        self.page__video_player.setObjectName("page__video_player")
        self.verticalLayout__video_page = QVBoxLayout(self.page__video_player)
        self.verticalLayout__video_page.setSpacing(1)
        self.verticalLayout__video_page.setObjectName("verticalLayout__video_page")
        self.verticalLayout__video_page.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout__video_player = QVBoxLayout()
        self.verticalLayout__video_player.setSpacing(1)
        self.verticalLayout__video_player.setObjectName("verticalLayout__video_player")
        self.verticalLayout__video_page.addLayout(self.verticalLayout__video_player)
        self.stackedWidget__whole.addWidget(self.page__video_player)
        self.page__web_view = QWidget()
        self.page__web_view.setObjectName("page__web_view")
        self.verticalLayout__web_page = QVBoxLayout(self.page__web_view)
        self.verticalLayout__web_page.setSpacing(1)
        self.verticalLayout__web_page.setObjectName("verticalLayout__web_page")
        self.verticalLayout__web_page.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout__web_view = QVBoxLayout()
        self.verticalLayout__web_view.setSpacing(1)
        self.verticalLayout__web_view.setObjectName("verticalLayout__web_view")
        self.verticalLayout__web_page.addLayout(self.verticalLayout__web_view)
        self.stackedWidget__whole.addWidget(self.page__web_view)

    def _build_debug_console(self, window: QMainWindow) -> None:
        self.widget__debug_console = QWidget(self.splitter__whole_vertical)
        self.widget__debug_console.setObjectName("widget__debug_console")
        self.verticalLayout__debug_console = QVBoxLayout(self.widget__debug_console)
        self.verticalLayout__debug_console.setSpacing(1)
        self.verticalLayout__debug_console.setObjectName(
            "verticalLayout__debug_console"
        )
        self.verticalLayout__debug_console.setContentsMargins(0, 0, 0, 0)
        self.textBrowser__debug = QTextBrowser(self.widget__debug_console)
        self.textBrowser__debug.setObjectName("textBrowser__debug")
        self.textBrowser__debug.setFrameShape(QFrame.Shape.NoFrame)
        self.textBrowser__debug.setTabStopDistance(40.0)
        self.textBrowser__debug.setOpenExternalLinks(True)
        self.textBrowser__debug.setStatusTip(
            main_window_text("Show debug of application")
        )
        self.verticalLayout__debug_console.addWidget(self.textBrowser__debug)
        self.splitter__whole_vertical.addWidget(self.widget__debug_console)
        self.verticalLayout__main.addWidget(self.splitter__whole_vertical)
        window.setCentralWidget(self.centralwidget)

    def _build_menus_and_toolbar(self, window: QMainWindow) -> None:
        self.menubar = QMenuBar(window)
        self.menubar.setObjectName("menubar")
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuFile.setTitle(main_window_text("File"))
        self.menuDatabase = QMenu(self.menuFile)
        self.menuDatabase.setObjectName("menuDatabase")
        self.menuDatabase.setIcon(QIcon(":/main/icons/database.png"))
        self.menuDatabase.setTitle(main_window_text("Database"))
        self.menuTools = QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menuTools.setTitle(main_window_text("Tools"))
        self.menuConfig = QMenu(self.menuTools)
        self.menuConfig.setObjectName("menuConfig")
        self.menuConfig.setIcon(
            QIcon(":/main/icons/ic_settings_applications_white.png")
        )
        self.menuConfig.setTitle(main_window_text("Config"))
        self.menuDownload = QMenu(self.menuTools)
        self.menuDownload.setObjectName("menuDownload")
        self.menuDownload.setIcon(QIcon(":/main/icons/ic_language_white.png"))
        self.menuDownload.setTitle(main_window_text("Download"))
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.setTitle(main_window_text("Help"))
        self.menuData = QMenu(self.menubar)
        self.menuData.setObjectName("menuData")
        self.menuData.setTitle(main_window_text("Data"))
        self.menuHistory = QMenu(self.menuData)
        self.menuHistory.setObjectName("menuHistory")
        self.menuHistory.setIcon(QIcon(Icon.IC_QUERY_BUILDER_WHITE))
        self.menuHistory.setTitle(main_window_text("History"))
        window.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(window)
        self.statusbar.setObjectName("statusbar")
        window.setStatusBar(self.statusbar)
        self._populate_navigation(window)

    def _populate_navigation(self, window: QMainWindow) -> None:
        self.toolBar = QToolBar(window)
        self.toolBar.setObjectName("toolBar")
        self.toolBar.setIconSize(QSize(18, 18))
        window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolBar)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuData.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menuFile.addAction(self.actionCreate_Account)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionLogin)
        self.menuFile.addAction(self.actionLogout)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menuDatabase.menuAction())
        self.menuFile.addSeparator()
        self.menuDatabase.addAction(self.actionCleanup)
        self.menuTools.addAction(self.menuConfig.menuAction())
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionPreference)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.menuDownload.menuAction())
        self.menuConfig.addSeparator()
        self.menuConfig.addAction(self.actionReset)
        self.menuDownload.addAction(self.actionFFmpeg)
        self.menuDownload.addAction(self.actionCodec)
        self.menuHelp.addAction(self.actionHelp)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionSubmit_a_Bug_Report)
        self.menuHelp.addAction(self.actionSubmit_Feedback)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionUpdate)
        self.menuHelp.addAction(self.actionAbout)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionDonate)
        self.menuData.addAction(self.actionImport_Data)
        self.menuData.addAction(self.actionExport_Data)
        self.menuData.addSeparator()
        self.menuData.addAction(self.menuHistory.menuAction())
        self.menuHistory.addAction(self.actionDelete_All)
        self.toolBar.addAction(self.actionOpen_the_hda_directory)
        self.toolBar.addAction(self.actionReload)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actioniHDA)
        self.toolBar.addAction(self.actionHistory)
        self.toolBar.addAction(self.actionVideo_Player)
        self.toolBar.addAction(self.actionWeb)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionCategory_Synchronization)
        self.toolBar.addAction(self.actionNode_Synchronization)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionUnpack_Subnet)
        self.toolBar.addAction(self.actionSticky_Note)
        self.toolBar.addAction(self.actionComment)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionNull)
        self.toolBar.addAction(self.actionInput)
        self.toolBar.addAction(self.actionOuput)
        self.toolBar.addAction(self.actionBoth)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionAutomatic_Name_Change)
        self.toolBar.setWindowTitle(main_window_text("toolBar"))
        self.stackedWidget__whole.setCurrentWidget(self.page__ihda)
        self.stackedWidget__category.setCurrentWidget(self.page__category)
        self.stackedWidget__hda_infos.setCurrentWidget(self.page__hda_info)
