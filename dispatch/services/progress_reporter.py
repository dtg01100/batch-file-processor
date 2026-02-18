from typing import Protocol, Optional
import logging
import sys


class ProgressReporter(Protocol):
    def update(
        self,
        message: str,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str,
    ) -> None:
        ...


class UIProgressReporter:
    def __init__(self):
        self._parent = None
        self._overlay_text = ""
        self._footer = ""
        self._overlay_height = 120

    def update(
        self,
        message: str,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str,
    ) -> None:
        self.update_overlay(
            parent=self._parent,
            overlay_text=message,
            footer=footer,
            overlay_height=self._overlay_height,
        )

    def update_overlay(
        self,
        parent,
        overlay_text: str,
        footer: str,
        overlay_height: int,
    ) -> None:
        pass


class CLIProgressReporter:
    def __init__(self, output: Optional[object] = None):
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

    def finish(self) -> None:
        self._output.write("\n")
        self._output.flush()


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


class LoggingProgressReporter:
    def __init__(self, logger: logging.Logger):
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
            f"{message} | "
            f"Folder {folder_num}/{folder_total}, "
            f"File {file_num}/{file_total}"
        )
        if footer:
            log_message += f" | {footer}"

        self._logger.info(log_message)
