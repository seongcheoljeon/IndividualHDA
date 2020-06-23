# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.25 01:20:06
# modified date:    
# description:

from re import compile, DOTALL
from imp import reload

from PySide2 import QtWidgets, QtGui

from widgets.rename_ihda import rename_ihda_ui

reload(rename_ihda_ui)


class RenameIHDA(QtWidgets.QDialog, rename_ihda_ui.Ui_Dialog__rename_ihda):
    def __init__(self, parent=None):
        super(RenameIHDA, self).__init__(parent)
        self.setupUi(self)
        self.label__bridge.setText('>>>>>')
        self.__final_ihda_name = None
        self.__is_valid_ihda_name = False
        self.__regex_spec_first_char = compile(r'^[^a-zA-Z0-9_]', DOTALL)
        self.__regex_find_sepc_char = compile(r'[^a-zA-Z0-9.\-_]', DOTALL)
        self.__connections()
        self.__valid_ihda_name(self.lineEdit__input_ihda_name.text())

    def __connections(self):
        self.lineEdit__input_ihda_name.textChanged.connect(self.__valid_ihda_name)

    @property
    def final_ihda_name(self):
        return self.__final_ihda_name

    def __valid_ihda_name(self, text):
        text = text.replace(' ', '_')
        self.set_new_ihda_name(text)
        old_ihda_name = self.label__old_ihda_name.text()
        if not len(text):
            self.set_confirm_pixmap(False)
            self.set_confirm_text('Nothing was entered.')
            self.is_valid_ihda_name = False
        elif text == old_ihda_name:
            self.set_confirm_pixmap(False)
            self.set_confirm_text('Same as the current iHDA name.')
            self.is_valid_ihda_name = False
        elif text.isdigit():
            self.set_confirm_pixmap(False)
            self.set_confirm_text('Everythong cannot consist of numbers.')
            self.is_valid_ihda_name = False
        elif text.startswith('_'):
            self.set_confirm_pixmap(False)
            self.set_confirm_text('The first character cannot be _(underscore).')
            self.is_valid_ihda_name = False
        elif text[0].isdigit():
            self.set_confirm_pixmap(False)
            self.set_confirm_text('The first character cannot be a number.')
            self.is_valid_ihda_name = False
        elif text.startswith('.'):
            self.set_confirm_pixmap(False)
            self.set_confirm_text('The first character cannot be .(full stop).')
            self.is_valid_ihda_name = False
        elif len(text) <= 2:
            self.set_confirm_pixmap(False)
            self.set_confirm_text('Must be at least 2 characters.')
            self.is_valid_ihda_name = False
        elif len(text) >= 255:
            self.set_confirm_pixmap(False)
            self.set_confirm_text('It cannot exceed 255 characters.')
            self.is_valid_ihda_name = False
        elif self.__regex_spec_first_char.match(text) is not None:
            find_str = self.__regex_spec_first_char.match(text).group()
            self.set_confirm_pixmap(False)
            self.set_confirm_text(
                'The first character cannot contain special characters. ({0})'.format(find_str))
            self.is_valid_ihda_name = False
        elif self.__regex_find_sepc_char.search(text) is not None:
            find_str = self.__regex_find_sepc_char.search(text).group()
            self.set_confirm_pixmap(False)
            self.set_confirm_text(
                'There should be no special characters between the names. ({0})'.format(find_str))
            self.is_valid_ihda_name = False
        else:
            self.set_confirm_pixmap(True)
            self.set_confirm_text('Valid iHDA name.')
            self.is_valid_ihda_name = True
            self.__final_ihda_name = text

    def accept(self):
        if not self.__is_valid_ihda_name:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setWindowTitle('iHDA Rename')
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText('It\'s not a valid iHDA name.')
            msgbox.setDetailedText('{0}'.format(self.label__confirm_ihda_name.text()))
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec_()

    def clear_parms(self):
        self.lineEdit__input_ihda_name.clear()
        self.label__confirm_ihda_name.clear()
        self.label__new_ihda_name.clear()
        self.label__old_ihda_name.clear()
        self.__final_ihda_name = None
        self.set_confirm_pixmap(False)
        self.is_valid_ihda_name = False

    @property
    def is_valid_ihda_name(self):
        return self.__is_valid_ihda_name

    @is_valid_ihda_name.setter
    def is_valid_ihda_name(self, flag):
        assert isinstance(flag, bool)
        self.__is_valid_ihda_name = flag

    def set_old_ihda_name(self, text):
        self.label__old_ihda_name.setText(text)

    def set_new_ihda_name(self, text):
        self.label__new_ihda_name.setText(text)

    def set_confirm_text(self, text):
        self.label__confirm_ihda_name.setText(text)

    def set_confirm_pixmap(self, flag):
        if flag:
            self.label__confirm_ihda_name_pixmap.setPixmap(
                QtGui.QPixmap(":/main/icons/ic_done_white.png"))
        else:
            self.label__confirm_ihda_name_pixmap.setPixmap(
                QtGui.QPixmap(":/main/icons/ic_clear_white.png"))

