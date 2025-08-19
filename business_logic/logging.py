import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(log_path: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a module-level logger for the application.

    - Logger name: "batch_file_processor"
    - Adds a StreamHandler (console) and, if log_path is provided, a
      RotatingFileHandler (10MB, 5 backups).
    - Timestamps use ISO8601-like formatting: YYYY-MM-DDThh:mm:ss±ZZZZ.
    - Calling multiple times is safe (handlers are only added once).
    """
    logger = logging.getLogger("batch_file_processor")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if setup_logging is called more than once
    if logger.handlers:
        return logger

    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S%z"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Stream handler (stderr)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Optional rotating file handler
    if log_path:
        file_handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger