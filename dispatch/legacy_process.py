"""Legacy backward-compatible dispatch process entry point.

Extracted from DispatchOrchestrator.process() to reduce orchestrator size
and separate the legacy API from the modern instance-based API.

Usage:
    from dispatch.legacy_process import process
    has_errors, summary = process(db, folders_db, run_log, ...)
"""

from typing import Any

from core.structured_logging import get_logger

logger = get_logger(__name__)


def process(
    database_connection: Any,
    folders_database: Any,
    run_log: Any,
    emails_table: Any,
    run_log_directory: str,
    reporting: Any,
    processed_files: Any,
    version: str,
    errors_folder: str,
    settings: dict,
    progress_callback: Any = None,
) -> tuple[bool, str]:
    """Legacy dispatch processing entry point.

    Provides a drop-in replacement for the legacy dispatch.process() function.
    Creates a DispatchOrchestrator and processes all active folders.

    Args:
        database_connection: Database connection (not used directly,
            kept for compatibility)
        folders_database: Folders database interface
        run_log: Run log for recording processing activity
        emails_table: Emails table for storing log references
        run_log_directory: Directory for storing run logs
        reporting: Reporting configuration
        processed_files: Processed files database
        version: Application version string
        errors_folder: Directory for storing error logs
        settings: Global application settings
        progress_callback: Optional progress callback for UI updates

    Returns:
        Tuple of (has_errors: bool, summary: str)

    """
    orchestrator, folders = _prepare_processing(
        folders_database, settings, version, progress_callback
    )

    logger.debug("Starting dispatch process for %d active folders", len(folders))

    has_errors = _iterate_folders(orchestrator, folders, run_log, processed_files)

    summary = orchestrator.get_summary()
    logger.info("Dispatch complete: %s", summary)
    return has_errors, summary


def _prepare_processing(
    folders_database: Any, settings: dict, version: str, progress_callback: Any
) -> tuple[Any, list]:
    """Prepare the DispatchOrchestrator and return (orchestrator, folders)."""
    from dispatch.orchestrator import DispatchOrchestrator
    from dispatch.pipeline.converter import EDIConverterStep
    from dispatch.pipeline.splitter import EDISplitterStep
    from dispatch.pipeline.validator import EDIValidationStep
    from dispatch.results import DispatchConfig

    config = DispatchConfig(
        database=folders_database,
        settings=settings,
        version=version,
        progress_reporter=progress_callback,
        validator_step=EDIValidationStep(),
        splitter_step=EDISplitterStep(),
        converter_step=EDIConverterStep(),
    )

    orchestrator = DispatchOrchestrator(config)
    folders = list(folders_database.find(folder_is_active=True, order_by="alias"))
    return orchestrator, folders


def _iterate_folders(
    orchestrator: Any, folders: list, run_log: Any, processed_files: Any
) -> bool:
    """Iterate over folders and run processing, returning whether any errors occurred.

    Uses single-pass discovery and processing: files are discovered and
    processed immediately for each folder, eliminating the pre-discovery phase.
    """
    has_errors = False
    for folder_index, folder in enumerate(folders, start=1):
        try:
            result = orchestrator.discover_and_process_folder(
                folder,
                run_log,
                processed_files,
                folder_num=folder_index,
                folder_total=len(folders),
            )
            if not result.success:
                has_errors = True
        except Exception as folder_error:
            has_errors = True
            if hasattr(run_log, "write"):
                try:
                    run_log.write(
                        (
                            f"ERROR processing folder"
                            f" {folder.get('alias', 'unknown')}:"
                            f" {folder_error}\r\n"
                        ).encode()
                    )
                except Exception:
                    logger.exception("Failed to write folder error to run_log")
    return has_errors
