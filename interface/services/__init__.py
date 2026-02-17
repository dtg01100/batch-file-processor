"""Services package for interface module.

This package contains service classes that provide business logic
separated from UI concerns.

Available services:
- FTPService: FTP connection testing and operations
- ReportingService: Email reporting and log file handling
"""

from interface.services.ftp_service import FTPService, FTPConnectionResult, MockFTPService
from interface.services.reporting_service import ReportingService

__all__ = [
    "FTPService",
    "FTPConnectionResult",
    "MockFTPService",
    "ReportingService",
]
