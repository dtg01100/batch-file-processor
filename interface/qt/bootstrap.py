"""Bootstrap and startup helpers for the Qt application."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Optional

from interface.qt.theme import Theme

logger = logging.getLogger(__name__)


class QtAppBootstrapService:
    """Encapsulates startup concerns for ``QtBatchFileSenderApp``."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def configure_qt_platform(self) -> None:
        """Configure Qt platform plugin to avoid Wayland issues."""
        if sys.platform == "win32":
            return

        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        x11_display = os.environ.get("DISPLAY")
        qpa_platform = os.environ.get("QT_QPA_PLATFORM")

        if wayland_display and x11_display and not qpa_platform:
            os.environ["QT_QPA_PLATFORM"] = "xcb"
            logger.info("Qt platform: Forcing XCB (X11) due to Wayland/X11 coexistence")

    def parse_arguments(self, args: Optional[list[str]] = None) -> argparse.Namespace:
        launch_options = argparse.ArgumentParser()
        launch_options.add_argument("-a", "--automatic", action="store_true")
        launch_options.add_argument(
            "-s", "--self-test", action="store_true", help="Run self-test and exit"
        )
        launch_options.add_argument(
            "-g",
            "--gui-test",
            action="store_true",
            help="Run GUI self-test (opens and closes main window)",
        )
        launch_options.add_argument(
            "--graphical-automatic",
            action="store_true",
            help="Show GUI and automatically start processing all folders",
        )
        parsed_args, _unknown = launch_options.parse_known_args(args)
        logger.debug(
            "Parsed args: automatic=%s, self_test=%s, gui_test=%s",
            parsed_args.automatic,
            parsed_args.self_test,
            parsed_args.gui_test,
        )
        return parsed_args

    def setup_config_directories(self) -> tuple[str, str]:
        config_folder = self._app._appdirs_module.user_data_dir(self._app._appname)
        database_path = os.path.join(config_folder, "folders.db")
        try:
            os.makedirs(config_folder, exist_ok=True)
        except (FileExistsError, NotADirectoryError, OSError):
            pass
        logger.debug("Config directory: %s", config_folder)
        return config_folder, database_path

    def build_ui_runtime(self) -> None:
        logger.debug("Building Qt UI runtime")
        qapplication_cls = self._app._get_qapplication_cls()
        qmainwindow_cls = self._app._get_qmainwindow_cls()
        self._app._app = qapplication_cls.instance() or qapplication_cls(
            self._app._sys_module.argv
        )
        self._app._app.setStyleSheet(Theme.get_stylesheet())
        self._app._window = qmainwindow_cls()
        self._app._window.setWindowTitle(f"{self._app._appname} {self._app._version}")

        if self._app._ui_service is None:
            from interface.qt.services.qt_services import QtUIService

            self._app._ui_service = QtUIService(self._app._window)

        if self._app._progress_service is None:
            from interface.qt.services.qt_services import QtProgressService

            self._app._progress_service = QtProgressService(self._app._window)
