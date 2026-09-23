"""Shared visual defaults. User font/zoom preferences override layout defaults.

Keep these in Qt logical pixels (Qt handles display scaling). Add semantic values
here only when controls share a visual purpose, not merely the same number.
"""

from libs.model_columns import AssetColumn, HistoryColumn, InsideColumn, RecordColumn

TOOLBAR_ICON_SIZE = 20
ASSET_COMBO_ICON_SIZE = 30
COMPACT_MARGIN = 3
TOOLBAR_SPACING = 3
SEARCH_SPACING = 5
PANEL_SPACING = 1
# Item delegates (widgets/item_delegates.py)
CARD_RADIUS = 6
CARD_PADDING = 4
BADGE_HEIGHT = 16
STAR_SIZE = 16
FAVORITE_COLOR = "#FF2400"  # a filled star must read at a glance in both themes
VERSION_COLOR = "#3B82F6"  # version pills: grey on grey was unreadable in Houdini

# Column identity belongs to each model; widths are presentation policy.
ASSET_TABLE_COLUMN_WIDTHS = (
    (AssetColumn.NAME, 250),
    (AssetColumn.DEFINITION, 130),
    (AssetColumn.FAVORITE, 40),
    (AssetColumn.VERSION, 76),
    (AssetColumn.USE_COUNT, 64),
)
HISTORY_TABLE_COLUMN_WIDTHS = (
    (HistoryColumn.ID, 80),
    (HistoryColumn.NAME, 255),
    (HistoryColumn.DEFINITION, 185),
    (HistoryColumn.VERSION, 80),
    (HistoryColumn.TYPE, 150),
)
INSIDE_TREE_COLUMN_WIDTHS = (
    (InsideColumn.NAME, 350),
    (InsideColumn.TYPE, 100),
    (InsideColumn.CATEGORY, 120),
    (InsideColumn.VERSION, 50),
)
RECORD_TREE_COLUMN_WIDTHS = (
    (RecordColumn.NAME, 350),
    (RecordColumn.TYPE, 100),
    (RecordColumn.CATEGORY, 100),
    (RecordColumn.VERSION, 50),
    (RecordColumn.HOUDINI, 100),
    (RecordColumn.LICENSE, 100),
    (RecordColumn.OS, 100),
    (RecordColumn.START_FRAME, 100),
    (RecordColumn.END_FRAME, 100),
    (RecordColumn.FPS, 50),
)
