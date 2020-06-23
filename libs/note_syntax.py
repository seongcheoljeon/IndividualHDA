#!/usr/bin/env python
# encoding=utf-8

# author            : Seongcheol Jeon
# email             : saelly55@gmail.com
# create date       : 2020.01.28 23:03
# modify date       :
# decription        :


from PySide2 import QtGui, QtCore


class NoteHighLighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
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

        brush = QtGui.QBrush(QtGui.QColor('#268BD2'), QtCore.Qt.SolidPattern)
        keyword.setForeground(brush)
        keyword.setFontWeight(QtGui.QFont.Bold)
        tmplst = [
            'load', 'loaded', 'save', 'saved', 'date', 'description',
            'author', 'user', 'artist', 'note', 'path', 'name', 'dir',
            'file', 'files', 'directory', 'houdini', 'nuke', 'maya',
            'linux', 'windows', 'mac', 'sop', 'out', 'driver', 'cop', 'chop',
            'dop', 'level', 'object', 'obj', 'node', 'asset', 'assets', 'hip', 'hipfile',
            'hipname', 'nukefile', 'mayafile', 'alembic', 'bgeo', 'bake',
            'simulation', 'cache', 'saveas', 'open', 'create', 'created',
            'time', 'datetime', 'range', 'distortion', 'size', 'plate',
            'project', 'shot', 'cut', 'element', 'version', 'ver', 'wip',
            'fx', 'comp', 'precomp', 'lighting', 'modeling', 'frame',
            'fps', 'sf', 'ef', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri',
            'Sat', 'AM', 'PM', 'individual hda',
            'sunday', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'edit', 'edited', 'editing', 'hda', 'hdafile',
            'tag', 'tags',
        ]
        keylst = tmplst[:]
        keylst.extend(map(lambda x: x.upper(), keylst))
        keylst.extend(map(lambda x: x.lower(), keylst))
        keylst.extend(map(lambda x: x.capitalize(), tmplst))
        # keywords = QtCore.QStringList(keylst)
        keywords = keylst
        for word in keywords:
            pattern = QtCore.QRegExp('\\b' + word + '\\b')
            rule = HighlightingRule(pattern, keyword)
            self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor('#B85900'), QtCore.Qt.SolidPattern)
        importantkeyword.setForeground(brush)
        importantkeyword.setFontWeight(QtGui.QFont.Bold)
        tmplst = [
            'important', 'critical', 'pub', 'wip',
        ]
        keylst = tmplst[:]
        keylst.extend(map(lambda x: x.upper(), keylst))
        keylst.extend(map(lambda x: x.lower(), keylst))
        keylst.extend(map(lambda x: x.capitalize(), tmplst))
        # keywords = QtCore.QStringList(keylst)
        keywords = keylst
        for word in keywords:
            pattern = QtCore.QRegExp('\\b' + word + '\\b')
            rule = HighlightingRule(pattern, importantkeyword)
            self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtCore.Qt.darkCyan, QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegExp('(<){1,2}-')
        assignment_operator.setForeground(brush)
        assignment_operator.setFontWeight(QtGui.QFont.Bold)
        rule = HighlightingRule(pattern, assignment_operator)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor('#859900'), QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegExp('[\)\(]+|[\{\}]+|[][]+')
        delimiter.setForeground(brush)
        delimiter.setFontWeight(QtGui.QFont.Bold)
        rule = HighlightingRule(pattern, delimiter)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor('#94558D'), QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegExp('[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?')
        pattern.setMinimal(True)
        number.setForeground(brush)
        rule = HighlightingRule(pattern, number)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegExp('^!!![^\n]*')
        important.setForeground(brush)
        important.setFontWeight(QtGui.QFont.Bold)
        rule = HighlightingRule(pattern, important)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtCore.Qt.darkGray, QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegExp('#[^\n]*')
        comment.setForeground(brush)
        rule = HighlightingRule(pattern, comment)
        self.__highlightingRules.append(rule)

        brush = QtGui.QBrush(QtGui.QColor('#DC322F'), QtCore.Qt.SolidPattern)
        pattern = QtCore.QRegExp('\".*\"')
        pattern.setMinimal(True)
        string.setForeground(brush)
        rule = HighlightingRule(pattern, string)
        self.__highlightingRules.append(rule)

        pattern = QtCore.QRegExp('\'.*\'')
        pattern.setMinimal(True)
        sing_quoted_string.setForeground(brush)
        rule = HighlightingRule(pattern, sing_quoted_string)
        self.__highlightingRules.append(rule)

    def highlightBlock(self, text):
        for rule in self.__highlightingRules:
            expression = QtCore.QRegExp(rule.pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, rule.format)
                try:
                    index = text.indexOf(expression, index + length)
                except AttributeError:
                    index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)


class HighlightingRule(object):
    def __init__(self, pattern, fmt):
        self.pattern = pattern
        self.format = fmt


if __name__ == '__main__':
    pass
