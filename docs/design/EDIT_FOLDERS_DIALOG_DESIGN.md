# Edit Folders Dialog Design

> **Note:** This document reflects the **current modular architecture** of the Edit Folders Dialog. For the detailed visual specification and widget hierarchy, please refer to the [**Widget Layout Specification**](WIDGET_LAYOUT_SPECIFICATION.md).

## 1. Overview

The **Edit Folders Dialog** (`interface.ui.dialogs.edit_folders_dialog.EditFoldersDialog`) is the primary interface for configuring folder-specific processing rules. It allows users to define input sources, processing logic (EDI conversion, splitting), and output destinations (Copy, FTP, Email).

Unlike earlier versions of the application, the current implementation follows a **modular architecture** using **Dependency Injection (DI)**. This separates the UI logic from data validation, extraction, and external services, enabling comprehensive unit testing without reliance on the GUI or live network connections.

### Key Responsibilities
*   **Configuration Management**: Edit folder processing rules.
*   **Modular Validation**: Validate settings using a dedicated validator class.
*   **Data Extraction**: Extract data from UI widgets into structured models.
*   **Service Abstraction**: Use abstract interfaces for external services (e.g., FTP) to support mocking.

## 2. Architecture

The dialog is structured around several collaborating components:

| Component | Class | Responsibility |
| :--- | :--- | :--- |
| **UI Controller** | [`EditFoldersDialog`](interface/ui/dialogs/edit_folders_dialog.py:37) | Manages the Tkinter window, widget lifecycle, and user interactions. |
| **Data Model** | [`FolderConfiguration`](interface/models/folder_configuration.py:222) | A structured dataclass representing the complete configuration state. |
| **Validator** | [`FolderSettingsValidator`](interface/validation/folder_settings_validator.py:55) | Contains all business logic for validating configuration rules. |
| **Extractor** | [`FolderDataExtractor`](interface/operations/folder_data_extractor.py) | Responsible for pulling raw values from UI widgets and populating the Data Model. |
| **Service** | [`FTPService`](interface/services/ftp_service.py:30) | Handles network operations (e.g., testing FTP connections) behind a protocol. |

### Dependency Injection
The `EditFoldersDialog` accepts dependencies via its constructor:
```python
def __init__(
    self,
    parent,
    foldersnameinput: Dict[str, Any],
    ftp_service: Optional[FTPServiceProtocol] = None,
    validator: Optional[FolderSettingsValidator] = None,
    extractor: Optional[FolderDataExtractor] = None,
    ...
)
```
This allows tests to inject mock services and validators, isolating the UI logic.

## 3. Data Model

The configuration is modeled using Python `dataclasses` in [`interface.models.folder_configuration`](interface/models/folder_configuration.py). This provides type safety and centralized validation logic for individual fields.

### 3.1. FolderConfiguration
The root object containing all settings:
*   **Identity**: `folder_name`, `alias`, `is_active`
*   **Backend Toggles**: `process_backend_copy`, `process_backend_ftp`, `process_backend_email`
*   **Sub-Configurations**: Nested dataclasses for specific domains.

### 3.2. Sub-Configurations
*   [`FTPConfiguration`](interface/models/folder_configuration.py:37): Server, port, credentials, folder path.
*   [`EmailConfiguration`](interface/models/folder_configuration.py:68): Recipients, subject line.
*   [`CopyConfiguration`](interface/models/folder_configuration.py:93): Destination directory.
*   [`EDIConfiguration`](interface/models/folder_configuration.py:106): Splitting, conversion formats, filtering.
*   [`UPCOverrideConfiguration`](interface/models/folder_configuration.py:129): UPC manipulation rules.
*   [`ARecordPaddingConfiguration`](interface/models/folder_configuration.py:156): Padding rules for A-records.
*   [`InvoiceDateConfiguration`](interface/models/folder_configuration.py:182): Date offset and formatting.

## 4. Interaction Flow

### 4.1. Initialization
1.  **Injection**: The dialog is instantiated with dependencies (or defaults if not provided).
2.  **UI Construction**: The `body()` method builds the widget hierarchy (refer to [Widget Layout Specification](WIDGET_LAYOUT_SPECIFICATION.md)).
3.  **Data Loading**: `set_dialog_variables()` populates the Tkinter variables from the initial configuration dictionary.

### 4.2. Validation & Saving
When the user clicks "Apply" or "Save":
1.  **Extraction**: The `FolderDataExtractor` reads values from the Tkinter variables and constructs a `FolderConfiguration` object.
2.  **Validation**: The `FolderSettingsValidator` checks the `FolderConfiguration` object.
    *   It performs static checks (required fields, format validation).
    *   It performs dynamic checks (FTP connection testing via `FTPService`).
3.  **Result Handling**:
    *   **Invalid**: Errors are displayed to the user.
    *   **Valid**: The configuration is saved to the database/backend.

## 5. Layout & Components

> **Reference:** For the canonical specification of the widget layout, including frame nesting, packing order, and specific widget types, see [**WIDGET_LAYOUT_SPECIFICATION.md**](WIDGET_LAYOUT_SPECIFICATION.md).

The layout is organized into four main columns within the body frame:
1.  **Others Frame**: List of other folders (for copying settings).
2.  **Folder Frame**: Basic identity and backend selection.
3.  **Preferences Frame**: Configuration for enabled backends (Copy, FTP, Email).
4.  **EDI Frame**: EDI processing, splitting, and conversion options.

The **Convert Options Frame** (inside the EDI Frame) is dynamic, showing different fields based on the selected "Convert To" format.
