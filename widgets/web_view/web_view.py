# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.23 02:03:49
# modified date:    
# description:      

import logging
from imp import reload
from urllib2 import urlopen, URLError

from PySide2 import QtWidgets, QtCore
from PySide2.QtWebEngineWidgets import QWebEngineFullScreenRequest, QWebEngineProfile

import public
from widgets.web_view import web_view_ui, web_ui_settings
from libs import log_handler

try:
    import hou
except ImportError as err:
    pass

reload(public)
reload(web_view_ui)
reload(web_ui_settings)
reload(log_handler)


class WebView(QtWidgets.QWidget, web_view_ui.Ui_Form__web):
    def __init__(self, help_site=None, parent=None):
        super(WebView, self).__init__(parent)
        self.setupUi(self)
        self.__ui_settings = web_ui_settings.WebUISettings(window=self)
        self.__blank_site = 'about:blank'
        self.__help_site = help_site

        self.__init_set()
        self.__connections()

    def __init_set(self):
        self.webEngineView__webview.page().profile().setPersistentCookiesPolicy(
            QWebEngineProfile.NoPersistentCookies)
        self.__set_init_load()
        self.__load_config()
        self.__load()

    def __connections(self):
        self.webEngineView__webview.page().titleChanged.connect(self.setWindowTitle)
        self.webEngineView__webview.page().urlChanged.connect(self.__url_changed)
        self.webEngineView__webview.loadStarted.connect(self.__load_started)
        self.webEngineView__webview.loadProgress.connect(self.__load_progress)
        self.webEngineView__webview.loadFinished.connect(self.__load_finished)
        # self.webEngineView__webview.page().fullScreenRequested.connect(self.__full_screen)
        #
        self.pushButton__back_page.clicked.connect(self.__back)
        self.pushButton__forward_page.clicked.connect(self.__forward)
        self.pushButton__refresh_page.clicked.connect(self.__reload)
        self.pushButton__close_page.clicked.connect(self.__stop)
        self.pushButton__home_page.clicked.connect(self.__init_set)
        self.pushButton__zoomin.clicked.connect(self.__zoom_in)
        self.pushButton__zoomout.clicked.connect(self.__zoom_out)
        self.pushButton__reset_zoom.clicked.connect(self.__reset_zoom)
        self.lineEdit__address.returnPressed.connect(self.__load)
        #
        self.pushButton__sidefx.clicked.connect(lambda: self.__load(url=self.__urls()['sidefx']))
        self.pushButton__odforce.clicked.connect(lambda: self.__load(url=self.__urls()['odforce']))
        self.pushButton__google.clicked.connect(lambda: self.__load(url=self.__urls()['google']))
        self.pushButton__translation.clicked.connect(lambda: self.__load(url=self.__urls()['translation']))
        self.pushButton__youtube.clicked.connect(lambda: self.__load(url=self.__urls()['youtube']))
        self.pushButton__vimeo.clicked.connect(lambda: self.__load(url=self.__urls()['vimeo']))
        self.pushButton__help.clicked.connect(lambda: self.__load(url=self.__urls()['help']))

    def closeEvent(self, event):
        self.__ui_settings.save_main_window_geometry()
        self.__ui_settings.save_splitter_status()
        self.__ui_settings.save_cfg_dict_to_file()
        self.webEngineView__webview.page().profile().clearHttpCache()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        event.accept()

    def __load_config(self):
        if public.Paths.json_web_filepath.exists():
            self.__ui_settings.load_main_window_geometry()
            self.__ui_settings.load_splitter_status()
            self.__ui_settings.load_cfg_dict_from_file()

    @staticmethod
    def is_network_connected():
        try:
            urlopen('http://216.58.192.142', timeout=1)
            return True
        except URLError as err:
            return False

    def __set_init_load(self):
        if self.__help_site is None:
            if WebView.is_network_connected():
                self.lineEdit__address.setText(
                    'https://www.youtube.com/channel/UCy4fuTNjIPeKPB4hacaP_6A?view_as=subscriber')
            else:
                self.lineEdit__address.setText(self.__blank_site)
        else:
            self.lineEdit__address.setText(self.__help_site)

    def __load(self, url=None):
        if url is None:
            url = QtCore.QUrl.fromUserInput(self.lineEdit__address.text())
        else:
            url = QtCore.QUrl.fromUserInput(url)
        if url.isValid():
            self.webEngineView__webview.load(url)

    def __full_screen(self, request):
        req = QWebEngineFullScreenRequest(request)
        req.accept()

    @QtCore.Slot()
    def __load_started(self):
        log_handler.LogHandler.log_msg(method=logging.info, msg='start loading iHDA webview')

    @QtCore.Slot(int)
    def __load_progress(self, prog):
        log_handler.LogHandler.log_msg(method=logging.info, msg='loading progress: {0}'.format(prog))

    @QtCore.Slot(bool)
    def __load_finished(self, status):
        if status:
            log_handler.LogHandler.log_msg(method=logging.info, msg='iHDA webview loading ends')
        else:
            log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA webview loading ends failed')

    def __back(self):
        self.webEngineView__webview.back()

    def __forward(self):
        self.webEngineView__webview.forward()

    def __reload(self):
        self.webEngineView__webview.reload()

    def __stop(self):
        self.webEngineView__webview.stop()

    def __url_changed(self, url):
        self.lineEdit__address.setText(url.toString())

    def __set_view_by_zoom_factor(self, zoom_factor):
        if public.IS_HOUDINI:
            self.webEngineView__webview.setZoomFactor(zoom_factor * hou.ui.globalScaleFactor())
        else:
            self.webEngineView__webview.setZoomFactor(zoom_factor)
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='current zoom factor of the webview: {0}'.format(self.curt_zoom_value))

    def __zoom_in(self):
        new_zoom = self.webEngineView__webview.zoomFactor() * 1.1
        if new_zoom <= WebView.__maximum_zoom_factor():
            self.__set_view_by_zoom_factor(new_zoom)

    def __zoom_out(self):
        new_zoom = self.webEngineView__webview.zoomFactor() / 2
        if new_zoom >= WebView.__minimum_zoom_factor():
            self.__set_view_by_zoom_factor(new_zoom)

    def __reset_zoom(self):
        self.__set_view_by_zoom_factor(1)

    @property
    def curt_zoom_value(self):
        percent = int(self.webEngineView__webview.zoomFactor() * 100)
        return percent

    @staticmethod
    def __maximum_zoom_factor():
        if public.IS_HOUDINI:
            return 5 * hou.ui.globalScaleFactor()
        else:
            return 5

    @staticmethod
    def __minimum_zoom_factor():
        if public.IS_HOUDINI:
            return 0.25 * hou.ui.globalScaleFactor()
        else:
            return 0.25

    def __urls(self):
        url_dat = {
            'sidefx': 'https://www.sidefx.com/learn/',
            'odforce': 'https://forums.odforce.net/',
            'google': 'https://www.google.com/',
            'translation': 'https://translate.google.com/?hl=ko&tab=wT1&authuser=0',
            'youtube': 'https://www.youtube.com/',
            'vimeo': 'https://vimeo.com/',
            'help': self.__blank_site if self.__help_site is None else self.__help_site
        }
        return url_dat

