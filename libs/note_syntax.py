#!/usr/bin/env python
from __future__ import annotations

from typing import Any
from PySide6 import QtWidgets

# author            : Seongcheol Jeon
# email             : saelly55@gmail.com
# create date       : 2020.01.28 23:03
# modify date       :
# decription        :


from PySide6 import QtGui, QtCore


class NoteHighLighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super(NoteHighLighter, self).__init__(parent)
        self.parent = parent
        keyword = QtGui.QTextCharFormat()
        importantkeyword = QtGui.QTextCharFormat()
        assignment_operator = QtGui.QTextCharFormat()
        delimiter = QtGui.QTextCharFormat()
        number = QtGui.QTextCharFormat()
        comment = QtGui.QTextCharFormat()
        important = QtGui.QTextCharFormat()
        string = QtGui.QTextCharFormat()
        sing_quoted_string = QtGui.QTextCharFormat()
        self.__highlightingRules = list()

        brush = QtGui.QBrush(QtGui.QColor("#268BD2"), QtCore.Qt.SolidPattern)
        keyword.setForeground(brush)
        keyword.setFontWeight(QtGui.QFont.Bold)
        tmplst = [
            "load",
            "loaded",
            "save",
            "saved",
            "date",
            "description",
            "author",
            "user",
            "artist",
            "note",
            "path",
            "name",
            "dir",
            "file",
            "files",
            "directory",
            "houdini",
            "nuke",
            "maya",
            "linux",
            "windows",
            "mac",
            "sop",
            "out",
            "driver",
            "cop",
            "chop",
            "dop",
            "level",
            "object",
            "obj",
            "node",
            "asset",
            "assets",
            "hip",
            "hipfile",
            "hipname",
            "nukefile",
            "mayafile",
            "alembic",
            "bgeo",
            "bake",
            "simulation",
            "cache",
            "saveas",
            "open",
            "create",
            "created",
            "time",
            "datetime",
            "range",
            "distortion",
            "size",
            "plate",
            "project",
            "shot",
            "cut",
            "element",
            "version",
            "ver",
            "wip",
            "fx",
            "comp",
            "precomp",
            "lighting",
            "modeling",
            "frame",
            "fps",
            "sf",
            "ef",
            "Sun",
            "Mon",
            "Tue",
            "Wed",
            "Thu",
            "Fri",
            "Sat",
            "AM",
            "PM",
            "individual hda",
            "sunday",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "edit",
            "edited",
            "editing",
            "hda",
            "hdafile",
            "tag",
            "tags",
        ]
        keylst = tmplst[:]
        keylst.extend([x.upper() for x in keylst])
        keylst.extend([x.lower() for x in keylst])
        keylst.extend([x.capitalize() for x in tmplst])
        # keywords = QtCore.QStringList(keylst)
        keywords = keylst
        for word in keywords:
            pattern = QtCore.QRegularExpression("\\b" + word + "\\b")
            rule = HighlightingRule(pattern, keyword)
            self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor("#B85900"), QtCore.Qt.SolidPattern)
        importantkeyword.setForeground(brush)
        importantkeyword.setFontWeight(QtGui.QFont.Bold)
        tmplst = [
            "important",
            "critical",
            "pub",
            "wip",
        ]
        keylst = tmplst[:]
        keylst.extend([x.upper() for x in keylst])
        keylst.extend([x.lower() for x in keylst])
        keylst.extend([x.capitalize() for x in tmplst])
        # keywords = QtCore.QStringList(keylst)
        keywords = keylst
        for word in keywords:
            pattern = QtCore.QRegularExpression("\\b" + word + "\\b")
            rule = HighlightingRule(pattern, importantkeyword)
            self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtCore.Qt.darkCyan, QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegularExpression("(<){1,2}-")
        assignment_operator.setForeground(brush)
        assignment_operator.setFontWeight(QtGui.QFont.Bold)
        rule = HighlightingRule(pattern, assignment_operator)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor("#859900"), QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegularExpression(r"[\)\(]+|[\{\}]+|[][]+")
        delimiter.setForeground(brush)
        delimiter.setFontWeight(QtGui.QFont.Bold)
        rule = HighlightingRule(pattern, delimiter)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor("#94558D"), QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegularExpression(r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?")
        pattern.setPatternOptions(QtCore.QRegularExpression.InvertedGreedinessOption)
        number.setForeground(brush)
        rule = HighlightingRule(pattern, number)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegularExpression("^!!![^\n]*")
        important.setForeground(brush)
        important.setFontWeight(QtGui.QFont.Bold)
        rule = HighlightingRule(pattern, important)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtCore.Qt.darkGray, QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegularExpression("#[^\n]*")
        comment.setForeground(brush)
        rule = HighlightingRule(pattern, comment)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor("#DC322F"), QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegularExpression('".*"')
        pattern.setPatternOptions(QtCore.QRegularExpression.InvertedGreedinessOption)
        string.setForeground(brush)
        rule = HighlightingRule(pattern, string)
        self.__highlightingRules.append(rule)

        pattern = QtCore.QRegularExpression("'.*'")
        pattern.setPatternOptions(QtCore.QRegularExpression.InvertedGreedinessOption)
        sing_quoted_string.setForeground(brush)
        rule = HighlightingRule(pattern, sing_quoted_string)
        self.__highlightingRules.append(rule)

    def highlightBlock(self, text: str) -> None:
        for rule in self.__highlightingRules:
            matches = rule.pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), rule.format
                )
        self.setCurrentBlockState(0)


class HighlightingRule(object):
    def __init__(self, pattern: Any, fmt: QtGui.QTextCharFormat) -> None:
        self.pattern = pattern
        self.format = fmt


if __name__ == "__main__":
    pass
