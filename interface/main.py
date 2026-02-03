"""
Main entry point for the PyQt6-based Batch File Processor application.

This module handles:
- Command-line argument parsing
- PyQt6 application creation
- Database path setup using appdirs
- Main window creation and display
"""

import argparse
import multiprocessing
import os
import platform
import sys
from pathlib import Path
from typing import Optional, cast

# Add project root to sys.path so we can import interface modules
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import appdirs

from interface.ui.app import Application, create_application
from interface.ui.main_window import create_main_window


# Application constants
APPNAME = "Batch File Sender"
VERSION = "1.0.0"
DATABASE_VERSION = "41"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--automatic",
        action="store_true",
        help="Run in automatic mode without GUI",
    )
    return parser.parse_args()


def get_database_path() -> tuple[str, str]:
    """Get the database path using appdirs.

    Returns:
        Tuple of (config_folder, database_path).
    """
    config_folder = appdirs.user_data_dir(APPNAME)
    database_path = os.path.join(config_folder, "folders.db")
    return config_folder, database_path


def ensure_config_directory(config_folder: str) -> None:
    """Ensure the configuration directory exists.

    Args:
        config_folder: Path to the configuration directory.
    """
    try:
        os.makedirs(config_folder)
    except FileExistsError:
        pass


def setup_database(db_manager) -> None:
    """Setup the database manager reference in the application.

    Args:
        db_manager: Database manager instance.
    """
    from interface.ui.app import Application

    instance = Application.instance()
    if instance is not None and isinstance(instance, Application):
        # Cast required because QApplication.instance() returns QCoreApplication | None
        # and isinstance check doesn't narrow to our Application subclass properly
        app = cast(Application, instance)
        app.database_manager = db_manager


def run_automatic_mode(db_manager, args, version: str) -> int:
    """Run the application in automatic (non-GUI) mode.

    Args:
        db_manager: Database manager instance.
        args: Parsed command-line arguments.
        version: Application version string.

    Returns:
        Exit code (0 for success).
    """
    from interface.operations.processing import automatic_process_directories

    automatic_process_directories(db_manager, args, version)
    return 0


def run_gui_mode(
    config_folder: str,
    database_path: str,
    args: argparse.Namespace,
    version: str,
    running_platform: str,
) -> None:
    """Run the application in GUI mode.

    Args:
        config_folder: Configuration directory path.
        database_path: Path to the database file.
        args: Parsed command-line arguments.
        version: Application version string.
        running_platform: Current operating system platform.
    """
    # Create and configure application FIRST
    # QSqlDatabase requires QCoreApplication to exist
    app = create_application(sys.argv)

    # Import database manager here to avoid circular imports
    from interface.database.database_manager import DatabaseManager

    # Initialize database AFTER QApplication exists
    db_manager = DatabaseManager(
        database_path=database_path,
        config_folder=config_folder,
        platform=running_platform,
        app_version=version,
        database_version=DATABASE_VERSION,
    )

    # Set database manager
    setup_database(db_manager)

    # Create and show main window
    main_window = create_main_window(db_manager=db_manager, app=app)
    main_window.setWindowTitle(f"Batch File Processor {version}")

    # Wire up application controller
    from interface.application_controller import ApplicationController

    controller = ApplicationController(
        main_window=main_window,
        db_manager=db_manager,
        app=app,
        database_path=database_path,
        args=args,
        version=version,
    )

    main_window.show()

    # Run application event loop
    exit_code = app.exec()

    # Cleanup
    db_manager.close()

    sys.exit(exit_code)


def main() -> Optional[int]:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, None for normal exit).
    """
    multiprocessing.freeze_support()

    print(f"{APPNAME} Version {VERSION}")
    running_platform = platform.system()
    print(f"Running on {running_platform}")

    args = parse_arguments()

    config_folder, database_path = get_database_path()
    ensure_config_directory(config_folder)

    if args.automatic:
        # Automatic mode: no Qt GUI, create DatabaseManager directly
        from interface.database.database_manager import DatabaseManager

        db_manager = DatabaseManager(
            database_path=database_path,
            config_folder=config_folder,
            platform=running_platform,
            app_version=VERSION,
            database_version=DATABASE_VERSION,
        )
        exit_code = run_automatic_mode(db_manager, args, VERSION)
        return exit_code

    # GUI mode: QApplication must exist before DatabaseManager (QSqlDatabase requirement)
    run_gui_mode(config_folder, database_path, args, VERSION, running_platform)

    return None


if __name__ == "__main__":
    exit_code = main()
    if exit_code is not None:
        sys.exit(exit_code)
