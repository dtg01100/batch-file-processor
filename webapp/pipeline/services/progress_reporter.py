import logging
import sys
from typing import Protocol, TextIO


class ProgressReporter(Protocol):
    def update(
        self,
        message: str,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str,
    ) -> None: ...

    def update_discovery_file(
        self,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        filename: str,
    ) -> None: ...


# ``UIProgressReporter`` was removed in Phase 9.2 (2026-09-02). It
# existed to forward ``update()`` calls to a Qt overlay widget that
# no longer exists; its ``update_overlay`` method body was already
# ``pass`` (a no-op). CLI/Null/Logging reporters below remain.


class CLIProgressReporter:
    def __init__(self, output: TextIO | None = None) -> None:
        self._output = output or sys.stdout

    def update(
        self,
        message: str,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str,
    ) -> None:
        progress_line = (
            f"{message} | "
            f"Folder {folder_num} of {folder_total}, "
            f"File {file_num} of {file_total}"
        )
        if footer:
            progress_line += f" | {footer}"

        self._output.write("\r" + progress_line)
        self._output.flush()

    def update_discovery_file(
        self,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        filename: str,
    ) -> None:
        pass


class NullProgressReporter:
    def update(
        self,
        message: str,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str,
    ) -> None:
        pass

    def update_discovery_file(
        self,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        filename: str,
    ) -> None:
        pass


class LoggingProgressReporter:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def update(
        self,
        message: str,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str,
    ) -> None:
        log_message = (
            f"{message} | Folder {folder_num}/{folder_total}, "
            f"File {file_num}/{file_total}"
        )
        if footer:
            log_message += f" | {footer}"

        self._logger.info(log_message)
