# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'detail_view.ui',
# licensing of 'detail_view.ui' applies.
#
# Created: Mon May 25 17:19:28 2020
#      by: pyside2-uic  running on PySide2 5.13.1
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_Dialog__detail_view(object):
    def setupUi(self, Dialog__detail_view):
        Dialog__detail_view.setObjectName("Dialog__detail_view")
        Dialog__detail_view.resize(869, 524)
        font = QtGui.QFont()
        font.setPointSize(11)
        Dialog__detail_view.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/detail_view_main/icons/viewport_logo_trans.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Dialog__detail_view.setWindowIcon(icon)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog__detail_view)
        self.verticalLayout_2.setSpacing(1)
        self.verticalLayout_2.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(3)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label__pixmap = QtWidgets.QLabel(Dialog__detail_view)
        self.label__pixmap.setText("")
        self.label__pixmap.setAlignment(QtCore.Qt.AlignCenter)
        self.label__pixmap.setObjectName("label__pixmap")
        self.verticalLayout.addWidget(self.label__pixmap)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.textBrowser__detail = QtWidgets.QTextBrowser(Dialog__detail_view)
        self.textBrowser__detail.setTabStopWidth(40)
        self.textBrowser__detail.setObjectName("textBrowser__detail")
        self.horizontalLayout.addWidget(self.textBrowser__detail)
        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog__detail_view)
        QtCore.QMetaObject.connectSlotsByName(Dialog__detail_view)

    def retranslateUi(self, Dialog__detail_view):
        Dialog__detail_view.setWindowTitle(QtWidgets.QApplication.translate("Dialog__detail_view", "iHDA Detail View", None, -1))

import detail_view_rc

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog__detail_view = QtWidgets.QDialog()
    ui = Ui_Dialog__detail_view()
    ui.setupUi(Dialog__detail_view)
    Dialog__detail_view.show()
    sys.exit(app.exec_())

