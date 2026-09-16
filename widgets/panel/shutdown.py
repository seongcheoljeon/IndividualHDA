"""Main-window close policy and host cleanup, separate from Qt event routing."""

from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtWidgets

from libs import houdini_api, ihda_system, log_handler
from libs.host import IS_HOUDINI
from libs.paths import Paths
from widgets.panel.lifetime import PanelLifetime


def detach_host_callbacks(window: Any) -> None:
    if IS_HOUDINI:
        window._remove_event_loop_callback(window._wrapper_current_panetab)
        window._remove_event_loop_callback(window._loading_counter)
        window._remove_selection_callback(
            window._wrapper_selection_callback_item_by_ihda
        )


class PanelShutdown:
    def __init__(self, window: Any, lifetime: PanelLifetime) -> None:
        self.window = window
        self._lifetime = lifetime
        self._prepared = False
        self._closed = False
        self._in_progress = False

    def _prepare(self) -> None:
        window = self.window
        window._closing = True
        window._library_sync_presenter.close()
        window._ai_target_id = -1
        self._lifetime.add(
            "history_debounce", lambda: window._history_search_debounce.timer.stop(), 0
        )
        # These dialogs are created lazily after construction.
        for attribute in ("_copy_dialog", "_metadata_dialog", "_library_manager"):
            dialog = getattr(window, attribute, None)
            if dialog is not None:
                self._lifetime.add(attribute, dialog.shutdown, 5)
                # Copy and manager shutdown already close their dialogs, whose
                # finished handlers may delete them during another worker drain.
                if attribute == "_metadata_dialog":
                    self._lifetime.add("metadata_hide", dialog.reject, 6)
        self._prepared = True

    def close(self) -> bool:
        if self._closed:
            return True
        if self._in_progress:
            return False
        self._in_progress = True
        try:
            if not self._prepared:
                self._prepare()
            errors = self._lifetime.close()
            if errors:
                raise RuntimeError(
                    "; ".join(f"{name}: {error}" for name, error in errors)
                )
            window = self.window
            # If activation fails after draining, keep the window in closing state.
            # A subsequent close retries activation without reusing stopped services.
            window._archives.commit_import()
            self._save_settings()
            if IS_HOUDINI:
                window._loading_close()
                window._dragdrop_overlay_close()
                if window._hda_base_dirpath is not None:
                    houdini_api.HoudiniAPI.clean_hda_library(window._hda_base_dirpath)
                else:
                    directory = window._preference.get_data_dirpath_from_saved()
                    if directory is not None:
                        houdini_api.HoudiniAPI.clean_hda_library(directory)
                if not window._embedded:
                    window.setParent(None)
            self._closed = True
            return True
        except Exception as error:
            logging.error("Panel close could not finish: %s", error)
            self.window.centralwidget.setEnabled(False)
            self.window.toolBar.setEnabled(False)
            self.window.menubar.setEnabled(False)
            QtWidgets.QMessageBox.critical(
                self.window,
                "Individual HDA",
                f"Could not finish closing: {error}\nClose this panel again to retry. Stopped services will not be restarted.",
            )
            return False
        finally:
            self._in_progress = False

    def _save_settings(self) -> None:
        window = self.window
        if window._is_reset_app_properties:
            if Paths.config_dirpath.exists():
                log_handler.uninstall_file_logging()
                ihda_system.IHDASystem.remove_dir(dirpath=Paths.config_dirpath)
        else:
            window._ui_settings.save_main_window_geometry()
            window._ui_settings.save_splitter_status()
            window._ui_settings.save_cfg_dict_to_file()
