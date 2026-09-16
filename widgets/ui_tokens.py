"""Shared visual defaults. User font/zoom preferences override layout defaults.

Keep these in Qt logical pixels (Qt handles display scaling). Add semantic values
here only when controls share a visual purpose, not merely the same number.
"""

TOOLBAR_ICON_SIZE = 20
ASSET_COMBO_ICON_SIZE = 30
COMPACT_MARGIN = 3
TOOLBAR_SPACING = 3
SEARCH_SPACING = 5
PANEL_SPACING = 1
TAG_TEXT_COLOR = "#bfff00"

# Column identity belongs to each model; widths are presentation policy.
ASSET_TABLE_COLUMN_WIDTHS = ((0, 250), (1, 130), (2, 10), (3, 60), (4, 50))
HISTORY_TABLE_COLUMN_WIDTHS = ((0, 80), (1, 255), (2, 185), (5, 80), (7, 150))
