from __future__ import annotations

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.25 01:20:06
# modified date:
# description:
from PySide6 import QtGui, QtWidgets

from widgets.rename_ihda.layout import RenameLayout
from widgets.rename_ihda.presenter import NameValidation, RenamePresenter


class RenameIHDA(QtWidgets.QDialog, RenameLayout):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.build_ui(self)
        self.label__bridge.setText(">>>>>")
        self.__final_ihda_name = ""
        self.__is_valid_ihda_name = False
        self._presenter = RenamePresenter(self)
        self.__connections()
        self.__valid_ihda_name(self.lineEdit__input_ihda_name.text())

    def __connections(self) -> None:
        self.lineEdit__input_ihda_name.textChanged.connect(self.__valid_ihda_name)

    @property
    def final_ihda_name(self) -> str:
        return self.__final_ihda_name

    def __valid_ihda_name(self, text: str) -> None:
        self._presenter.edit(text, self.label__old_ihda_name.text())

    def show_validation(self, validation: NameValidation) -> None:
        self.set_new_ihda_name(validation.name)
        self.set_confirm_pixmap(validation.valid)
        self.set_confirm_text(validation.error or "Valid iHDA name.")
        self.is_valid_ihda_name = validation.valid
        self.__final_ihda_name = validation.name if validation.valid else ""

    def accept(self) -> None:
        if not self.__is_valid_ihda_name:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setWindowTitle("iHDA Rename")
            msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msgbox.setText("It's not a valid iHDA name.")
            msgbox.setDetailedText(f"{self.label__confirm_ihda_name.text()}")
            msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            _ = msgbox.exec()
        else:
            super().accept()

    def clear_parms(self) -> None:
        self.lineEdit__input_ihda_name.clear()
        self.label__confirm_ihda_name.clear()
        self.label__new_ihda_name.clear()
        self.label__old_ihda_name.clear()
        self.__final_ihda_name = ""
        self.set_confirm_pixmap(False)
        self.is_valid_ihda_name = False

    @property
    def is_valid_ihda_name(self) -> bool:
        return self.__is_valid_ihda_name

    @is_valid_ihda_name.setter
    def is_valid_ihda_name(self, flag: bool) -> None:
        assert isinstance(flag, bool)
        self.__is_valid_ihda_name = flag

    def set_old_ihda_name(self, text: str) -> None:
        self.label__old_ihda_name.setText(text)
        self.__valid_ihda_name(self.lineEdit__input_ihda_name.text())

    def set_new_ihda_name(self, text: str) -> None:
        self.label__new_ihda_name.setText(text)

    def set_confirm_text(self, text: str) -> None:
        self.label__confirm_ihda_name.setText(text)

    def set_confirm_pixmap(self, flag: bool) -> None:
        if flag:
            self.label__confirm_ihda_name_pixmap.setPixmap(
                QtGui.QPixmap(":/main/icons/ic_done_white.png")
            )
        else:
            self.label__confirm_ihda_name_pixmap.setPixmap(
                QtGui.QPixmap(":/main/icons/ic_clear_white.png")
            )
