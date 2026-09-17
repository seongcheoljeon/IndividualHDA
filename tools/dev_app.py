"""Run the real Qt panel with isolated sample data, without Houdini."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke", action="store_true", help="open, verify sample data, then close"
    )
    args = parser.parse_args()
    with TemporaryDirectory(prefix="ihda-developer-") as directory:
        root = Path(directory)
        # Set locations before any application module computes its paths.
        os.environ["IHDA_CONFIG_DIR"] = str(root / "settings")
        os.environ["IHDA_USER"] = "developer"
        if args.smoke:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtCore, QtWidgets

        from libs.keys import Name
        from libs.paths import Paths
        from libs.settings_store import save_json
        from main import IndividualHDA
        from tools.sample_library import create_sample_library
        from widgets.panel.services import PanelServices

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(
            sys.argv[:1]
        )
        assert isinstance(application, QtWidgets.QApplication)
        application.setQuitOnLastWindowClosed(False)
        database = create_sample_library(root / "library")
        save_json(
            Paths.json_pref_filepath,
            {Name.PreferenceUI.lineedit_data_dirpath: str(database.parent)},
        )
        window = IndividualHDA(
            services=PanelServices(help_site="about:blank", host_actions_enabled=False)
        )
        window.setWindowTitle("Individual HDA — Development samples")
        window.show()
        result = 0

        def finish() -> None:
            nonlocal result
            try:
                if len(window.models.assets.rows) != 3:
                    raise RuntimeError("The sample library did not load")
                if not window.close():
                    QtCore.QTimer.singleShot(50, finish)
                    return
            except Exception as error:
                print(str(error), file=sys.stderr)
                result = 1
            application.quit()

        if args.smoke:
            QtCore.QTimer.singleShot(500, finish)
        else:
            application.setQuitOnLastWindowClosed(True)
        application.exec()
        window.deleteLater()
        application.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        from libs.log_handler import uninstall_file_logging

        uninstall_file_logging()
        return result


if __name__ == "__main__":
    raise SystemExit(main())
