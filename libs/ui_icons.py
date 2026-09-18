"""Icons more than one screen uses; single-use icons stay literal at their site.

A path here changes in one place. Values are Qt resource paths, so they work
wherever a str path does (QPixmap, QIcon).
"""

from __future__ import annotations

from enum import StrEnum


class Icon(StrEnum):
    CASE_SENSITIVE = ":/main/icons/case_sensitive.png"
    CLEAR = ":/main/icons/clear.png"
    HIPFILE = ":/main/icons/hipfile.png"
    HOUDINI_LOGO_WHITE = ":/main/icons/houdini_logo_white.png"
    IC_ARCHIVE_WHITE = ":/main/icons/ic_archive_white.png"
    IC_BOOKMARK_WHITE = ":/main/icons/ic_bookmark_white.png"
    IC_BORDER_COLOR_WHITE = ":/main/icons/ic_border_color_white.png"
    IC_BUILD_WHITE = ":/main/icons/ic_build_white.png"
    IC_CAMERA_ALT_WHITE = ":/main/icons/ic_camera_alt_white.png"
    IC_CLEAR_WHITE = ":/main/icons/ic_clear_white.png"
    IC_DELETE_FOREVER_WHITE = ":/main/icons/ic_delete_forever_white.png"
    IC_DONE_WHITE = ":/main/icons/ic_done_white.png"
    IC_FIND_IN_PAGE_WHITE = ":/main/icons/ic_find_in_page_white.png"
    IC_FOLDER_WHITE = ":/main/icons/ic_folder_white.png"
    IC_FORMAT_QUOTE_WHITE = ":/main/icons/ic_format_quote_white.png"
    IC_MOVIE_WHITE = ":/main/icons/ic_movie_white.png"
    IC_QUERY_BUILDER_WHITE = ":/main/icons/ic_query_builder_white.png"
    IC_REFRESH_WHITE = ":/main/icons/ic_refresh_white.png"
    IC_RESTORE_PAGE_WHITE = ":/main/icons/ic_restore_page_white.png"
    IC_SAVE_WHITE = ":/main/icons/ic_save_white.png"
    IC_SWAP_HORIZ_WHITE = ":/main/icons/ic_swap_horiz_white.png"
    IC_VIDEOCAM_WHITE = ":/main/icons/ic_videocam_white.png"
    NETWORK_INTELLIGENCE = ":/main/icons/network_intelligence.png"
    NO_IMG_AVAILABLE = ":/main/icons/no_img_available.png"
    SHOW_ALL = ":/main/icons/show_all.png"
    UPLOAD = ":/main/icons/upload.png"
    VIEWPORT_LOGO_TRANS = ":/main/icons/viewport_logo_trans.png"
    VIDEO_IC_DELETE_FOREVER_WHITE = (
        ":/video_player_main/icons/ic_delete_forever_white.png"
    )
    VIDEO_IC_STOP_WHITE = ":/video_player_main/icons/ic_stop_white.png"
