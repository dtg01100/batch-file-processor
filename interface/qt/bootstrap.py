"""Bootstrap and startup helpers for the Qt application."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional

from core.structured_logging import (
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    log_with_context,
    set_correlation_id,
)
from dispatch.feature_flags import get_strict_testing_mode
from interface.qt.theme import Theme

logger = get_logger(__name__)


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
            log_with_context(
                logger,
                20,  # INFO
                "Qt platform: Forcing XCB (X11) due to Wayland/X11 coexistence",
                correlation_id=get_correlation_id(),
                component="qt_bootstrap",
                operation="configure_qt_platform",
                context={
                    "wayland_display": wayland_display,
                    "x11_display": x11_display,
                },
            )

    def parse_arguments(self, args: Optional[list[str]] = None) -> argparse.Namespace:
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
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
        log_with_context(
            logger,
            10,  # DEBUG
            "Parsed command line arguments",
            correlation_id=correlation_id,
            component="qt_bootstrap",
            operation="parse_arguments",
            context={
                "automatic": parsed_args.automatic,
                "self_test": parsed_args.self_test,
                "gui_test": parsed_args.gui_test,
                "graphical_automatic": getattr(
                    parsed_args, "graphical_automatic", False
                ),
            },
        )
        return parsed_args

    def setup_config_directories(self) -> tuple[str, str]:
        config_folder = self._app._appdirs_module.user_data_dir(self._app._appname)
        database_path = os.path.join(config_folder, "folders.db")
        try:
            os.makedirs(config_folder, exist_ok=True)
        except (FileExistsError, NotADirectoryError, OSError) as error:
            if get_strict_testing_mode():
                raise RuntimeError(
                    f"Failed to create config directory '{config_folder}'"
                ) from error
        log_with_context(
            logger,
            10,  # DEBUG
            "Config directories setup complete",
            correlation_id=get_correlation_id(),
            component="qt_bootstrap",
            operation="setup_config_directories",
            context={
                "config_folder": config_folder,
                "database_path": database_path,
            },
        )
        return config_folder, database_path

    def build_ui_runtime(self) -> None:
        log_with_context(
            logger,
            10,  # DEBUG
            "Building Qt UI runtime",
            correlation_id=get_correlation_id(),
            component="qt_bootstrap",
            operation="build_ui_runtime",
        )
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
