# Widget Layout Specification

> **Note:** This document reflects the UI state at commit `9446b3de7e0eb96122a1151620de7c012898269b`. File paths refer to the structure at that time (primarily `interface.py`).

This document provides a comprehensive and pedantic specification of the widget layout for the Batch File Sender application. It details the visual hierarchy, layout management, and widget configuration for all major dialogs and windows.

## 1. Main Application Window (`interface.py`)

The main application window serves as the primary interface for user interaction. It is divided into a left-side options panel and a right-side folder list.

### 1.1 Visual Hierarchy

*   **Root Window** (`tkinter.Tk`)
    *   **Options Frame** (`tkinter.ttk.Frame`) - Left Panel
        *   `Button`: "Add Directory..."
        *   `Button`: "Batch Add Directories..."
        *   `Button`: "Set Defaults..."
        *   `Button`: "Edit Settings..."
        *   `Button`: "Process All Folders"
        *   `Separator` (Horizontal)
        *   `Button`: "Maintenance..."
        *   `Button`: "Enable Resend..."
        *   `Separator` (Horizontal)
        *   `Button`: "Processed Files Report..."
    *   **Users List Frame** (`tkinter.ttk.Frame`) - Right Panel
        *   **Folder List Widget** (Dynamic Frame Structure)
            *   *See Section 2 for details*
        *   **Search Widget** (Dynamic Frame Structure)
            *   *See Section 3 for details*

### 1.2 Layout Management

*   **Options Frame**: Packed to the left (`side=tkinter.LEFT`, `anchor="n"`, `fill=tkinter.Y`).
    *   Buttons are packed vertically (`side=tkinter.TOP`, `fill=tkinter.X`, `pady=2`, `padx=2`).
    *   "Process All Folders" is packed at the bottom of its group (`side=tkinter.BOTTOM`).
    *   Separators are packed with `fill="x"`.
*   **Users List Frame**: Packed to the right (`side=tkinter.RIGHT`, `fill=tkinter.BOTH`, `expand=tkinter.TRUE`).
    *   **Search Widget**: Packed at the bottom (`side=tkinter.BOTTOM`, `ipady=5`).
    *   **Folder List Widget**: Packed to the right (`side=tkinter.RIGHT`, `fill=tkinter.BOTH`, `expand=tkinter.TRUE`).

### 1.3 Widget Details

| Widget Type | Text / Label | Position (Pack) | Styling / Notes |
| :--- | :--- | :--- | :--- |
| `ttk.Button` | "Add Directory..." | Top, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Batch Add Directories..." | Top, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Set Defaults..." | Top, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Edit Settings..." | Top, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Process All Folders" | Bottom, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Maintenance..." | Top, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Enable Resend..." | Bottom, Fill X | `pady=2`, `padx=2` |
| `ttk.Button` | "Processed Files Report..." | Top, Fill X | `pady=2`, `padx=2` |

---

## 2. Folder List Widget (`interface.py` - `make_users_list`)

This widget displays the list of active and inactive folders.

### 2.1 Visual Hierarchy

*   **Main Frame** (`users_list_frame`)
    *   **Scrollable Lists Frame** (`tkinter.ttk.Frame`)
        *   **Inactive List Container** (`tkinter.ttk.Frame`)
            *   `Label`: "Inactive Folders"
            *   `Separator` (Horizontal)
            *   **Inactive Scrolled Frame** (`VerticalScrolledFrame`)
                *   *List of Inactive Folder Rows*
        *   **Active List Container** (`tkinter.ttk.Frame`)
            *   `Label`: "Active Folders"
            *   `Separator` (Horizontal)
            *   **Active Scrolled Frame** (`VerticalScrolledFrame`)
                *   *List of Active Folder Rows*
    *   **Separator** (Horizontal)

### 2.2 Layout Management

*   **Scrollable Lists Frame**: Packed at the bottom (`side=tkinter.BOTTOM`, `expand=tkinter.TRUE`, `fill=tkinter.Y`).
    *   **Inactive List Container**: Packed to the left (`side=tkinter.LEFT`, `expand=tkinter.TRUE`, `fill=tkinter.Y`).
    *   **Active List Container**: Packed to the right (`side=tkinter.RIGHT`, `expand=tkinter.TRUE`, `fill=tkinter.Y`).
*   **Scrolled Frames**: Packed with `fill=tkinter.BOTH`, `expand=tkinter.TRUE`, `anchor=tkinter.E`, `padx=3`, `pady=3`.

### 2.3 Widget Details (Folder Rows)

**Active Folder Row:**
*   `Button` ("<-"): Grid `column=0`, `row=0`.
*   `Button` ("Edit: [Alias]..."): Grid `column=1`, `row=0`, `sticky=E+W`.
*   `Button` ("Send"): Grid `column=2`, `row=0`, `padx=(0, 10)`.

**Inactive Folder Row:**
*   `Button` ("Edit: [Alias]..."): Grid `column=0`, `row=0`, `sticky=E+W`, `padx=(10, 0)`.
*   `Button` ("Delete"): Grid `column=1`, `row=0`, `sticky=E`, `padx=(0, 10)`.

---

## 3. Search Widget (`interface.py` - `make_users_list`)

A reusable widget for filtering the folder list.

### 3.1 Visual Hierarchy

*   **Main Frame** (`search_frame`)
    *   `Entry`: Search input field.
    *   `Button`: "Update Filter".

### 3.2 Layout Management

*   **Entry**: Packed to the left (`side=tkinter.LEFT`).
*   **Button**: Packed to the right (`side=tkinter.RIGHT`).

---

## 4. Edit Settings Dialog (`interface.py` - `EditSettingsDialog`)

A modal dialog for configuring application-wide settings.

### 4.1 Visual Hierarchy

*   **Dialog Body**
    *   **AS400 Connection Frame** (`tkinter.ttk.Frame`)
        *   `Label`: "ODBC Driver:"
        *   `OptionMenu`: Driver Selection
        *   `Label`: "AS400 Address:"
        *   `Entry`: Address Input
        *   `Label`: "AS400 Username:"
        *   `Entry`: Username Input
        *   `Label`: "AS400 Password:"
        *   `Entry`: Password Input
    *   **Email Options Frame** (`tkinter.ttk.Frame`)
        *   `Label`: "Email Address:"
        *   `Entry`: Email Input
        *   `Label`: "Email Username:"
        *   `Entry`: Username Input
        *   `Label`: "Email Password:"
        *   `Entry`: Password Input
        *   `Label`: "Email SMTP Server:"
        *   `Entry`: Server Input
        *   `Label`: "Email SMTP Port"
        *   `Entry`: Port Input
    *   **Report Sending Options Frame** (`tkinter.ttk.Frame`)
        *   `Label`: "Email Destination:"
        *   `Entry`: Destination Input
    *   **Interval Backups Frame** (`tkinter.ttk.Frame`)
        *   `Checkbutton`: "Enable interval backup"
        *   `Label`: "Backup interval: "
        *   `Spinbox`: Interval Input
    *   **Global Checkbuttons**
        *   `Checkbutton`: "Enable Email"
        *   `Checkbutton`: "Enable Report Sending"
        *   `Checkbutton`: "Report EDI Validator Warnings"
        *   `Checkbutton`: "Enable Report Printing Fallback:"
    *   **Buttons**
        *   `Button`: "Select Log Folder..."

### 4.2 Layout Management

The dialog uses a **Grid** layout manager.

*   **AS400 Frame**: `row=0`, `column=0`, `columnspan=2`, `sticky=W+E`.
    *   Labels are `sticky=E`.
    *   Entries are in `column=1`.
*   **Enable Email Checkbutton**: `row=1`, `columnspan=3`, `sticky=W`.
*   **Email Options Frame**: `row=2`, `columnspan=3`.
    *   Labels are `sticky=E`.
    *   Entries are in `column=1`.
*   **Enable Report Sending Checkbutton**: `row=3`, `column=0`, `sticky=W`.
*   **Select Log Folder Button**: `row=3`, `column=1`, `sticky=E`, `rowspan=2`.
*   **Report EDI Validator Warnings Checkbutton**: `row=4`, `column=0`, `sticky=W`.
*   **Report Sending Options Frame**: `row=5`, `columnspan=3`.
*   **Enable Report Printing Fallback Checkbutton**: `row=8`, `column=1`, `sticky=W`.
*   **Interval Backups Frame**: `row=9`, `column=0`, `columnspan=3`, `sticky=W+E`.

### 4.3 Widget Details

| Widget Type | Text / Label | Grid Position | Notes |
| :--- | :--- | :--- | :--- |
| `ttk.Checkbutton` | "Enable Email" | Row 1, Colspan 3 | Controls Email Frame state |
| `ttk.Checkbutton` | "Enable Report Sending" | Row 3, Col 0 | Controls Report Frame state |
| `ttk.Entry` | (Various) | Column 1 | Width=40 |
| `ttk.Spinbox` | (Backup Interval) | Row 0, Col 2 (Inner) | Width=4, Justify=RIGHT |

---

## 5. Maintenance Dialog (`interface.py` - `maintenance_functions_popup`)

A popup window for advanced maintenance operations.

### 5.1 Visual Hierarchy

*   **Popup Window** (`tkinter.Toplevel`)
    *   **Button Frame** (`tkinter.ttk.Frame`)
        *   `Button`: "Move all to active (Skips Settings Validation)"
        *   `Button`: "Move all to inactive"
        *   `Button`: "Clear all resend flags"
        *   `Button`: "Clear queued emails"
        *   `Button`: "Mark all in active as processed"
        *   `Button`: "Remove all inactive configurations"
        *   `Button`: "Clear sent file records"
        *   `Button`: "Import old configurations..."
    *   **Warning Label** (`tkinter.ttk.Label`)

### 5.2 Layout Management

*   **Button Frame**: Packed to the left (`side=tkinter.LEFT`).
    *   All buttons are packed vertically (`side=tkinter.TOP`, `fill=tkinter.X`, `padx=2`, `pady=2`).
*   **Warning Label**: Packed to the right (`side=tkinter.RIGHT`, `padx=20`).

---

## 6. Processed Files Dialog (`interface.py` - `processed_files_popup`)

A dialog for viewing and exporting processed file reports.

### 6.1 Visual Hierarchy

*   **Popup Window** (`tkinter.Toplevel`)
    *   **Body Frame** (`tkinter.ttk.Frame`)
        *   **List Container** (`tkinter.ttk.Frame`)
            *   **List Frame** (`VerticalScrolledFrame`)
                *   *List of Radiobuttons (Folder Aliases)*
        *   **Actions Frame** (`tkinter.ttk.Frame`)
            *   `Label`: "Select a Folder."
            *   `Button`: "Choose output Folder" (Dynamic)
            *   `Button`: "Export Processed Report" (Dynamic)
    *   **Separator** (Horizontal)
    *   **Close Frame** (`tkinter.ttk.Frame`)
        *   `Button`: "Close"

### 6.2 Layout Management

*   **List Container**: Packed to the left (`side=tkinter.LEFT`).
*   **Actions Frame**: Packed to the right (`side=tkinter.RIGHT`, `anchor=tkinter.N`, `padx=5`).
*   **Close Frame**: Packed at the bottom.
*   **Radiobuttons**: Packed inside the scrolled frame (`anchor="w"`, `fill="x"`).

---

## 7. Edit Folders Dialog (`interface.py` - `EditDialog`)

A complex dialog for editing individual folder settings.

*Note: This dialog is highly dynamic based on the selected "Convert To" format.*

### 7.1 Visual Hierarchy (High Level)

*   **Header Frame** (`tkinter.ttk.Frame`)
    *   `Checkbutton`: "Active"
*   **Body Frame** (`tkinter.ttk.Frame`)
    *   **Others Frame** (`tkinter.ttk.Frame`)
        *   `Listbox`: List of other folders (for copying config)
        *   `Button`: "Copy Config"
    *   **Folder Frame** (`tkinter.ttk.Frame`)
        *   *Folder Path, Alias, Backend Selection*
    *   **Preferences Frame** (`tkinter.ttk.Frame`)
        *   *Copy, FTP, and Email Backend Settings*
    *   **EDI Frame** (`tkinter.ttk.Frame`)
        *   *EDI Conversion Settings*
        *   **Convert Options Frame** (`tkinter.ttk.Frame`)
            *   *Dynamic options based on format*

### 7.2 Layout Management

*   **Header Frame**: Packed at the top (`fill=tkinter.X`).
*   **Body Frame**: Packed below header.
    *   **Others Frame**: Packed to the left (`side=tkinter.LEFT`, `fill=tkinter.Y`).
    *   **Folder Frame**: Packed to the left (`side=tkinter.LEFT`, `anchor="n"`).
    *   **Preferences Frame**: Packed to the left (`side=tkinter.LEFT`, `anchor="n"`).
    *   **EDI Frame**: Packed to the left (`side=tkinter.LEFT`, `anchor="n"`).
*   **Grid Layout** is used within the frames.
*   **Dynamic Visibility**: Widgets in the `Convert Options Frame` are shown/hidden using `grid()` and `grid_forget()` based on the `convert_formats_var`.

### 7.3 Key Widget Groups

*   **Backends**: Checkbuttons for Copy, FTP, Email.
*   **FTP Settings**: Server, Port, Folder, Username, Password.
*   **Email Settings**: Recipient, Subject.
*   **Convert To**: OptionMenu for selecting format (CSV, ScannerWare, etc.).

