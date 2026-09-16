"""Code-built MainWindow layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QRect,
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
    QVBoxLayout,
    QWidget,
)

import icons_rc  # noqa: F401 (register bundled icons)
from widgets.layout_helpers import make_font, size_policy
from widgets.ui_tokens import TOOLBAR_ICON_SIZE


def _translate(text: str) -> str:
    return QCoreApplication.translate("MainWindow__individualHDA", text)


class MainWindowLayout:
    def build_ui(self, window: QMainWindow) -> None:
        self._configure_window(window)
        self._build_application_actions(window)
        self._build_workspace_actions(window)
        self._build_houdini_actions(window)
        self._build_support_actions(window)
        self._build_shell(window)
        self._build_category_panel(window)
        self._build_browser_host(window)
        self._build_details_toolbar(window)
        self._build_note_and_tags(window)
        self._build_scene_records(window)
        self._build_inside_nodes(window)
        self._build_media_hosts(window)
        self._build_history_page(window)
        self._build_debug_console(window)
        self._build_menus_and_toolbar(window)

    def _configure_window(self, window: QMainWindow) -> None:
        if not window.objectName():
            window.setObjectName("MainWindow__individualHDA")
        window.resize(1472, 863)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/main/icons/viewport_logo_trans.png"))
        window.setWindowTitle(_translate("Individual HDA"))

    def _build_application_actions(self, window: QMainWindow) -> None:
        self.actionQuit = QAction(window)
        self.actionQuit.setObjectName("actionQuit")
        self.actionQuit.setIcon(QIcon(":/main/icons/ic_not_interested_white_48dp.png"))
        self.actionQuit.setText(_translate("Quit"))
        self.actionReload = QAction(window)
        self.actionReload.setObjectName("actionReload")
        self.actionReload.setIcon(QIcon(":/main/icons/ic_refresh_white.png"))
        self.actionReload.setText(_translate("Reload"))
        self.actionReload.setToolTip(_translate("Reload the library from storage"))
        self.actionHelp = QAction(window)
        self.actionHelp.setObjectName("actionHelp")
        self.actionHelp.setIcon(QIcon(":/main/icons/ic_help_white.png"))
        self.actionHelp.setText(_translate("Help"))
        self.actionAbout = QAction(window)
        self.actionAbout.setObjectName("actionAbout")
        self.actionAbout.setIcon(QIcon(":/main/icons/ic_info_outline_white.png"))
        self.actionAbout.setText(_translate("About"))
        self.actionReset = QAction(window)
        self.actionReset.setObjectName("actionReset")
        self.actionReset.setIcon(QIcon(":/main/icons/ic_restore_page_white.png"))
        self.actionReset.setText(_translate("Reset"))
        self.actionReset.setStatusTip(_translate("Initialize the property"))
        self.actionDefault = QAction(window)
        self.actionDefault.setObjectName("actionDefault")
        self.actionDefault.setCheckable(True)
        self.actionDefault.setChecked(True)
        self.actionDefault.setText(_translate("Default"))
        self.actionDefault.setStatusTip(_translate("Change to the default theme"))
        self.actionDark_blue = QAction(window)
        self.actionDark_blue.setObjectName("actionDark_blue")
        self.actionDark_blue.setCheckable(True)
        self.actionDark_blue.setText(_translate("Dark blue"))
        self.actionDark_blue.setStatusTip(_translate("Change to the dark blue"))
        self.actionOpen_the_hda_directory = QAction(window)
        self.actionOpen_the_hda_directory.setObjectName("actionOpen_the_hda_directory")
        self.actionOpen_the_hda_directory.setIcon(
            QIcon(":/main/icons/ic_folder_white.png")
        )
        self.actionOpen_the_hda_directory.setText(
            _translate("Open the HDA directory...")
        )
        self.actionOpen_the_hda_directory.setStatusTip(
            _translate("Open the HDA directory path.")
        )
        self.actionLogin = QAction(window)
        self.actionLogin.setObjectName("actionLogin")
        self.actionLogin.setIcon(QIcon(":/main/icons/ic_account_box_white.png"))
        self.actionLogin.setText(_translate("Login"))
        self.actionLogout = QAction(window)
        self.actionLogout.setObjectName("actionLogout")
        self.actionLogout.setIcon(QIcon(":/main/icons/ic_account_box_white.png"))
        self.actionLogout.setText(_translate("Logout"))
        self.actionSubmit_a_Bug_Report = QAction(window)
        self.actionSubmit_a_Bug_Report.setObjectName("actionSubmit_a_Bug_Report")
        self.actionSubmit_a_Bug_Report.setIcon(QIcon(":/main/icons/ic_email_white.png"))
        self.actionSubmit_a_Bug_Report.setText(_translate("Submit a Bug Report"))
        self.actionSubmit_Feedback = QAction(window)
        self.actionSubmit_Feedback.setObjectName("actionSubmit_Feedback")
        self.actionSubmit_Feedback.setIcon(QIcon(":/main/icons/ic_send_white.png"))
        self.actionSubmit_Feedback.setText(_translate("Submit Feedback"))

    def _build_workspace_actions(self, window: QMainWindow) -> None:
        self.actioniHDA = QAction(window)
        self.actioniHDA.setObjectName("actioniHDA")
        self.actioniHDA.setCheckable(True)
        self.actioniHDA.setChecked(True)
        self.actioniHDA.setIcon(QIcon(":/main/icons/houdini_logo_white.png"))
        self.actioniHDA.setText(_translate("iHDA"))
        self.actioniHDA.setStatusTip(_translate("Show iHDA window."))
        self.actionVideo_Player = QAction(window)
        self.actionVideo_Player.setObjectName("actionVideo_Player")
        self.actionVideo_Player.setCheckable(True)
        self.actionVideo_Player.setIcon(QIcon(":/main/icons/ic_movie_white.png"))
        self.actionVideo_Player.setText(_translate("Video Player"))
        self.actionVideo_Player.setStatusTip(_translate("Show video player window."))
        self.actionWeb = QAction(window)
        self.actionWeb.setObjectName("actionWeb")
        self.actionWeb.setCheckable(True)
        self.actionWeb.setIcon(QIcon(":/main/icons/ic_language_white.png"))
        self.actionWeb.setText(_translate("Web"))
        self.actionWeb.setStatusTip(_translate("Show web window."))
        self.actionCreate_Account = QAction(window)
        self.actionCreate_Account.setObjectName("actionCreate_Account")
        self.actionCreate_Account.setIcon(QIcon(":/main/icons/ic_group_white.png"))
        self.actionCreate_Account.setText(_translate("Create Account"))
        self.actionPreference = QAction(window)
        self.actionPreference.setObjectName("actionPreference")
        self.actionPreference.setIcon(QIcon(":/main/icons/ic_build_white.png"))
        self.actionPreference.setText(_translate("Preference"))
        self.actionPreference.setStatusTip(_translate("Setting iHDA preference."))
        self.actionImport_Data = QAction(window)
        self.actionImport_Data.setObjectName("actionImport_Data")
        self.actionImport_Data.setIcon(QIcon(":/main/icons/ic_unarchive_white.png"))
        self.actionImport_Data.setText(_translate("Import Data"))
        self.actionImport_Data.setStatusTip(_translate("Import iHDA data."))
        self.actionExport_Data = QAction(window)
        self.actionExport_Data.setObjectName("actionExport_Data")
        self.actionExport_Data.setIcon(QIcon(":/main/icons/ic_archive_white.png"))
        self.actionExport_Data.setText(_translate("Export Data"))
        self.actionExport_Data.setStatusTip(_translate("Export iHDA data."))
        self.actionDownload_FFmpeg = QAction(window)
        self.actionDownload_FFmpeg.setObjectName("actionDownload_FFmpeg")
        self.actionDownload_FFmpeg.setIcon(
            QIcon(":/main/icons/ic_language_white_48dp.png")
        )
        self.actionDownload_FFmpeg.setText(_translate("Download FFmpeg"))
        self.actionDownload_FFmpeg.setStatusTip(
            _translate("Go to the ffmpeg download site.")
        )
        self.actionHistory = QAction(window)
        self.actionHistory.setObjectName("actionHistory")
        self.actionHistory.setCheckable(True)
        self.actionHistory.setIcon(QIcon(":/main/icons/ic_query_builder_white.png"))
        self.actionHistory.setText(_translate("History"))
        self.actionHistory.setStatusTip(_translate("Show iHDA history"))
        self.actionUpdate = QAction(window)
        self.actionUpdate.setObjectName("actionUpdate")
        self.actionUpdate.setIcon(QIcon(":/main/icons/ic_new_releases_white.png"))
        self.actionUpdate.setText(_translate("Update..."))
        self.actionFFmpeg = QAction(window)
        self.actionFFmpeg.setObjectName("actionFFmpeg")
        self.actionFFmpeg.setText(_translate("FFmpeg"))
        self.actionFFmpeg.setToolTip(_translate("Download FFmpeg"))
        self.actionCodec = QAction(window)
        self.actionCodec.setObjectName("actionCodec")
        self.actionCodec.setText(_translate("Codec"))
        self.actionCodec.setToolTip(_translate("Download Codec"))
        self.actionDelete_All = QAction(window)
        self.actionDelete_All.setObjectName("actionDelete_All")
        self.actionDelete_All.setIcon(QIcon(":/main/icons/ic_delete_forever_white.png"))
        self.actionDelete_All.setText(_translate("Delete All"))
        self.actionDelete_All.setStatusTip(_translate("Delete all iHDA history."))

    def _build_houdini_actions(self, window: QMainWindow) -> None:
        self.actionUnpack_Subnet = QAction(window)
        self.actionUnpack_Subnet.setObjectName("actionUnpack_Subnet")
        self.actionUnpack_Subnet.setCheckable(True)
        self.actionUnpack_Subnet.setIcon(QIcon(":/main/icons/unpack_subnet.png"))
        self.actionUnpack_Subnet.setText(_translate("Unpack Subnet"))
        self.actionUnpack_Subnet.setStatusTip(
            _translate("When you import a node, you unpack it and import it")
        )
        self.actionSticky_Note = QAction(window)
        self.actionSticky_Note.setObjectName("actionSticky_Note")
        self.actionSticky_Note.setCheckable(True)
        self.actionSticky_Note.setIcon(QIcon(":/main/icons/network_sticky.png"))
        self.actionSticky_Note.setText(_translate("Sticky Note"))
        self.actionSticky_Note.setToolTip(_translate("Note to Sticky Note"))
        self.actionSticky_Note.setStatusTip(
            _translate("Apply iHDA note contents to houdini sticky note")
        )
        self.actionComment = QAction(window)
        self.actionComment.setObjectName("actionComment")
        self.actionComment.setCheckable(True)
        self.actionComment.setIcon(QIcon(":/main/icons/ic_comment_white.png"))
        self.actionComment.setText(_translate("Comment"))
        self.actionComment.setToolTip(_translate("Houdini Node Comment"))
        self.actionComment.setStatusTip(
            _translate(
                "If true, simple iHDA information is entered as Houdini node description."
            )
        )
        self.actionNode_Synchronization = QAction(window)
        self.actionNode_Synchronization.setObjectName("actionNode_Synchronization")
        self.actionNode_Synchronization.setCheckable(True)
        self.actionNode_Synchronization.setIcon(
            QIcon(":/main/icons/ic_swap_vert_white.png")
        )
        self.actionNode_Synchronization.setText(_translate("Node Synchronization"))
        self.actionNode_Synchronization.setStatusTip(
            _translate(
                "When activated, the Houdini node and iHDA app are synchronized."
            )
        )
        self.actionNull = QAction(window)
        self.actionNull.setObjectName("actionNull")
        self.actionNull.setCheckable(True)
        self.actionNull.setChecked(True)
        self.actionNull.setIcon(QIcon(":/main/icons/ic_clear_white.png"))
        self.actionNull.setText(_translate("Null"))
        self.actionNull.setToolTip(_translate("Do not connect"))
        self.actionNull.setStatusTip(
            _translate(
                "It does not connect the node even if there is node connection information."
            )
        )
        self.actionInput = QAction(window)
        self.actionInput.setObjectName("actionInput")
        self.actionInput.setCheckable(True)
        self.actionInput.setIcon(
            QIcon(":/main/icons/ic_vertical_align_bottom_white.png")
        )
        self.actionInput.setText(_translate("Input"))
        self.actionInput.setToolTip(_translate("Input connection"))
        self.actionInput.setStatusTip(_translate("Connect only inputs from nodes"))
        self.actionOuput = QAction(window)
        self.actionOuput.setObjectName("actionOuput")
        self.actionOuput.setCheckable(True)
        self.actionOuput.setIcon(QIcon(":/main/icons/ic_vertical_align_top_white.png"))
        self.actionOuput.setText(_translate("Ouput"))
        self.actionOuput.setToolTip(_translate("Ouput connection"))
        self.actionOuput.setStatusTip(
            _translate("Connect only the output of the nodes.")
        )
        self.actionBoth = QAction(window)
        self.actionBoth.setObjectName("actionBoth")
        self.actionBoth.setCheckable(True)
        self.actionBoth.setIcon(
            QIcon(":/main/icons/ic_vertical_align_center_white.png")
        )
        self.actionBoth.setText(_translate("Both"))
        self.actionBoth.setToolTip(_translate("Both connections"))
        self.actionBoth.setStatusTip(
            _translate("Connect both input and output of nodes.")
        )
        self.actionCategory_Synchronization = QAction(window)
        self.actionCategory_Synchronization.setObjectName(
            "actionCategory_Synchronization"
        )
        self.actionCategory_Synchronization.setCheckable(True)
        self.actionCategory_Synchronization.setIcon(
            QIcon(":/main/icons/ic_swap_horiz_white.png")
        )
        self.actionCategory_Synchronization.setText(
            _translate("Category Synchronization")
        )
        self.actionCategory_Synchronization.setToolTip(
            _translate("Category Synchronization")
        )
        self.actionCategory_Synchronization.setStatusTip(
            _translate(
                "Synchronize houdini category with current HDA category in real time"
            )
        )
        self.actionCleanup = QAction(window)
        self.actionCleanup.setObjectName("actionCleanup")
        self.actionCleanup.setIcon(QIcon(":/main/icons/clear.png"))
        self.actionCleanup.setText(_translate("Clean up"))
        self.actionCleanup.setStatusTip(
            _translate("Clean up unnecessary data from the database.")
        )
        self.actionAutomatic_Name_Change = QAction(window)
        self.actionAutomatic_Name_Change.setObjectName("actionAutomatic_Name_Change")
        self.actionAutomatic_Name_Change.setCheckable(True)
        self.actionAutomatic_Name_Change.setChecked(True)
        self.actionAutomatic_Name_Change.setIcon(
            QIcon(":/main/icons/ic_text_format_white.png")
        )
        self.actionAutomatic_Name_Change.setText(_translate("Automatic Name Change"))
        self.actionAutomatic_Name_Change.setToolTip(
            _translate("Houdini node name is changed automatically")
        )
        self.actionAutomatic_Name_Change.setStatusTip(
            _translate(
                "When you select this option, the name that can cause errors when registering Houdini nodes to the iHDA app is automatically changed."
            )
        )

    def _build_support_actions(self, window: QMainWindow) -> None:
        self.actionSystem_Info = QAction(window)
        self.actionSystem_Info.setObjectName("actionSystem_Info")
        self.actionSystem_Info.setIcon(QIcon(":/main/icons/ic_fingerprint_white.png"))
        self.actionSystem_Info.setText(_translate("System Info"))
        self.actionSystem_Info.setToolTip(_translate("Current System Information"))
        self.actionSystem_Info.setStatusTip(
            _translate("Display current computer system information.")
        )
        self.actionLicense_Registration = QAction(window)
        self.actionLicense_Registration.setObjectName("actionLicense_Registration")
        self.actionLicense_Registration.setIcon(
            QIcon(":/main/icons/ic_chrome_reader_mode_white.png")
        )
        self.actionLicense_Registration.setText(_translate("License Registration..."))
        self.actionLicense_Registration.setStatusTip(
            _translate("Register your iHDA license.")
        )
        self.actionDonate = QAction(window)
        self.actionDonate.setObjectName("actionDonate")
        self.actionDonate.setIcon(
            QIcon(":/main/icons/ic_sentiment_satisfied_white.png")
        )
        self.actionDonate.setText(_translate("Donate"))
        self.actionDonate.setStatusTip(
            _translate("Donate. I need your help to make a better program.")
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

    def _build_category_panel(self, window: QMainWindow) -> None:
        self.widget__category_panel = QWidget(self.splitter__whole_horizontal)
        self.widget__category_panel.setObjectName("widget__category_panel")
        self.verticalLayout__category_panel = QVBoxLayout(self.widget__category_panel)
        self.verticalLayout__category_panel.setSpacing(1)
        self.verticalLayout__category_panel.setObjectName(
            "verticalLayout__category_panel"
        )
        self.verticalLayout__category_panel.setContentsMargins(0, 0, 0, 0)
        self.splitter__cate_whole_vertical = QSplitter(self.widget__category_panel)
        self.splitter__cate_whole_vertical.setObjectName(
            "splitter__cate_whole_vertical"
        )
        self.splitter__cate_whole_vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__cate_whole_vertical.setHandleWidth(3)
        self.widget__category_search = QWidget(self.splitter__cate_whole_vertical)
        self.widget__category_search.setObjectName("widget__category_search")
        self.horizontalLayout__category_search = QHBoxLayout(
            self.widget__category_search
        )
        self.horizontalLayout__category_search.setSpacing(5)
        self.horizontalLayout__category_search.setObjectName(
            "horizontalLayout__category_search"
        )
        self.horizontalLayout__category_search.setContentsMargins(3, 0, 3, 0)
        self.checkBox__casesensitive_cate = QCheckBox(self.widget__category_search)
        self.checkBox__casesensitive_cate.setObjectName("checkBox__casesensitive_cate")
        self.checkBox__casesensitive_cate.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__casesensitive_cate.setIcon(
            QIcon(":/main/icons/case_sensitive.png")
        )
        self.checkBox__casesensitive_cate.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.checkBox__casesensitive_cate.setToolTip(_translate("Word Case Sensitive"))
        self.checkBox__casesensitive_cate.setStatusTip(
            _translate("It is case sensitive")
        )
        self.checkBox__casesensitive_cate.setText("")
        self.horizontalLayout__category_search.addWidget(
            self.checkBox__casesensitive_cate
        )
        self.lineEdit__search_cate = QLineEdit(self.widget__category_search)
        self.lineEdit__search_cate.setObjectName("lineEdit__search_cate")
        self.lineEdit__search_cate.setFrame(False)
        self.lineEdit__search_cate.setClearButtonEnabled(True)
        self.lineEdit__search_cate.setStatusTip(
            _translate("Please enter your search term")
        )
        self.lineEdit__search_cate.setPlaceholderText(_translate("ex) sop"))
        self.horizontalLayout__category_search.addWidget(self.lineEdit__search_cate)
        self.splitter__cate_whole_vertical.addWidget(self.widget__category_search)
        self.stackedWidget__category = QStackedWidget(
            self.splitter__cate_whole_vertical
        )
        self.stackedWidget__category.setObjectName("stackedWidget__category")
        self.stackedWidget__category.setStatusTip(
            _translate("Show the category of the iHDA")
        )
        self.page__category = QWidget()
        self.page__category.setObjectName("page__category")
        self.verticalLayout__category_page = QVBoxLayout(self.page__category)
        self.verticalLayout__category_page.setSpacing(1)
        self.verticalLayout__category_page.setObjectName(
            "verticalLayout__category_page"
        )
        self.verticalLayout__category_page.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout__category = QVBoxLayout()
        self.verticalLayout__category.setSpacing(1)
        self.verticalLayout__category.setObjectName("verticalLayout__category")
        self.verticalLayout__category_page.addLayout(self.verticalLayout__category)
        self.stackedWidget__category.addWidget(self.page__category)
        self.splitter__cate_whole_vertical.addWidget(self.stackedWidget__category)
        self.verticalLayout__category_panel.addWidget(
            self.splitter__cate_whole_vertical
        )
        self.horizontalLayout__category_count = QHBoxLayout()
        self.horizontalLayout__category_count.setSpacing(3)
        self.horizontalLayout__category_count.setObjectName(
            "horizontalLayout__category_count"
        )
        self.horizontalLayout__category_count.setContentsMargins(3, -1, 3, -1)
        self.spacer__category_count = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__category_count.addItem(self.spacer__category_count)
        self.label__cate_count = QLabel(self.widget__category_panel)
        self.label__cate_count.setObjectName("label__cate_count")
        self.label__cate_count.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.label__cate_count.setText(_translate("0"))
        self.horizontalLayout__category_count.addWidget(self.label__cate_count)
        self.label__cate_count_suffix = QLabel(self.widget__category_panel)
        self.label__cate_count_suffix.setObjectName("label__cate_count_suffix")
        self.label__cate_count_suffix.setText(_translate("categories"))
        self.horizontalLayout__category_count.addWidget(self.label__cate_count_suffix)
        self.verticalLayout__category_panel.addLayout(
            self.horizontalLayout__category_count
        )
        self.splitter__whole_horizontal.addWidget(self.widget__category_panel)

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
        self.label__tag_pixmap.setPixmap(QPixmap(":/main/icons/ic_bookmark_white.png"))
        self.label__tag_pixmap.setScaledContents(True)
        self.label__tag_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__tag_pixmap.setText("")
        self.horizontalLayout__asset_tags.addWidget(self.label__tag_pixmap)
        self.label__tags = QLabel(self.widget__asset_panel)
        self.label__tags.setObjectName("label__tags")
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
        self.label__logged_id.setToolTip(_translate("Logged ID"))
        self.label__logged_id.setStatusTip(_translate("Displays the logged-in ID"))
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
        self.label__hda_count_suffix.setText(_translate("iHDA(s)"))
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
        self.pushButton__hda_info.setIcon(
            QIcon(":/main/icons/ic_border_color_white.png")
        )
        self.pushButton__hda_info.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__hda_info.setCheckable(True)
        self.pushButton__hda_info.setChecked(True)
        self.pushButton__hda_info.setAutoExclusive(True)
        self.pushButton__hda_info.setFlat(True)
        self.pushButton__hda_info.setToolTip(_translate("iHDA Info View"))
        self.pushButton__hda_info.setStatusTip(
            _translate("iHDA notes and tag information.")
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
            _translate("iHDA Location Record View")
        )
        self.pushButton__hda_loc_record.setStatusTip(
            _translate("Record iHDA location of current HIP file.")
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
        self.pushButton__hda_inside_node_view.setIcon(
            QIcon(":/main/icons/ic_find_in_page_white.png")
        )
        self.pushButton__hda_inside_node_view.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__hda_inside_node_view.setCheckable(True)
        self.pushButton__hda_inside_node_view.setAutoExclusive(True)
        self.pushButton__hda_inside_node_view.setFlat(True)
        self.pushButton__hda_inside_node_view.setToolTip(
            _translate("iHDA Inside Node View")
        )
        self.pushButton__hda_inside_node_view.setStatusTip(
            _translate("Find the iHDA node in the current HIP file.")
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
        self.pushButton__donate.setToolTip(_translate("Donate..."))
        self.pushButton__donate.setStatusTip(
            _translate("Donate. I need your help to make a better program.")
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
        self.textEdit__note.setStatusTip(_translate("Please enter a note for that HDA"))
        self.textEdit__note.setPlaceholderText(
            _translate("This is a note to write the selected iHDA.")
        )
        self.verticalLayout__note_editor.addWidget(self.textEdit__note)
        self.label__metadata_status = QLabel(self.widget__note_editor)
        self.label__metadata_status.setObjectName("label__metadata_status")
        self.verticalLayout__note_editor.addWidget(self.label__metadata_status)
        self.horizontalLayout__note_actions = QHBoxLayout()
        self.horizontalLayout__note_actions.setSpacing(3)
        self.horizontalLayout__note_actions.setObjectName(
            "horizontalLayout__note_actions"
        )
        self.horizontalLayout__note_actions.setContentsMargins(3, -1, 3, -1)
        self.spacer__note_actions = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__note_actions.addItem(self.spacer__note_actions)
        self.pushButton__note_save = QPushButton(self.widget__note_editor)
        self.pushButton__note_save.setObjectName("pushButton__note_save")
        self.pushButton__note_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__note_save.setIcon(QIcon(":/main/icons/ic_save_white.png"))
        self.pushButton__note_save.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__note_save.setFlat(True)
        self.pushButton__note_save.setToolTip(_translate("Save Note"))
        self.pushButton__note_save.setStatusTip(
            _translate("Save the text entered in the selected iHDA node")
        )
        self.pushButton__note_save.setText("")
        self.horizontalLayout__note_actions.addWidget(self.pushButton__note_save)
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
        self.textEdit__tag = QTextEdit(self.widget__tag_editor)
        self.textEdit__tag.setObjectName("textEdit__tag")
        self.textEdit__tag.setFrameShape(QFrame.Shape.NoFrame)
        self.textEdit__tag.setTabStopDistance(40.0)
        self.textEdit__tag.setStatusTip(_translate("Please enter a tag for that HDA"))
        self.textEdit__tag.setPlaceholderText(
            _translate("ex) #basic #explosion #smoke <Separated by #>")
        )
        self.verticalLayout__tag_editor.addWidget(self.textEdit__tag)
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
        self.pushButton__tag_save = QPushButton(self.widget__tag_editor)
        self.pushButton__tag_save.setObjectName("pushButton__tag_save")
        self.pushButton__tag_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__tag_save.setIcon(QIcon(":/main/icons/ic_save_white.png"))
        self.pushButton__tag_save.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__tag_save.setFlat(True)
        self.pushButton__tag_save.setToolTip(_translate("Save Tag"))
        self.pushButton__tag_save.setStatusTip(
            _translate("Save the tag you entered in the selected iHDA node")
        )
        self.pushButton__tag_save.setText("")
        self.horizontalLayout__tag_actions.addWidget(self.pushButton__tag_save)
        self.verticalLayout__tag_editor.addLayout(self.horizontalLayout__tag_actions)
        self.splitter__hda_info_vertical.addWidget(self.widget__tag_editor)
        self.verticalLayout__detail_page.addWidget(self.splitter__hda_info_vertical)
        self.stackedWidget__hda_infos.addWidget(self.page__hda_info)

    def _build_scene_records(self, window: QMainWindow) -> None:
        self.page__hda_loc_record = QWidget()
        self.page__hda_loc_record.setObjectName("page__hda_loc_record")
        self.verticalLayout__scene_record_page = QVBoxLayout(self.page__hda_loc_record)
        self.verticalLayout__scene_record_page.setSpacing(1)
        self.verticalLayout__scene_record_page.setObjectName(
            "verticalLayout__scene_record_page"
        )
        self.verticalLayout__scene_record_page.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout__scene_record_content = QVBoxLayout()
        self.verticalLayout__scene_record_content.setSpacing(1)
        self.verticalLayout__scene_record_content.setObjectName(
            "verticalLayout__scene_record_content"
        )
        self.horizontalLayout__scene_record_search = QHBoxLayout()
        self.horizontalLayout__scene_record_search.setSpacing(5)
        self.horizontalLayout__scene_record_search.setObjectName(
            "horizontalLayout__scene_record_search"
        )
        self.lineEdit__search_record = QLineEdit(self.page__hda_loc_record)
        self.lineEdit__search_record.setObjectName("lineEdit__search_record")
        self.lineEdit__search_record.setFrame(False)
        self.lineEdit__search_record.setClearButtonEnabled(True)
        self.lineEdit__search_record.setStatusTip(
            _translate("Please enter your search term")
        )
        self.lineEdit__search_record.setPlaceholderText(_translate("ex) untitled.hip"))
        self.horizontalLayout__scene_record_search.addWidget(
            self.lineEdit__search_record
        )
        self.checkBox__record_only_current_ihda = QCheckBox(self.page__hda_loc_record)
        self.checkBox__record_only_current_ihda.setObjectName(
            "checkBox__record_only_current_ihda"
        )
        self.checkBox__record_only_current_ihda.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__record_only_current_ihda.setIcon(
            QIcon(":/main/icons/show_all.png")
        )
        self.checkBox__record_only_current_ihda.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.checkBox__record_only_current_ihda.setToolTip(
            _translate("Show Only Current iHDA")
        )
        self.checkBox__record_only_current_ihda.setStatusTip(
            _translate(
                "When selected, displays information only from the current iHDA node."
            )
        )
        self.checkBox__record_only_current_ihda.setText("")
        self.horizontalLayout__scene_record_search.addWidget(
            self.checkBox__record_only_current_ihda
        )
        self.checkBox__record_only_current_hipfile = QCheckBox(
            self.page__hda_loc_record
        )
        self.checkBox__record_only_current_hipfile.setObjectName(
            "checkBox__record_only_current_hipfile"
        )
        self.checkBox__record_only_current_hipfile.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__record_only_current_hipfile.setIcon(
            QIcon(":/main/icons/hipfile.png")
        )
        self.checkBox__record_only_current_hipfile.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.checkBox__record_only_current_hipfile.setToolTip(
            _translate("Show Only Current HIP File")
        )
        self.checkBox__record_only_current_hipfile.setStatusTip(
            _translate(
                "When checked, only information from the current HIP file is displayed."
            )
        )
        self.checkBox__record_only_current_hipfile.setText("")
        self.horizontalLayout__scene_record_search.addWidget(
            self.checkBox__record_only_current_hipfile
        )
        self.spacer__scene_record_search = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__scene_record_search.addItem(
            self.spacer__scene_record_search
        )
        self.pushButton__cleanup_hda_record = QPushButton(self.page__hda_loc_record)
        self.pushButton__cleanup_hda_record.setObjectName(
            "pushButton__cleanup_hda_record"
        )
        self.pushButton__cleanup_hda_record.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__cleanup_hda_record.setIcon(QIcon(":/main/icons/clear.png"))
        self.pushButton__cleanup_hda_record.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__cleanup_hda_record.setFlat(True)
        self.pushButton__cleanup_hda_record.setToolTip(
            _translate("Remove any unnecessary iHDA Record data that does not exist.")
        )
        self.pushButton__cleanup_hda_record.setStatusTip(
            _translate("Remove any unnecessary iHDA Record data that does not exist.")
        )
        self.pushButton__cleanup_hda_record.setText("")
        self.horizontalLayout__scene_record_search.addWidget(
            self.pushButton__cleanup_hda_record
        )
        self.verticalLayout__scene_record_content.addLayout(
            self.horizontalLayout__scene_record_search
        )
        self.verticalLayout__hda_loc_record = QVBoxLayout()
        self.verticalLayout__hda_loc_record.setSpacing(1)
        self.verticalLayout__hda_loc_record.setObjectName(
            "verticalLayout__hda_loc_record"
        )
        self.verticalLayout__scene_record_content.addLayout(
            self.verticalLayout__hda_loc_record
        )
        self.horizontalLayout__scene_record_count = QHBoxLayout()
        self.horizontalLayout__scene_record_count.setSpacing(5)
        self.horizontalLayout__scene_record_count.setObjectName(
            "horizontalLayout__scene_record_count"
        )
        self.spacer__scene_record_count = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__scene_record_count.addItem(
            self.spacer__scene_record_count
        )
        self.label__loc_record_count = QLabel(self.page__hda_loc_record)
        self.label__loc_record_count.setObjectName("label__loc_record_count")
        self.label__loc_record_count.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.label__loc_record_count.setText(_translate("0"))
        self.horizontalLayout__scene_record_count.addWidget(
            self.label__loc_record_count
        )
        self.label__loc_record_count_suffix = QLabel(self.page__hda_loc_record)
        self.label__loc_record_count_suffix.setObjectName(
            "label__loc_record_count_suffix"
        )
        self.label__loc_record_count_suffix.setText(_translate("records"))
        self.horizontalLayout__scene_record_count.addWidget(
            self.label__loc_record_count_suffix
        )
        self.verticalLayout__scene_record_content.addLayout(
            self.horizontalLayout__scene_record_count
        )
        self.verticalLayout__scene_record_page.addLayout(
            self.verticalLayout__scene_record_content
        )
        self.stackedWidget__hda_infos.addWidget(self.page__hda_loc_record)

    def _build_inside_nodes(self, window: QMainWindow) -> None:
        self.page__hda_inside_hipfile = QWidget()
        self.page__hda_inside_hipfile.setObjectName("page__hda_inside_hipfile")
        self.verticalLayout__inside_page = QVBoxLayout(self.page__hda_inside_hipfile)
        self.verticalLayout__inside_page.setSpacing(1)
        self.verticalLayout__inside_page.setObjectName("verticalLayout__inside_page")
        self.verticalLayout__inside_page.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout__inside_content = QVBoxLayout()
        self.verticalLayout__inside_content.setSpacing(1)
        self.verticalLayout__inside_content.setObjectName(
            "verticalLayout__inside_content"
        )
        self.horizontalLayout__inside_search = QHBoxLayout()
        self.horizontalLayout__inside_search.setSpacing(3)
        self.horizontalLayout__inside_search.setObjectName(
            "horizontalLayout__inside_search"
        )
        self.checkBox__hda_inside_connect_to_view = QCheckBox(
            self.page__hda_inside_hipfile
        )
        self.checkBox__hda_inside_connect_to_view.setObjectName(
            "checkBox__hda_inside_connect_to_view"
        )
        self.checkBox__hda_inside_connect_to_view.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__hda_inside_connect_to_view.setIcon(
            QIcon(":/main/icons/show_all.png")
        )
        self.checkBox__hda_inside_connect_to_view.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.checkBox__hda_inside_connect_to_view.setToolTip(
            _translate("Connect to List/Table View")
        )
        self.checkBox__hda_inside_connect_to_view.setStatusTip(
            _translate(
                "When you enable this option, when you select an iHDA node in the List/Table view, only the information for that node is automatically displayed."
            )
        )
        self.checkBox__hda_inside_connect_to_view.setText("")
        self.horizontalLayout__inside_search.addWidget(
            self.checkBox__hda_inside_connect_to_view
        )
        self.comboBox__hda_inside_node = QComboBox(self.page__hda_inside_hipfile)
        self.comboBox__hda_inside_node.setObjectName("comboBox__hda_inside_node")
        self.comboBox__hda_inside_node.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.comboBox__hda_inside_node.setFrame(False)
        self.comboBox__hda_inside_node.setToolTip(
            _translate("Select which iHDA node to search.")
        )
        self.comboBox__hda_inside_node.setStatusTip(
            _translate("The selected iHDA node is retrieved from the current HIP file.")
        )
        self.horizontalLayout__inside_search.addWidget(self.comboBox__hda_inside_node)
        self.lineEdit__search_found_hda_inside_node = QLineEdit(
            self.page__hda_inside_hipfile
        )
        self.lineEdit__search_found_hda_inside_node.setObjectName(
            "lineEdit__search_found_hda_inside_node"
        )
        self.lineEdit__search_found_hda_inside_node.setFrame(False)
        self.lineEdit__search_found_hda_inside_node.setClearButtonEnabled(True)
        self.lineEdit__search_found_hda_inside_node.setStatusTip(
            _translate("Please enter your search term")
        )
        self.lineEdit__search_found_hda_inside_node.setPlaceholderText(
            _translate("ex) setup_fire")
        )
        self.horizontalLayout__inside_search.addWidget(
            self.lineEdit__search_found_hda_inside_node
        )
        self.spacer__inside_search = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__inside_search.addItem(self.spacer__inside_search)
        self.pushButton__hda_inside_node_refresh = QPushButton(
            self.page__hda_inside_hipfile
        )
        self.pushButton__hda_inside_node_refresh.setObjectName(
            "pushButton__hda_inside_node_refresh"
        )
        self.pushButton__hda_inside_node_refresh.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__hda_inside_node_refresh.setIcon(
            QIcon(":/main/icons/ic_refresh_white.png")
        )
        self.pushButton__hda_inside_node_refresh.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__hda_inside_node_refresh.setFlat(True)
        self.pushButton__hda_inside_node_refresh.setToolTip(
            _translate("Refresh the iHDA node search results in the current HIP file.")
        )
        self.pushButton__hda_inside_node_refresh.setStatusTip(
            _translate(
                "If the search results do not match the iHDA node in the current HIP file, click this button to refresh."
            )
        )
        self.pushButton__hda_inside_node_refresh.setText("")
        self.horizontalLayout__inside_search.addWidget(
            self.pushButton__hda_inside_node_refresh
        )
        self.verticalLayout__inside_content.addLayout(
            self.horizontalLayout__inside_search
        )
        self.verticalLayout__hda_inside_node = QVBoxLayout()
        self.verticalLayout__hda_inside_node.setSpacing(1)
        self.verticalLayout__hda_inside_node.setObjectName(
            "verticalLayout__hda_inside_node"
        )
        self.verticalLayout__inside_content.addLayout(
            self.verticalLayout__hda_inside_node
        )
        self.horizontalLayout__inside_count = QHBoxLayout()
        self.horizontalLayout__inside_count.setSpacing(3)
        self.horizontalLayout__inside_count.setObjectName(
            "horizontalLayout__inside_count"
        )
        self.horizontalLayout__inside_count.setContentsMargins(3, -1, 3, -1)
        self.spacer__inside_count = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__inside_count.addItem(self.spacer__inside_count)
        self.label__found_hda_inside_hipfile = QLabel(self.page__hda_inside_hipfile)
        self.label__found_hda_inside_hipfile.setObjectName(
            "label__found_hda_inside_hipfile"
        )
        self.label__found_hda_inside_hipfile.setText(_translate("found iHDA of "))
        self.horizontalLayout__inside_count.addWidget(
            self.label__found_hda_inside_hipfile
        )
        self.label__found_hda_inside_hipfile_count = QLabel(
            self.page__hda_inside_hipfile
        )
        self.label__found_hda_inside_hipfile_count.setObjectName(
            "label__found_hda_inside_hipfile_count"
        )
        self.label__found_hda_inside_hipfile_count.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.label__found_hda_inside_hipfile_count.setText(_translate("0"))
        self.horizontalLayout__inside_count.addWidget(
            self.label__found_hda_inside_hipfile_count
        )
        self.verticalLayout__inside_content.addLayout(
            self.horizontalLayout__inside_count
        )
        self.verticalLayout__inside_page.addLayout(self.verticalLayout__inside_content)
        self.stackedWidget__hda_infos.addWidget(self.page__hda_inside_hipfile)
        self.splitter__hda_info_whole_vertical.addWidget(self.stackedWidget__hda_infos)
        self.splitter__whole_horizontal.addWidget(
            self.splitter__hda_info_whole_vertical
        )
        self.verticalLayout__library_page.addWidget(self.splitter__whole_horizontal)
        self.stackedWidget__whole.addWidget(self.page__ihda)

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

    def _build_history_page(self, window: QMainWindow) -> None:
        self.page__history = QWidget()
        self.page__history.setObjectName("page__history")
        self.verticalLayout__history_page = QVBoxLayout(self.page__history)
        self.verticalLayout__history_page.setSpacing(1)
        self.verticalLayout__history_page.setObjectName("verticalLayout__history_page")
        self.verticalLayout__history_page.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout__history_content = QVBoxLayout()
        self.verticalLayout__history_content.setSpacing(1)
        self.verticalLayout__history_content.setObjectName(
            "verticalLayout__history_content"
        )
        self.splitter__ihda_hist_whole_vertical = QSplitter(self.page__history)
        self.splitter__ihda_hist_whole_vertical.setObjectName(
            "splitter__ihda_hist_whole_vertical"
        )
        self.splitter__ihda_hist_whole_vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__ihda_hist_whole_vertical.setHandleWidth(3)
        self._build_history_search(window)
        self._build_history_date_filter(window)
        self._build_history_results(window)

    def _build_history_search(self, window: QMainWindow) -> None:
        self.widget__history_search = QWidget(self.splitter__ihda_hist_whole_vertical)
        self.widget__history_search.setObjectName("widget__history_search")
        self.horizontalLayout__history_search = QHBoxLayout(self.widget__history_search)
        self.horizontalLayout__history_search.setSpacing(5)
        self.horizontalLayout__history_search.setObjectName(
            "horizontalLayout__history_search"
        )
        self.horizontalLayout__history_search.setContentsMargins(0, 0, 0, 0)
        self.comboBox__hist_ihda_node = QComboBox(self.widget__history_search)
        self.comboBox__hist_ihda_node.setObjectName("comboBox__hist_ihda_node")
        self.comboBox__hist_ihda_node.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.comboBox__hist_ihda_node.setFrame(False)
        self.comboBox__hist_ihda_node.setToolTip(_translate("Select iHDA node"))
        self.comboBox__hist_ihda_node.setStatusTip(
            _translate("It shows the history of the selected iHDA node.")
        )
        self.horizontalLayout__history_search.addWidget(self.comboBox__hist_ihda_node)
        self.spacer__history_search = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__history_search.addItem(self.spacer__history_search)
        self.horizontalLayout__history_query = QHBoxLayout()
        self.horizontalLayout__history_query.setSpacing(5)
        self.horizontalLayout__history_query.setObjectName(
            "horizontalLayout__history_query"
        )
        self.horizontalLayout__history_query.setContentsMargins(3, -1, 3, -1)
        self.comboBox__search_field_hist = QComboBox(self.widget__history_search)
        self.comboBox__search_field_hist.setObjectName("comboBox__search_field_hist")
        self.comboBox__search_field_hist.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.comboBox__search_field_hist.setFrame(False)
        self.comboBox__search_field_hist.setToolTip(_translate("Search Type"))
        self.comboBox__search_field_hist.setStatusTip(
            _translate("Decide what type to search for")
        )
        self.horizontalLayout__history_query.addWidget(self.comboBox__search_field_hist)
        self.checkBox__casesensitive_hda_hist = QCheckBox(self.widget__history_search)
        self.checkBox__casesensitive_hda_hist.setObjectName(
            "checkBox__casesensitive_hda_hist"
        )
        self.checkBox__casesensitive_hda_hist.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__casesensitive_hda_hist.setIcon(
            QIcon(":/main/icons/case_sensitive.png")
        )
        self.checkBox__casesensitive_hda_hist.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.checkBox__casesensitive_hda_hist.setToolTip(
            _translate("Word Case Sensitive")
        )
        self.checkBox__casesensitive_hda_hist.setStatusTip(
            _translate("It is case sensitive")
        )
        self.checkBox__casesensitive_hda_hist.setText("")
        self.horizontalLayout__history_query.addWidget(
            self.checkBox__casesensitive_hda_hist
        )
        self.lineEdit__search_hda_hist = QLineEdit(self.widget__history_search)
        self.lineEdit__search_hda_hist.setObjectName("lineEdit__search_hda_hist")
        self.lineEdit__search_hda_hist.setFrame(False)
        self.lineEdit__search_hda_hist.setClearButtonEnabled(True)
        self.lineEdit__search_hda_hist.setStatusTip(
            _translate("Please enter your search term")
        )
        self.lineEdit__search_hda_hist.setPlaceholderText(_translate("ex) wrangle"))
        self.horizontalLayout__history_query.addWidget(self.lineEdit__search_hda_hist)
        self.horizontalLayout__history_search.addLayout(
            self.horizontalLayout__history_query
        )
        self.spacer__history_search_end = QSpacerItem(
            24, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__history_search.addItem(self.spacer__history_search_end)

    def _build_history_date_filter(self, window: QMainWindow) -> None:
        self.horizontalLayout__history_date_filter = QHBoxLayout()
        self.horizontalLayout__history_date_filter.setObjectName(
            "horizontalLayout__history_date_filter"
        )
        self.checkBox__hist_search_date = QCheckBox(self.widget__history_search)
        self.checkBox__hist_search_date.setObjectName("checkBox__hist_search_date")
        self.checkBox__hist_search_date.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.checkBox__hist_search_date.setToolTip(_translate("Search History By Date"))
        self.checkBox__hist_search_date.setStatusTip(
            _translate("Search iHDA history by date")
        )
        self.checkBox__hist_search_date.setText(_translate("Date Search"))
        self.horizontalLayout__history_date_filter.addWidget(
            self.checkBox__hist_search_date
        )
        self.horizontalLayout__history_date_range = QHBoxLayout()
        self.horizontalLayout__history_date_range.setObjectName(
            "horizontalLayout__history_date_range"
        )
        self.dateEdit__hist_search_start = QDateEdit(self.widget__history_search)
        self.dateEdit__hist_search_start.setObjectName("dateEdit__hist_search_start")
        self.dateEdit__hist_search_start.setFrame(False)
        self.dateEdit__hist_search_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dateEdit__hist_search_start.setCalendarPopup(True)
        self.dateEdit__hist_search_start.setDate(QDate(2020, 1, 1))
        self.dateEdit__hist_search_start.setToolTip(_translate("Start Date"))
        self.dateEdit__hist_search_start.setStatusTip(
            _translate("Start date to search")
        )
        self.horizontalLayout__history_date_range.addWidget(
            self.dateEdit__hist_search_start
        )
        self.label__join_str = QLabel(self.widget__history_search)
        self.label__join_str.setObjectName("label__join_str")
        self.label__join_str.setSizePolicy(
            size_policy(
                self.label__join_str,
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__join_str.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__join_str.setText(_translate("~"))
        self.horizontalLayout__history_date_range.addWidget(self.label__join_str)
        self.dateEdit__hist_search_end = QDateEdit(self.widget__history_search)
        self.dateEdit__hist_search_end.setObjectName("dateEdit__hist_search_end")
        self.dateEdit__hist_search_end.setFrame(False)
        self.dateEdit__hist_search_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dateEdit__hist_search_end.setCalendarPopup(True)
        self.dateEdit__hist_search_end.setDate(QDate(2020, 12, 31))
        self.dateEdit__hist_search_end.setToolTip(_translate("End Date"))
        self.dateEdit__hist_search_end.setStatusTip(_translate("End date to search"))
        self.horizontalLayout__history_date_range.addWidget(
            self.dateEdit__hist_search_end
        )
        self.horizontalLayout__history_date_filter.addLayout(
            self.horizontalLayout__history_date_range
        )
        self.horizontalLayout__history_search.addLayout(
            self.horizontalLayout__history_date_filter
        )
        self.spacer__history_search_middle = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__history_search.addItem(
            self.spacer__history_search_middle
        )
        self.splitter__ihda_hist_whole_vertical.addWidget(self.widget__history_search)

    def _build_history_results(self, window: QMainWindow) -> None:
        self.widget__history_view = QWidget(self.splitter__ihda_hist_whole_vertical)
        self.widget__history_view.setObjectName("widget__history_view")
        self.verticalLayout__history = QVBoxLayout(self.widget__history_view)
        self.verticalLayout__history.setSpacing(1)
        self.verticalLayout__history.setObjectName("verticalLayout__history")
        self.verticalLayout__history.setContentsMargins(0, 0, 0, 0)
        self.splitter__ihda_hist_whole_vertical.addWidget(self.widget__history_view)
        self.verticalLayout__history_content.addWidget(
            self.splitter__ihda_hist_whole_vertical
        )
        self.horizontalLayout__history_footer = QHBoxLayout()
        self.horizontalLayout__history_footer.setSpacing(5)
        self.horizontalLayout__history_footer.setObjectName(
            "horizontalLayout__history_footer"
        )
        self.label__hist_tag_pixmap = QLabel(self.page__history)
        self.label__hist_tag_pixmap.setObjectName("label__hist_tag_pixmap")
        self.label__hist_tag_pixmap.setMaximumSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.label__hist_tag_pixmap.setPixmap(
            QPixmap(":/main/icons/ic_bookmark_white_18dp.png")
        )
        self.label__hist_tag_pixmap.setScaledContents(True)
        self.label__hist_tag_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__hist_tag_pixmap.setText("")
        self.horizontalLayout__history_footer.addWidget(self.label__hist_tag_pixmap)
        self.label__hist_tags = QLabel(self.page__history)
        self.label__hist_tags.setObjectName("label__hist_tags")
        self.label__hist_tags.setText("")
        self.horizontalLayout__history_footer.addWidget(self.label__hist_tags)
        self.spacer__history_footer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__history_footer.addItem(self.spacer__history_footer)
        self.horizontalLayout__history_count = QHBoxLayout()
        self.horizontalLayout__history_count.setSpacing(5)
        self.horizontalLayout__history_count.setObjectName(
            "horizontalLayout__history_count"
        )
        self.label__hist_cnt = QLabel(self.page__history)
        self.label__hist_cnt.setObjectName("label__hist_cnt")
        self.label__hist_cnt.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.label__hist_cnt.setText(_translate("0"))
        self.horizontalLayout__history_count.addWidget(self.label__hist_cnt)
        self.label__hist_cnt_suffix = QLabel(self.page__history)
        self.label__hist_cnt_suffix.setObjectName("label__hist_cnt_suffix")
        self.label__hist_cnt_suffix.setText(_translate("histories"))
        self.horizontalLayout__history_count.addWidget(self.label__hist_cnt_suffix)
        self.horizontalLayout__history_footer.addLayout(
            self.horizontalLayout__history_count
        )
        self.verticalLayout__history_content.addLayout(
            self.horizontalLayout__history_footer
        )
        self.verticalLayout__history_page.addLayout(
            self.verticalLayout__history_content
        )
        self.stackedWidget__whole.addWidget(self.page__history)
        self.splitter__whole_vertical.addWidget(self.stackedWidget__whole)

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
        self.textBrowser__debug.setStatusTip(_translate("Show debug of application"))
        self.verticalLayout__debug_console.addWidget(self.textBrowser__debug)
        self.splitter__whole_vertical.addWidget(self.widget__debug_console)
        self.verticalLayout__main.addWidget(self.splitter__whole_vertical)
        window.setCentralWidget(self.centralwidget)

    def _build_menus_and_toolbar(self, window: QMainWindow) -> None:
        self.menubar = QMenuBar(window)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1472, 31))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuFile.setTitle(_translate("File"))
        self.menuDatabase = QMenu(self.menuFile)
        self.menuDatabase.setObjectName("menuDatabase")
        self.menuDatabase.setIcon(QIcon(":/main/icons/database.png"))
        self.menuDatabase.setTitle(_translate("Database"))
        self.menuTools = QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menuTools.setTitle(_translate("Tools"))
        self.menuConfig = QMenu(self.menuTools)
        self.menuConfig.setObjectName("menuConfig")
        self.menuConfig.setIcon(
            QIcon(":/main/icons/ic_settings_applications_white.png")
        )
        self.menuConfig.setTitle(_translate("Config"))
        self.menuTheme = QMenu(self.menuConfig)
        self.menuTheme.setObjectName("menuTheme")
        self.menuTheme.setIcon(QIcon(":/main/icons/ic_palette_white.png"))
        self.menuTheme.setTitle(_translate("Theme"))
        self.menuDownload = QMenu(self.menuTools)
        self.menuDownload.setObjectName("menuDownload")
        self.menuDownload.setIcon(QIcon(":/main/icons/ic_language_white.png"))
        self.menuDownload.setTitle(_translate("Download"))
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.setTitle(_translate("Help"))
        self.menuData = QMenu(self.menubar)
        self.menuData.setObjectName("menuData")
        self.menuData.setTitle(_translate("Data"))
        self.menuHistory = QMenu(self.menuData)
        self.menuHistory.setObjectName("menuHistory")
        self.menuHistory.setIcon(QIcon(":/main/icons/ic_query_builder_white.png"))
        self.menuHistory.setTitle(_translate("History"))
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
        self.menuConfig.addAction(self.menuTheme.menuAction())
        self.menuConfig.addSeparator()
        self.menuConfig.addAction(self.actionReset)
        self.menuTheme.addAction(self.actionDefault)
        self.menuTheme.addAction(self.actionDark_blue)
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
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actioniHDA)
        self.toolBar.addAction(self.actionHistory)
        self.toolBar.addAction(self.actionVideo_Player)
        self.toolBar.addAction(self.actionWeb)
        self.toolBar.addSeparator()
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
        self.toolBar.setWindowTitle(_translate("toolBar"))
        self.stackedWidget__whole.setCurrentIndex(0)
        self.stackedWidget__category.setCurrentIndex(0)
        self.stackedWidget__hda_infos.setCurrentIndex(0)
