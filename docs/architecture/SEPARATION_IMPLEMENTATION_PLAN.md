# GUI/Business Logic Separation Implementation Plan

**Goal**: Enable multiple frontends (PyQt6 desktop + future web) by extracting business logic from Qt dependencies.

**Estimated Total Effort**: 15-25 hours across 4 phases

---

## Executive Summary

```
CURRENT STATE                         TARGET STATE
─────────────────                     ─────────────────
┌─────────────────┐                   ┌─────────────────┐
│   PyQt6 GUI     │                   │   PyQt6 GUI     │◄─── Qt Adapters
│   (tightly      │                   └────────┬────────┘
│    coupled)     │                            │
└────────┬────────┘                   ┌────────▼────────┐
         │                            │     PORTS       │◄─── Interfaces
┌────────▼────────┐                   │  (Abstractions) │
│ QSqlDatabase    │                   └────────┬────────┘
│ QMessageBox     │                            │
│ Mixed concerns  │                   ┌────────▼────────┐
└─────────────────┘                   │  CORE DOMAIN    │◄─── Pure Python
                                      │  (Framework-    │
                                      │   agnostic)     │
                                      └────────┬────────┘
                                               │
                                      ┌────────▼────────┐
                                      │  Web Frontend   │◄─── FastAPI Adapters
                                      │  (Future)       │
                                      └─────────────────┘
```

---

## Phase 1: Repository Interface Extraction (Foundation)

**Priority**: CRITICAL - All other phases depend on this  
**Effort**: 4-6 hours  
**Risk**: Low (additive changes, existing tests remain valid)

### 1.1 Create Core Domain Structure

```bash
mkdir -p core/ports
mkdir -p core/domain/models
mkdir -p adapters/qt/repositories
mkdir -p adapters/sqlite/repositories
```

**New file structure:**
```
batch-file-processor/
├── core/
│   ├── __init__.py
│   ├── ports/
│   │   ├── __init__.py
│   │   └── repositories.py      # Abstract interfaces
│   └── domain/
│       ├── __init__.py
│       └── models/
│           ├── __init__.py
│           ├── folder.py        # Copy from interface/models/
│           ├── settings.py      # Copy from interface/models/
│           └── processed_file.py
├── adapters/
│   ├── __init__.py
│   ├── qt/
│   │   ├── __init__.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── qt_folder_repo.py
│   └── sqlite/
│       ├── __init__.py
│       └── repositories/
│           ├── __init__.py
│           └── sqlite_folder_repo.py
```

### 1.2 Define Repository Interfaces

**File: `core/ports/repositories.py`**

```python
"""
Repository interfaces (ports) for data access abstraction.

These interfaces define the contract for data access, allowing
different implementations (Qt, pure SQLite, async, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from core.domain.models import Folder, Settings, ProcessedFile


class IFolderRepository(ABC):
    """Abstract interface for folder data access."""
    
    @abstractmethod
    def find_all(self, active_only: bool = False) -> List[Folder]:
        """Get all folders, optionally filtered to active only."""
        ...
    
    @abstractmethod
    def find_by_id(self, folder_id: int) -> Optional[Folder]:
        """Get a folder by its ID."""
        ...
    
    @abstractmethod
    def find_by_path(self, path: str) -> Optional[Folder]:
        """Get a folder by its filesystem path."""
        ...
    
    @abstractmethod
    def create(self, folder: Folder) -> int:
        """Create a new folder, return its ID."""
        ...
    
    @abstractmethod
    def update(self, folder: Folder) -> None:
        """Update an existing folder."""
        ...
    
    @abstractmethod
    def delete(self, folder_id: int) -> None:
        """Delete a folder by ID."""
        ...
    
    @abstractmethod
    def count(self, active_only: bool = False) -> int:
        """Count folders, optionally filtered to active only."""
        ...
    
    @abstractmethod
    def set_active(self, folder_id: int, active: bool) -> None:
        """Set folder active/inactive status."""
        ...
    
    @abstractmethod
    def set_all_active(self, active: bool) -> None:
        """Set all folders to active/inactive."""
        ...


class ISettingsRepository(ABC):
    """Abstract interface for settings/defaults access."""
    
    @abstractmethod
    def get_defaults(self) -> Dict[str, Any]:
        """Get default settings template."""
        ...
    
    @abstractmethod
    def update_defaults(self, settings: Dict[str, Any]) -> None:
        """Update default settings."""
        ...
    
    @abstractmethod
    def get_setting(self, key: str) -> Optional[Any]:
        """Get a specific setting value."""
        ...
    
    @abstractmethod
    def set_setting(self, key: str, value: Any) -> None:
        """Set a specific setting value."""
        ...


class IProcessedFilesRepository(ABC):
    """Abstract interface for processed files tracking."""
    
    @abstractmethod
    def is_processed(self, file_hash: str) -> bool:
        """Check if a file hash has been processed."""
        ...
    
    @abstractmethod
    def mark_processed(self, file_hash: str, folder_id: int, filename: str) -> None:
        """Mark a file as processed."""
        ...
    
    @abstractmethod
    def clear_all(self) -> int:
        """Clear all processed file records. Returns count deleted."""
        ...
    
    @abstractmethod
    def clear_for_folder(self, folder_id: int) -> int:
        """Clear processed records for a specific folder."""
        ...
    
    @abstractmethod
    def find_by_hash(self, file_hash: str) -> Optional[ProcessedFile]:
        """Find processed file record by hash."""
        ...


class IEmailQueueRepository(ABC):
    """Abstract interface for email queue management."""
    
    @abstractmethod
    def enqueue(self, email_data: Dict[str, Any]) -> None:
        """Add an email to the queue."""
        ...
    
    @abstractmethod
    def dequeue_batch(self, max_size: int, max_count: int) -> List[Dict[str, Any]]:
        """Get a batch of emails to send."""
        ...
    
    @abstractmethod
    def mark_sent(self, email_ids: List[int]) -> None:
        """Mark emails as sent."""
        ...
    
    @abstractmethod
    def clear_queue(self) -> int:
        """Clear all queued emails. Returns count deleted."""
        ...
```

### 1.3 Implement Qt Repository Adapter

**File: `adapters/qt/repositories/qt_folder_repo.py`**

```python
"""
Qt-based folder repository implementation.

Wraps the existing DatabaseManager/Table API to implement IFolderRepository.
"""

from typing import List, Optional
from core.ports.repositories import IFolderRepository
from core.domain.models import Folder


class QtFolderRepository(IFolderRepository):
    """Qt SQL implementation of folder repository."""
    
    def __init__(self, db_manager):
        """
        Initialize with existing DatabaseManager.
        
        Args:
            db_manager: interface.database.database_manager.DatabaseManager instance
        """
        self._db = db_manager
        self._table = db_manager.folders_table
    
    def find_all(self, active_only: bool = False) -> List[Folder]:
        if active_only:
            rows = self._table.find(folder_is_active="True")
        else:
            rows = self._table.all()
        return [self._row_to_folder(row) for row in rows]
    
    def find_by_id(self, folder_id: int) -> Optional[Folder]:
        row = self._table.find_one(id=folder_id)
        return self._row_to_folder(row) if row else None
    
    def find_by_path(self, path: str) -> Optional[Folder]:
        row = self._table.find_one(folder_name=path)
        return self._row_to_folder(row) if row else None
    
    def create(self, folder: Folder) -> int:
        data = self._folder_to_row(folder)
        if 'id' in data:
            del data['id']  # Let DB assign ID
        self._table.insert(data)
        created = self._table.find_one(folder_name=folder.path)
        return created['id'] if created else -1
    
    def update(self, folder: Folder) -> None:
        if folder.id is None:
            raise ValueError("Cannot update folder without ID")
        data = self._folder_to_row(folder)
        self._table.update(data, ['id'])
    
    def delete(self, folder_id: int) -> None:
        self._table.delete(id=folder_id)
    
    def count(self, active_only: bool = False) -> int:
        if active_only:
            return self._table.count(folder_is_active="True")
        return self._table.count()
    
    def set_active(self, folder_id: int, active: bool) -> None:
        self._table.update({
            'id': folder_id,
            'folder_is_active': "True" if active else "False"
        }, ['id'])
    
    def set_all_active(self, active: bool) -> None:
        # Need raw SQL for bulk update
        value = "True" if active else "False"
        self._db.database_connection.query(
            f"UPDATE folders SET folder_is_active = '{value}'"
        )
    
    def _row_to_folder(self, row: dict) -> Folder:
        """Convert database row to Folder domain model."""
        return Folder(
            id=row.get('id'),
            alias=row.get('alias', ''),
            path=row.get('folder_name', ''),
            active=row.get('folder_is_active') == "True",
            # ... map other fields
        )
    
    def _folder_to_row(self, folder: Folder) -> dict:
        """Convert Folder domain model to database row."""
        return {
            'id': folder.id,
            'alias': folder.alias,
            'folder_name': folder.path,
            'folder_is_active': "True" if folder.active else "False",
            # ... map other fields
        }
```

### 1.4 Implement Pure SQLite Repository

**File: `adapters/sqlite/repositories/sqlite_folder_repo.py`**

```python
"""
Pure SQLite folder repository implementation.

No Qt dependencies - suitable for CLI, web, or async contexts.
"""

import sqlite3
from typing import List, Optional
from contextlib import contextmanager
from core.ports.repositories import IFolderRepository
from core.domain.models import Folder


class SqliteFolderRepository(IFolderRepository):
    """Pure sqlite3 implementation of folder repository."""
    
    def __init__(self, database_path: str):
        """
        Initialize with database file path.
        
        Args:
            database_path: Path to SQLite database file
        """
        self._db_path = database_path
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def find_all(self, active_only: bool = False) -> List[Folder]:
        with self._get_connection() as conn:
            if active_only:
                cursor = conn.execute(
                    "SELECT * FROM folders WHERE folder_is_active = 'True'"
                )
            else:
                cursor = conn.execute("SELECT * FROM folders")
            return [self._row_to_folder(dict(row)) for row in cursor.fetchall()]
    
    def find_by_id(self, folder_id: int) -> Optional[Folder]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM folders WHERE id = ?", (folder_id,)
            )
            row = cursor.fetchone()
            return self._row_to_folder(dict(row)) if row else None
    
    # ... implement remaining methods similarly
    
    def _row_to_folder(self, row: dict) -> Folder:
        """Convert database row to Folder domain model."""
        return Folder(
            id=row.get('id'),
            alias=row.get('alias', ''),
            path=row.get('folder_name', ''),
            active=row.get('folder_is_active') == "True",
            # ... map other fields
        )
```

### 1.5 Migration Strategy

**Step-by-step migration for existing code:**

1. **Create interfaces and adapters** (non-breaking)
2. **Update `FolderOperations` to accept repository interface:**

```python
# BEFORE (interface/operations/folder_operations.py)
class FolderOperations:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager
    
    def add_folder(self, folder_path: str) -> Optional[int]:
        # Direct db_manager usage
        self.db_manager.folders_table.insert({...})

# AFTER
class FolderOperations:
    def __init__(
        self, 
        folder_repo: IFolderRepository,
        settings_repo: ISettingsRepository
    ) -> None:
        self._folder_repo = folder_repo
        self._settings_repo = settings_repo
    
    def add_folder(self, folder_path: str) -> Optional[int]:
        # Use repository interface
        defaults = self._settings_repo.get_defaults()
        folder = Folder(path=folder_path, alias=os.path.basename(folder_path))
        return self._folder_repo.create(folder)
```

3. **Update `ApplicationController` initialization:**

```python
# Wire up Qt adapters
from adapters.qt.repositories import QtFolderRepository, QtSettingsRepository

folder_repo = QtFolderRepository(db_manager)
settings_repo = QtSettingsRepository(db_manager)
self._folder_ops = FolderOperations(folder_repo, settings_repo)
```

### 1.6 Testing Strategy

```python
# tests/unit/test_folder_operations.py
from unittest.mock import Mock
from core.ports.repositories import IFolderRepository
from interface.operations.folder_operations import FolderOperations

def test_add_folder_creates_with_unique_alias():
    # Arrange
    mock_repo = Mock(spec=IFolderRepository)
    mock_repo.find_by_path.return_value = None
    mock_repo.create.return_value = 42
    
    ops = FolderOperations(folder_repo=mock_repo, settings_repo=Mock())
    
    # Act
    result = ops.add_folder("/path/to/folder")
    
    # Assert
    assert result == 42
    mock_repo.create.assert_called_once()
```

### 1.7 Phase 1 Checklist

- [ ] Create `core/` directory structure
- [ ] Define repository interfaces in `core/ports/repositories.py`
- [ ] Move/copy domain models to `core/domain/models/`
- [ ] Implement `QtFolderRepository` adapter
- [ ] Implement `QtSettingsRepository` adapter
- [ ] Implement `QtProcessedFilesRepository` adapter
- [ ] Implement `SqliteFolderRepository` (for testing/future use)
- [ ] Update `FolderOperations` to use interfaces
- [ ] Update `MaintenanceOperations` to use interfaces
- [ ] Update `ApplicationController` to wire adapters
- [ ] Add unit tests with mock repositories
- [ ] Verify all existing tests still pass

---

## Phase 2: UI Interaction Abstraction

**Priority**: HIGH - Removes dialog calls from business logic  
**Effort**: 3-4 hours  
**Risk**: Low-Medium (behavioral changes need careful testing)

### 2.1 Define UI Interaction Interfaces

**File: `core/ports/ui.py`**

```python
"""
UI interaction interfaces (ports) for user feedback abstraction.

These interfaces define the contract for user interactions, allowing
different implementations (Qt dialogs, web responses, CLI prompts).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Callable
from enum import Enum
from dataclasses import dataclass


class ConfirmResult(Enum):
    """Result of a confirmation dialog."""
    YES = "yes"
    NO = "no"
    CANCEL = "cancel"


@dataclass
class ProgressInfo:
    """Progress update information."""
    current: int
    total: int
    message: str = ""


class IProgressTracker(ABC):
    """Interface for tracking long-running operation progress."""
    
    @abstractmethod
    def update(self, value: int, message: str = "") -> None:
        """Update progress value and optional message."""
        ...
    
    @abstractmethod
    def is_cancelled(self) -> bool:
        """Check if user cancelled the operation."""
        ...
    
    @abstractmethod
    def close(self) -> None:
        """Close the progress indicator."""
        ...


class IUserInteraction(ABC):
    """Abstract interface for user interactions."""
    
    @abstractmethod
    def confirm(
        self, 
        title: str, 
        message: str,
        default: ConfirmResult = ConfirmResult.NO
    ) -> ConfirmResult:
        """
        Show confirmation dialog.
        
        Args:
            title: Dialog title
            message: Message to display
            default: Default button selection
            
        Returns:
            User's choice
        """
        ...
    
    @abstractmethod
    def show_info(self, title: str, message: str) -> None:
        """Show informational message."""
        ...
    
    @abstractmethod
    def show_error(self, title: str, message: str) -> None:
        """Show error message."""
        ...
    
    @abstractmethod
    def show_warning(self, title: str, message: str) -> None:
        """Show warning message."""
        ...
    
    @abstractmethod
    def select_directory(
        self, 
        title: str, 
        initial_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Show directory selection dialog.
        
        Returns:
            Selected path or None if cancelled
        """
        ...
    
    @abstractmethod
    def select_file(
        self,
        title: str,
        initial_dir: Optional[str] = None,
        filters: Optional[str] = None
    ) -> Optional[str]:
        """
        Show file selection dialog.
        
        Returns:
            Selected path or None if cancelled
        """
        ...
    
    @abstractmethod
    def create_progress(
        self, 
        title: str, 
        message: str,
        maximum: int,
        cancellable: bool = True
    ) -> IProgressTracker:
        """
        Create a progress tracker for long operations.
        
        Returns:
            Progress tracker instance
        """
        ...


class INotificationService(ABC):
    """Interface for sending notifications (non-blocking)."""
    
    @abstractmethod
    def notify_success(self, title: str, message: str) -> None:
        """Send success notification."""
        ...
    
    @abstractmethod
    def notify_error(self, title: str, message: str) -> None:
        """Send error notification."""
        ...
    
    @abstractmethod
    def notify_progress(self, operation_id: str, progress: ProgressInfo) -> None:
        """Send progress update for an operation."""
        ...
```

### 2.2 Implement Qt UI Adapter

**File: `adapters/qt/ui/qt_user_interaction.py`**

```python
"""
Qt implementation of user interaction interfaces.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMessageBox, QFileDialog, QProgressDialog, QWidget
)
from PyQt6.QtCore import Qt

from core.ports.ui import (
    IUserInteraction, IProgressTracker, ConfirmResult
)


class QtProgressTracker(IProgressTracker):
    """Qt implementation of progress tracking."""
    
    def __init__(self, dialog: QProgressDialog):
        self._dialog = dialog
        self._cancelled = False
        self._dialog.canceled.connect(self._on_cancel)
    
    def _on_cancel(self):
        self._cancelled = True
    
    def update(self, value: int, message: str = "") -> None:
        self._dialog.setValue(value)
        if message:
            self._dialog.setLabelText(message)
    
    def is_cancelled(self) -> bool:
        return self._cancelled or self._dialog.wasCanceled()
    
    def close(self) -> None:
        self._dialog.close()


class QtUserInteraction(IUserInteraction):
    """Qt implementation of user interaction interface."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        self._parent = parent
    
    def confirm(
        self, 
        title: str, 
        message: str,
        default: ConfirmResult = ConfirmResult.NO
    ) -> ConfirmResult:
        default_btn = (
            QMessageBox.StandardButton.Yes 
            if default == ConfirmResult.YES 
            else QMessageBox.StandardButton.No
        )
        
        reply = QMessageBox.question(
            self._parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_btn
        )
        
        return (
            ConfirmResult.YES 
            if reply == QMessageBox.StandardButton.Yes 
            else ConfirmResult.NO
        )
    
    def show_info(self, title: str, message: str) -> None:
        QMessageBox.information(self._parent, title, message)
    
    def show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self._parent, title, message)
    
    def show_warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self._parent, title, message)
    
    def select_directory(
        self, 
        title: str, 
        initial_dir: Optional[str] = None
    ) -> Optional[str]:
        path = QFileDialog.getExistingDirectory(
            self._parent, title, initial_dir or ""
        )
        return path if path else None
    
    def select_file(
        self,
        title: str,
        initial_dir: Optional[str] = None,
        filters: Optional[str] = None
    ) -> Optional[str]:
        path, _ = QFileDialog.getOpenFileName(
            self._parent, title, initial_dir or "", filters or ""
        )
        return path if path else None
    
    def create_progress(
        self, 
        title: str, 
        message: str,
        maximum: int,
        cancellable: bool = True
    ) -> IProgressTracker:
        dialog = QProgressDialog(message, "Cancel" if cancellable else "", 0, maximum, self._parent)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.show()
        return QtProgressTracker(dialog)
```

### 2.3 Refactor ApplicationController

**Current problem in `application_controller.py`:**
```python
# Qt dialogs embedded directly in business logic flow
def _handle_add_folder(self) -> None:
    folder_path = QFileDialog.getExistingDirectory(...)  # UI
    if existing["truefalse"]:
        reply = QMessageBox.question(...)  # UI
        if reply == QMessageBox.StandardButton.Yes:
            self._handle_edit_folder(folder_id)
```

**Refactored approach:**
```python
class ApplicationController:
    def __init__(
        self,
        main_window: "MainWindow",
        folder_repo: IFolderRepository,
        settings_repo: ISettingsRepository,
        ui: IUserInteraction,  # <-- Injected interface
        ...
    ):
        self._ui = ui
        self._folder_ops = FolderOperations(folder_repo, settings_repo)
    
    def _handle_add_folder(self) -> None:
        # Get initial directory
        initial_dir = self._settings_repo.get_setting("single_add_folder_prior")
        
        # Use interface instead of direct Qt call
        folder_path = self._ui.select_directory("Select Folder", initial_dir)
        if not folder_path:
            return
        
        # Update prior setting
        self._settings_repo.set_setting("single_add_folder_prior", folder_path)
        
        # Check existing
        existing = self._folder_ops.check_folder_exists(folder_path)
        
        if existing["truefalse"]:
            # Use interface instead of QMessageBox
            result = self._ui.confirm(
                "Folder Exists",
                "Folder already known, would you like to edit?"
            )
            if result == ConfirmResult.YES:
                self._handle_edit_folder(existing["matched_folder"]["id"])
        else:
            folder_id = self._folder_ops.add_folder(folder_path)
            # ... continue
```

### 2.4 Phase 2 Checklist

- [ ] Create `core/ports/ui.py` with interfaces
- [ ] Implement `QtUserInteraction` adapter
- [ ] Implement `QtProgressTracker` adapter
- [ ] Refactor `ApplicationController` to use `IUserInteraction`
- [ ] Remove direct `QMessageBox`/`QFileDialog` imports from controller
- [ ] Update controller initialization to inject UI adapter
- [ ] Test dialog flows still work correctly
- [ ] Add unit tests with mock UI interface

---

## Phase 3: Service Layer Extraction

**Priority**: MEDIUM - Creates clean API for any frontend  
**Effort**: 4-6 hours  
**Risk**: Medium (restructuring, but operations already mostly clean)

### 3.1 Create Service Layer

The service layer wraps operations and provides a clean API that:
- Takes repositories and UI interfaces via dependency injection
- Returns results (not void with side effects)
- Never imports Qt directly

**File: `core/services/folder_service.py`**

```python
"""
Folder management service.

Provides high-level folder operations independent of UI framework.
"""

import os
from typing import List, Optional, Tuple
from dataclasses import dataclass

from core.ports.repositories import IFolderRepository, ISettingsRepository
from core.ports.ui import IUserInteraction, ConfirmResult
from core.domain.models import Folder


@dataclass
class AddFolderResult:
    """Result of adding a folder."""
    success: bool
    folder_id: Optional[int] = None
    was_existing: bool = False
    error: Optional[str] = None


@dataclass
class BatchAddResult:
    """Result of batch adding folders."""
    added_ids: List[int]
    added_count: int
    skipped_count: int


class FolderService:
    """
    Service for folder management operations.
    
    This service is UI-framework agnostic and can be used by
    Qt GUI, web API, CLI, or any other frontend.
    """
    
    SKIP_FIELDS = [
        "folder_name", "alias", "id", "logs_directory", "errors_folder",
        "enable_reporting", "report_printing_fallback", "single_add_folder_prior",
        "batch_add_folder_prior", "export_processed_folder_prior", "report_edi_errors",
    ]
    
    def __init__(
        self,
        folder_repo: IFolderRepository,
        settings_repo: ISettingsRepository,
    ):
        self._folder_repo = folder_repo
        self._settings_repo = settings_repo
    
    def get_all_folders(self, active_only: bool = False) -> List[Folder]:
        """Get all folder configurations."""
        return self._folder_repo.find_all(active_only=active_only)
    
    def get_folder(self, folder_id: int) -> Optional[Folder]:
        """Get a specific folder by ID."""
        return self._folder_repo.find_by_id(folder_id)
    
    def check_folder_exists(self, path: str) -> Tuple[bool, Optional[Folder]]:
        """Check if a folder path is already configured."""
        folder = self._folder_repo.find_by_path(path)
        return (folder is not None, folder)
    
    def add_folder(self, path: str, alias: Optional[str] = None) -> AddFolderResult:
        """
        Add a new folder configuration.
        
        Args:
            path: Filesystem path to the folder
            alias: Optional display name (defaults to folder basename)
            
        Returns:
            AddFolderResult with status and folder ID
        """
        # Check if already exists
        exists, existing = self.check_folder_exists(path)
        if exists:
            return AddFolderResult(
                success=False,
                folder_id=existing.id,
                was_existing=True,
                error="Folder already configured"
            )
        
        # Get template settings
        defaults = self._settings_repo.get_defaults()
        template = {k: v for k, v in defaults.items() if k not in self.SKIP_FIELDS}
        
        # Generate unique alias
        base_alias = alias or os.path.basename(path)
        final_alias = self._generate_unique_alias(base_alias)
        
        # Create folder
        folder = Folder(
            path=path,
            alias=final_alias,
            active=True,
            **template
        )
        
        folder_id = self._folder_repo.create(folder)
        
        return AddFolderResult(
            success=True,
            folder_id=folder_id,
            was_existing=False
        )
    
    def _generate_unique_alias(self, base_alias: str) -> str:
        """Generate a unique alias, appending numbers if needed."""
        alias = base_alias
        counter = 1
        while self._folder_repo.find_by_alias(alias) is not None:
            alias = f"{base_alias} {counter}"
            counter += 1
        return alias
    
    def update_folder(self, folder: Folder) -> bool:
        """Update a folder configuration."""
        if folder.id is None:
            return False
        self._folder_repo.update(folder)
        return True
    
    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder configuration."""
        folder = self._folder_repo.find_by_id(folder_id)
        if not folder:
            return False
        self._folder_repo.delete(folder_id)
        return True
    
    def toggle_active(self, folder_id: int) -> Optional[bool]:
        """Toggle folder active status. Returns new status or None if not found."""
        folder = self._folder_repo.find_by_id(folder_id)
        if not folder:
            return None
        new_status = not folder.active
        self._folder_repo.set_active(folder_id, new_status)
        return new_status
    
    def batch_add_folders(self, paths: List[str]) -> BatchAddResult:
        """Add multiple folders at once."""
        added_ids = []
        skipped = 0
        
        for path in paths:
            result = self.add_folder(path)
            if result.success:
                added_ids.append(result.folder_id)
            else:
                skipped += 1
        
        return BatchAddResult(
            added_ids=added_ids,
            added_count=len(added_ids),
            skipped_count=skipped
        )
    
    def get_folder_count(self, active_only: bool = False) -> int:
        """Get count of configured folders."""
        return self._folder_repo.count(active_only=active_only)
```

**File: `core/services/processing_service.py`**

```python
"""
Processing orchestration service.

Coordinates the file processing workflow independent of UI framework.
"""

from dataclasses import dataclass
from typing import Optional, Callable, List
import datetime

from core.ports.repositories import IFolderRepository, ISettingsRepository
from core.domain.models import Folder


@dataclass
class ProcessingProgress:
    """Progress update during processing."""
    phase: str
    current: int
    total: int
    message: str


@dataclass  
class ProcessingResult:
    """Result of a processing run."""
    success: bool
    folders_processed: int
    files_processed: int
    errors: List[str]
    backup_path: Optional[str] = None
    log_path: Optional[str] = None
    duration_seconds: float = 0.0


ProgressCallback = Callable[[ProcessingProgress], bool]  # Returns False to cancel


class ProcessingService:
    """
    Service for orchestrating batch file processing.
    
    This wraps the existing ProcessingOrchestrator/dispatch logic
    with a clean interface suitable for any frontend.
    """
    
    def __init__(
        self,
        folder_repo: IFolderRepository,
        settings_repo: ISettingsRepository,
        database_path: str,
        version: str,
    ):
        self._folder_repo = folder_repo
        self._settings_repo = settings_repo
        self._database_path = database_path
        self._version = version
    
    def process_all_folders(
        self,
        auto_mode: bool = False,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """
        Process all active folders.
        
        Args:
            auto_mode: If True, run without interactive prompts
            progress_callback: Optional callback for progress updates
                              Return False from callback to cancel
        
        Returns:
            ProcessingResult with summary
        """
        start_time = datetime.datetime.now()
        errors = []
        
        # Get active folders
        folders = self._folder_repo.find_all(active_only=True)
        if not folders:
            return ProcessingResult(
                success=False,
                folders_processed=0,
                files_processed=0,
                errors=["No active folders configured"]
            )
        
        # Report initial progress
        if progress_callback:
            should_continue = progress_callback(ProcessingProgress(
                phase="initializing",
                current=0,
                total=len(folders),
                message="Starting processing..."
            ))
            if not should_continue:
                return ProcessingResult(
                    success=False,
                    folders_processed=0,
                    files_processed=0,
                    errors=["Cancelled by user"]
                )
        
        # TODO: Integrate with existing dispatch/coordinator
        # For now, this shows the interface pattern
        
        duration = (datetime.datetime.now() - start_time).total_seconds()
        
        return ProcessingResult(
            success=len(errors) == 0,
            folders_processed=len(folders),
            files_processed=0,  # TODO: track actual count
            errors=errors,
            duration_seconds=duration
        )
    
    def process_single_folder(
        self,
        folder_id: int,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """Process a single folder by ID."""
        folder = self._folder_repo.find_by_id(folder_id)
        if not folder:
            return ProcessingResult(
                success=False,
                folders_processed=0,
                files_processed=0,
                errors=[f"Folder {folder_id} not found"]
            )
        
        # TODO: Implement single-folder processing
        return ProcessingResult(
            success=True,
            folders_processed=1,
            files_processed=0,
            errors=[]
        )
```

### 3.2 Service Composition

**File: `core/services/__init__.py`**

```python
"""
Service layer - framework-agnostic business logic.

Usage:
    from core.services import create_services
    
    services = create_services(
        folder_repo=folder_repo,
        settings_repo=settings_repo,
        ...
    )
    
    result = services.folders.add_folder("/path/to/dir")
"""

from dataclasses import dataclass
from core.ports.repositories import (
    IFolderRepository, ISettingsRepository, IProcessedFilesRepository
)
from .folder_service import FolderService
from .processing_service import ProcessingService
from .maintenance_service import MaintenanceService


@dataclass
class Services:
    """Container for all application services."""
    folders: FolderService
    processing: ProcessingService
    maintenance: MaintenanceService


def create_services(
    folder_repo: IFolderRepository,
    settings_repo: ISettingsRepository,
    processed_files_repo: IProcessedFilesRepository,
    database_path: str,
    version: str,
) -> Services:
    """
    Factory function to create all services with dependencies.
    
    This is the main entry point for service layer initialization.
    """
    return Services(
        folders=FolderService(folder_repo, settings_repo),
        processing=ProcessingService(
            folder_repo, settings_repo, database_path, version
        ),
        maintenance=MaintenanceService(
            folder_repo, settings_repo, processed_files_repo
        ),
    )
```

### 3.3 Updated Controller Pattern

```python
# interface/application_controller.py (refactored)

from core.services import Services, create_services
from core.ports.ui import IUserInteraction, ConfirmResult
from adapters.qt.repositories import QtFolderRepository, QtSettingsRepository
from adapters.qt.ui import QtUserInteraction


class ApplicationController:
    """Application controller using service layer."""
    
    def __init__(
        self,
        main_window: "MainWindow",
        db_manager: "DatabaseManager",
        database_path: str,
        version: str,
    ):
        self._main_window = main_window
        
        # Create adapters
        folder_repo = QtFolderRepository(db_manager)
        settings_repo = QtSettingsRepository(db_manager)
        processed_repo = QtProcessedFilesRepository(db_manager)
        
        # Create services
        self._services = create_services(
            folder_repo=folder_repo,
            settings_repo=settings_repo,
            processed_files_repo=processed_repo,
            database_path=database_path,
            version=version,
        )
        
        # Create UI adapter
        self._ui = QtUserInteraction(main_window)
        
        self._connect_signals()
    
    def _handle_add_folder(self) -> None:
        """Handle add folder request - now much cleaner."""
        # Get directory from user
        folder_path = self._ui.select_directory(
            "Select Folder",
            self._services.folders.get_prior_folder_setting()
        )
        if not folder_path:
            return
        
        # Try to add
        result = self._services.folders.add_folder(folder_path)
        
        if result.was_existing:
            if self._ui.confirm("Folder Exists", "Edit existing?") == ConfirmResult.YES:
                self._handle_edit_folder(result.folder_id)
        elif result.success:
            self._ui.show_info("Success", f"Folder added: {folder_path}")
            self._refresh_folder_list()
        else:
            self._ui.show_error("Error", result.error or "Unknown error")
    
    def _handle_process_directories(self) -> None:
        """Handle process request - progress via callback."""
        if self._services.folders.get_folder_count(active_only=True) == 0:
            self._ui.show_error("Error", "No active folders")
            return
        
        # Create progress tracker
        progress = self._ui.create_progress(
            "Processing",
            "Processing directories...",
            maximum=100
        )
        
        def on_progress(p) -> bool:
            progress.update(
                int(p.current / p.total * 100),
                p.message
            )
            return not progress.is_cancelled()
        
        try:
            result = self._services.processing.process_all_folders(
                progress_callback=on_progress
            )
            
            if result.success:
                self._ui.show_info(
                    "Complete",
                    f"Processed {result.files_processed} files"
                )
            else:
                self._ui.show_error("Errors", "\n".join(result.errors))
        finally:
            progress.close()
```

### 3.4 Phase 3 Checklist

- [ ] Create `core/services/` directory
- [ ] Implement `FolderService` with result types
- [ ] Implement `ProcessingService` with progress callbacks  
- [ ] Implement `MaintenanceService`
- [ ] Create `create_services()` factory
- [ ] Refactor `ApplicationController` to use services
- [ ] Remove direct operations class usage from controller
- [ ] Add service layer unit tests
- [ ] Integration test services with mock repositories

---

## Phase 4: Web API Preparation (Future-Ready)

**Priority**: LOW - Only when web frontend is needed  
**Effort**: 4-6 hours  
**Risk**: Low (additive, existing code unchanged)

### 4.1 Async Repository Variants

For web (FastAPI), you'll want async database access:

**File: `adapters/async_sqlite/repositories/async_folder_repo.py`**

```python
"""
Async SQLite folder repository for web backends.
"""

import aiosqlite
from typing import List, Optional
from core.ports.repositories import IFolderRepository
from core.domain.models import Folder


class AsyncSqliteFolderRepository(IFolderRepository):
    """Async SQLite implementation using aiosqlite."""
    
    def __init__(self, database_path: str):
        self._db_path = database_path
    
    async def find_all(self, active_only: bool = False) -> List[Folder]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            if active_only:
                cursor = await db.execute(
                    "SELECT * FROM folders WHERE folder_is_active = 'True'"
                )
            else:
                cursor = await db.execute("SELECT * FROM folders")
            rows = await cursor.fetchall()
            return [self._row_to_folder(dict(row)) for row in rows]
    
    # ... other methods as async
```

### 4.2 FastAPI Router Example

**File: `adapters/api/routes/folders.py`**

```python
"""
FastAPI routes for folder management.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from core.services import FolderService
from core.domain.models import Folder
from ..dependencies import get_folder_service

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("/", response_model=List[Folder])
async def list_folders(
    active_only: bool = False,
    service: FolderService = Depends(get_folder_service)
):
    """Get all folder configurations."""
    return service.get_all_folders(active_only=active_only)


@router.post("/", response_model=dict)
async def add_folder(
    path: str,
    alias: str = None,
    service: FolderService = Depends(get_folder_service)
):
    """Add a new folder configuration."""
    result = service.add_folder(path, alias)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {"folder_id": result.folder_id}


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    service: FolderService = Depends(get_folder_service)
):
    """Delete a folder configuration."""
    if not service.delete_folder(folder_id):
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"status": "deleted"}


@router.post("/{folder_id}/toggle-active")
async def toggle_active(
    folder_id: int,
    service: FolderService = Depends(get_folder_service)
):
    """Toggle folder active status."""
    new_status = service.toggle_active(folder_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"active": new_status}
```

### 4.3 WebSocket Progress Updates

```python
"""
WebSocket support for real-time progress updates.
"""

from fastapi import WebSocket
from core.services import ProcessingService, ProcessingProgress


class WebProgressCallback:
    """WebSocket-based progress reporter."""
    
    def __init__(self, websocket: WebSocket):
        self._ws = websocket
        self._cancelled = False
    
    async def __call__(self, progress: ProcessingProgress) -> bool:
        await self._ws.send_json({
            "type": "progress",
            "phase": progress.phase,
            "current": progress.current,
            "total": progress.total,
            "message": progress.message
        })
        return not self._cancelled
    
    def cancel(self):
        self._cancelled = True


@router.websocket("/ws/process")
async def process_websocket(
    websocket: WebSocket,
    service: ProcessingService = Depends(get_processing_service)
):
    await websocket.accept()
    
    callback = WebProgressCallback(websocket)
    
    try:
        result = await service.process_all_folders(
            progress_callback=callback
        )
        
        await websocket.send_json({
            "type": "complete",
            "success": result.success,
            "files_processed": result.files_processed,
            "errors": result.errors
        })
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

### 4.4 Phase 4 Checklist

- [ ] Define async variants of repository interfaces (if needed)
- [ ] Implement `AsyncSqliteFolderRepository`
- [ ] Create FastAPI app structure in `adapters/api/`
- [ ] Implement REST routes for folders, settings, processing
- [ ] Add WebSocket support for progress updates
- [ ] Create dependency injection for FastAPI
- [ ] Add API authentication/authorization
- [ ] Write API integration tests
- [ ] Document API endpoints (OpenAPI/Swagger)

---

## Implementation Order & Dependencies

```
Phase 1: Repository Interfaces (FOUNDATION)
    │
    ├── 1.1 Create directory structure
    ├── 1.2 Define interfaces
    ├── 1.3 Qt adapter implementation
    ├── 1.4 SQLite adapter implementation
    └── 1.5 Migrate operations to use interfaces
           │
           ▼
Phase 2: UI Interaction Abstraction
    │
    ├── 2.1 Define UI interfaces
    ├── 2.2 Qt UI adapter
    └── 2.3 Refactor ApplicationController
           │
           ▼
Phase 3: Service Layer
    │
    ├── 3.1 Create service classes
    ├── 3.2 Service composition
    └── 3.3 Controller uses services
           │
           ▼
Phase 4: Web API (when needed)
    │
    ├── 4.1 Async repositories
    ├── 4.2 FastAPI routes
    └── 4.3 WebSocket progress
```

---

## Testing Strategy

### Unit Tests (Mock Dependencies)

```python
# tests/unit/services/test_folder_service.py
from unittest.mock import Mock
from core.services import FolderService
from core.domain.models import Folder

def test_add_folder_success():
    mock_repo = Mock()
    mock_repo.find_by_path.return_value = None
    mock_repo.create.return_value = 42
    
    service = FolderService(mock_repo, Mock())
    result = service.add_folder("/new/path")
    
    assert result.success
    assert result.folder_id == 42

def test_add_folder_already_exists():
    mock_repo = Mock()
    mock_repo.find_by_path.return_value = Folder(id=1, path="/existing")
    
    service = FolderService(mock_repo, Mock())
    result = service.add_folder("/existing")
    
    assert not result.success
    assert result.was_existing
```

### Integration Tests (Real Database)

```python
# tests/integration/services/test_folder_service_integration.py
import pytest
from adapters.sqlite.repositories import SqliteFolderRepository
from core.services import FolderService

@pytest.fixture
def folder_service(temp_database):
    repo = SqliteFolderRepository(temp_database)
    return FolderService(repo, Mock())

def test_add_and_retrieve_folder(folder_service):
    result = folder_service.add_folder("/test/path")
    assert result.success
    
    folder = folder_service.get_folder(result.folder_id)
    assert folder.path == "/test/path"
```

---

## Migration Checklist Summary

### Phase 1 (4-6 hours)
- [ ] Directory structure created
- [ ] Repository interfaces defined
- [ ] Qt adapters implemented
- [ ] SQLite adapters implemented
- [ ] Operations migrated to interfaces
- [ ] Existing tests pass

### Phase 2 (3-4 hours)
- [ ] UI interfaces defined
- [ ] Qt UI adapter implemented
- [ ] Controller refactored
- [ ] Dialog flows tested

### Phase 3 (4-6 hours)
- [ ] Service classes created
- [ ] Service composition factory
- [ ] Controller uses services
- [ ] Service unit tests

### Phase 4 (4-6 hours, when needed)
- [ ] Async repositories
- [ ] FastAPI routes
- [ ] WebSocket support
- [ ] API tests

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Each phase has tests; run full suite after each change |
| Qt-specific edge cases | Qt adapters wrap existing code, not rewrite |
| Performance regression | Pure SQLite adapter is simpler than Qt wrapper |
| Scope creep | Each phase is independent; stop after Phase 3 if web not needed |

---

## Quick Wins (Start Today)

If you want to start small:

1. **Create `core/ports/repositories.py`** with just `IFolderRepository`
2. **Create `adapters/qt/repositories/qt_folder_repo.py`** wrapping existing `Table`
3. **Update `FolderOperations.__init__`** to accept the interface
4. **Run tests** - everything should still work

This gives you the abstraction layer with minimal risk, and you can expand from there.
