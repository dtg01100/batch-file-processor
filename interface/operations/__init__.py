"""
Operations module initialization.

This module provides folder operations, processing orchestration,
and maintenance functionality for the interface.py refactoring.

Classes:
    FolderOperations: CRUD operations for folder configurations
    ProcessingOrchestrator: Orchestrates directory processing workflow
    MaintenanceOperations: Database maintenance and cleanup operations
"""

from .folder_operations import FolderOperations
from .processing import ProcessingOrchestrator, ProcessingResult, DispatchResult, automatic_process_directories
from .maintenance import MaintenanceOperations

__all__ = [
    "FolderOperations",
    "ProcessingOrchestrator",
    "ProcessingResult",
    "DispatchResult",
    "automatic_process_directories",
    "MaintenanceOperations",
]
