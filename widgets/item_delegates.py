"""How items look: cards in the asset grid, rows in the tables, badges in trees.

Delegates read roles the models already provide and draw; they never touch
files or the repository (the same rule tests hold data() to). Colours come from
``option.palette`` so both themes (Houdini host, dark blue) stay consistent, and
the theme's own hover/selection background is drawn first through the style.
"""

from __future__ import annotations

import math
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from widgets.ui_tokens import BADGE_HEIGHT, CARD_PADDING, CARD_RADIUS, STAR_SIZE

UNAVAILABLE_OPACITY = 0.55


# --- shared drawing -----------------------------------------------------------


def theme_background(
    painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem
) -> None:
    """The style's item background (hover, selection, alternate) without content.

    QSS ``::item`` rules only reach a delegate through the style, so every
    delegate starts here and paints its own content on top.
    """
    opt = QtWidgets.QStyleOptionViewItem(option)
    opt.text = ""
    opt.icon = QtGui.QIcon()
    opt.decorationSize = QtCore.QSize(0, 0)
    widget = opt.widget
    style = widget.style() if widget is not None else QtWidgets.QApplication.style()
    style.drawControl(
        QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget
    )


def star_rect(rect: QtCore.QRect, size: int = STAR_SIZE) -> QtCore.QRect:
    """Top-right corner of ``rect``; the click target of the favorite toggle."""
    return QtCore.QRect(
        rect.right() - size - CARD_PADDING, rect.top() + CARD_PADDING, size, size
    )


def star_path(rect: QtCore.QRect) -> QtGui.QPainterPath:
    center = QtCore.QPointF(rect.center()) + QtCore.QPointF(0.5, 0.5)
    outer, inner = rect.width() / 2.0, rect.width() / 4.6
    path = QtGui.QPainterPath()
    for i in range(10):
        radius = outer if i % 2 == 0 else inner
        angle = -math.pi / 2 + i * math.pi / 5
        point = QtCore.QPointF(
            center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle)
        )
        if i == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


def draw_star(
    painter: QtGui.QPainter,
    rect: QtCore.QRect,
    palette: QtGui.QPalette,
    *,
    filled: bool,
) -> None:
    painter.save()
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    path = star_path(rect)
    if filled:
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(palette.highlight())
    else:
        painter.setPen(QtGui.QPen(palette.mid().color(), 1.2))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.restore()


def draw_pill(
    painter: QtGui.QPainter,
    top_left: QtCore.QPoint,
    text: str,
    palette: QtGui.QPalette,
    font: QtGui.QFont,
) -> QtCore.QRect:
    """A small rounded label (version, count); returns the rect it used."""
    metrics = QtGui.QFontMetrics(font)
    width = metrics.horizontalAdvance(text) + BADGE_HEIGHT // 2 + 6
    rect = QtCore.QRect(top_left, QtCore.QSize(width, BADGE_HEIGHT))
    painter.save()
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    background = QtGui.QColor(palette.mid().color())
    background.setAlpha(200)
    painter.setBrush(background)
    painter.drawRoundedRect(rect, BADGE_HEIGHT / 2, BADGE_HEIGHT / 2)
    painter.setPen(palette.text().color())
    painter.setFont(font)
    painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()
    return rect


def draw_rounded_pixmap(
    painter: QtGui.QPainter, area: QtCore.QRect, pixmap: QtGui.QPixmap, radius: int
) -> None:
    """``pixmap`` centred in ``area`` behind rounded corners; never upscaled."""
    size = pixmap.size().boundedTo(area.size())
    target = QtCore.QRect(QtCore.QPoint(0, 0), size)
    target.moveCenter(area.center())
    painter.save()
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
    clip = QtGui.QPainterPath()
    clip.addRoundedRect(QtCore.QRectF(target), radius, radius)
    painter.setClipPath(clip)
    painter.drawPixmap(target, pixmap)
    painter.restore()


def small_font(font: QtGui.QFont) -> QtGui.QFont:
    small = QtGui.QFont(font)
    small.setItalic(False)
    small.setStrikeOut(False)
    if small.pointSize() > 0:
        small.setPointSize(max(6, small.pointSize() - 2))
    return small


def is_available(data: Any) -> bool:
    """Missing local files dim an item; remote rows have no files to miss."""
    if data is None:
        return True
    return bool(getattr(data, "available", True) or getattr(data, "remote", False))


# --- the asset grid -----------------------------------------------------------


class CardDelegate(QtWidgets.QStyledItemDelegate):
    """One asset as a card: rounded thumbnail, name, version pill, favorite star."""

    favoriteToggled = QtCore.Signal(QtCore.QModelIndex)

    def __init__(
        self,
        parent: QtCore.QObject | None,
        *,
        data_role: int,
        favorite_role: int,
        version_role: int,
    ) -> None:
        super().__init__(parent)
        self._data_role = data_role
        self._favorite_role = favorite_role
        self._version_role = version_role

    def paint(  # type: ignore[override]
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        theme_background(painter, opt)
        palette = opt.palette
        selected = bool(opt.state & QtWidgets.QStyle.StateFlag.State_Selected)
        hovered = bool(opt.state & QtWidgets.QStyle.StateFlag.State_MouseOver)
        rect = opt.rect.adjusted(
            CARD_PADDING, CARD_PADDING, -CARD_PADDING, -CARD_PADDING
        )
        font = QtGui.QFont(opt.font)
        font.setStrikeOut(False)
        metrics = QtGui.QFontMetrics(font)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if selected:
            painter.setPen(QtGui.QPen(palette.highlight().color(), 1.5))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                QtCore.QRectF(opt.rect).adjusted(1, 1, -1, -1), CARD_RADIUS, CARD_RADIUS
            )
        if not is_available(index.data(self._data_role)):
            painter.setOpacity(UNAVAILABLE_OPACITY)
        text_height = metrics.height()
        thumb_area = QtCore.QRect(
            rect.left(),
            rect.top(),
            rect.width(),
            max(0, rect.height() - text_height - CARD_PADDING),
        )
        pixmap = index.data(QtCore.Qt.ItemDataRole.DecorationRole)
        if isinstance(pixmap, QtGui.QPixmap) and not pixmap.isNull():
            draw_rounded_pixmap(painter, thumb_area, pixmap, CARD_RADIUS)
        name = str(index.data(QtCore.Qt.ItemDataRole.DisplayRole) or "")
        painter.setFont(font)
        painter.setPen(palette.text().color())
        painter.drawText(
            QtCore.QRect(
                rect.left(), rect.bottom() - text_height, rect.width(), text_height
            ),
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
            metrics.elidedText(name, QtCore.Qt.TextElideMode.ElideMiddle, rect.width()),
        )
        version = index.data(self._version_role)
        if version:
            draw_pill(
                painter,
                QtCore.QPoint(rect.left(), rect.top()),
                f"v{version}",
                palette,
                small_font(font),
            )
        favorite = bool(index.data(self._favorite_role))
        if favorite or hovered:
            draw_star(painter, star_rect(opt.rect), palette, filled=favorite)
        painter.restore()

    def editorEvent(  # type: ignore[override]
        self,
        event: QtCore.QEvent,
        model: QtCore.QAbstractItemModel,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> bool:
        if (
            event.type() == QtCore.QEvent.Type.MouseButtonRelease
            and isinstance(event, QtGui.QMouseEvent)
            and event.button() == QtCore.Qt.MouseButton.LeftButton
            and star_rect(option.rect).contains(event.position().toPoint())
        ):
            self.favoriteToggled.emit(
                index
                if isinstance(index, QtCore.QModelIndex)
                else model.index(index.row(), index.column(), index.parent())
            )
            return True
        return super().editorEvent(event, model, option, index)


# --- the asset and history tables -----------------------------------------------


class RowDelegate(QtWidgets.QStyledItemDelegate):
    """Table rows: thumbnail + two-line name cell, version pill, clickable star.

    Activity rows of the history table (renames, video changes: ``is_version``
    False) get a timeline dot and dim italic text instead of a thumbnail.
    """

    favoriteToggled = QtCore.Signal(QtCore.QModelIndex)

    def __init__(
        self,
        parent: QtCore.QObject | None,
        *,
        data_role: int,
        name_column: int,
        secondary_column: int,
        version_column: int | None = None,
        favorite_column: int | None = None,
        favorite_role: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._data_role = data_role
        self._name_column = name_column
        self._secondary_column = secondary_column
        self._version_column = version_column
        self._favorite_column = favorite_column
        self._favorite_role = favorite_role

    @staticmethod
    def _is_version(data: Any) -> bool:
        return bool(getattr(data, "is_version", True))

    def paint(  # type: ignore[override]
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        column = index.column()
        if column not in (
            self._name_column,
            self._version_column,
            self._favorite_column,
        ):
            super().paint(painter, option, index)
            return
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        theme_background(painter, opt)
        palette = opt.palette
        data = index.data(self._data_role)
        font = QtGui.QFont(opt.font)
        font.setStrikeOut(False)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if not is_available(data):
            painter.setOpacity(UNAVAILABLE_OPACITY)
        if column == self._favorite_column:
            favorite = self._favorite_role is not None and bool(
                index.data(self._favorite_role)
            )
            rect = QtCore.QRect(0, 0, STAR_SIZE, STAR_SIZE)
            rect.moveCenter(opt.rect.center())
            hovered = bool(opt.state & QtWidgets.QStyle.StateFlag.State_MouseOver)
            if favorite or hovered:
                draw_star(painter, rect, palette, filled=favorite)
        elif column == self._version_column:
            text = str(index.data(QtCore.Qt.ItemDataRole.DisplayRole) or "")
            if text:
                pill_font = small_font(font)
                width = QtGui.QFontMetrics(pill_font).horizontalAdvance(text) + 14
                top_left = QtCore.QPoint(
                    opt.rect.center().x() - width // 2,
                    opt.rect.center().y() - BADGE_HEIGHT // 2,
                )
                draw_pill(painter, top_left, text, palette, pill_font)
        else:
            self._paint_name(painter, opt, index, data, font)
        painter.restore()

    def _paint_name(
        self,
        painter: QtGui.QPainter,
        opt: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        data: Any,
        font: QtGui.QFont,
    ) -> None:
        palette = opt.palette
        rect = opt.rect.adjusted(CARD_PADDING, 0, -CARD_PADDING, 0)
        name = str(index.data(QtCore.Qt.ItemDataRole.DisplayRole) or "")
        if not self._is_version(data):
            # Activity row: a timeline dot and the event text, quieter than a version.
            dot = QtCore.QRectF(rect.left() + 2, rect.center().y() - 3, 7, 7)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(palette.mid())
            painter.drawEllipse(dot)
            font.setItalic(True)
            painter.setFont(font)
            painter.setPen(palette.placeholderText().color())
            painter.drawText(
                rect.adjusted(14, 0, 0, 0),
                QtCore.Qt.AlignmentFlag.AlignLeft
                | QtCore.Qt.AlignmentFlag.AlignVCenter,
                QtGui.QFontMetrics(font).elidedText(
                    name, QtCore.Qt.TextElideMode.ElideRight, rect.width() - 14
                ),
            )
            return
        pixmap = index.data(QtCore.Qt.ItemDataRole.DecorationRole)
        text_left = rect.left()
        if isinstance(pixmap, QtGui.QPixmap) and not pixmap.isNull():
            edge = min(rect.height() - 2, pixmap.height(), pixmap.width())
            area = QtCore.QRect(rect.left(), rect.top() + 1, edge, rect.height() - 2)
            draw_rounded_pixmap(painter, area, pixmap, CARD_RADIUS // 2)
            text_left = area.right() + CARD_PADDING * 2
        text_rect = QtCore.QRect(
            text_left, rect.top(), rect.right() - text_left, rect.height()
        )
        secondary = ""
        model = index.model()
        if self._secondary_column != index.column() and model is not None:
            sibling = model.index(index.row(), self._secondary_column, index.parent())
            secondary = str(sibling.data(QtCore.Qt.ItemDataRole.DisplayRole) or "")
        metrics = QtGui.QFontMetrics(font)
        detail_font = small_font(font)
        detail_metrics = QtGui.QFontMetrics(detail_font)
        two_lines = bool(secondary) and (
            metrics.height() + detail_metrics.height() <= text_rect.height()
        )
        if two_lines:
            top = (
                text_rect.top()
                + (text_rect.height() - metrics.height() - detail_metrics.height()) // 2
            )
            name_rect = QtCore.QRect(
                text_rect.left(), top, text_rect.width(), metrics.height()
            )
            detail_rect = QtCore.QRect(
                text_rect.left(),
                top + metrics.height(),
                text_rect.width(),
                detail_metrics.height(),
            )
        else:
            name_rect, detail_rect = text_rect, QtCore.QRect()
        painter.setFont(font)
        painter.setPen(palette.text().color())
        painter.drawText(
            name_rect,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            metrics.elidedText(
                name, QtCore.Qt.TextElideMode.ElideMiddle, name_rect.width()
            ),
        )
        if two_lines:
            painter.setFont(detail_font)
            painter.setPen(palette.placeholderText().color())
            painter.drawText(
                detail_rect,
                QtCore.Qt.AlignmentFlag.AlignLeft
                | QtCore.Qt.AlignmentFlag.AlignVCenter,
                detail_metrics.elidedText(
                    secondary, QtCore.Qt.TextElideMode.ElideRight, detail_rect.width()
                ),
            )

    def editorEvent(  # type: ignore[override]
        self,
        event: QtCore.QEvent,
        model: QtCore.QAbstractItemModel,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> bool:
        if (
            self._favorite_column is not None
            and index.column() == self._favorite_column
            and event.type() == QtCore.QEvent.Type.MouseButtonRelease
            and isinstance(event, QtGui.QMouseEvent)
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            self.favoriteToggled.emit(
                index
                if isinstance(index, QtCore.QModelIndex)
                else model.index(index.row(), index.column(), index.parent())
            )
            return True
        return super().editorEvent(event, model, option, index)


def two_line_row_height(font: QtGui.QFont) -> int:
    """The row height a two-line name cell needs; tables take the max with the icon."""
    metrics = QtGui.QFontMetrics(font)
    return metrics.height() + QtGui.QFontMetrics(small_font(font)).height() + 6
