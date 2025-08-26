# Architecture Analysis of the Batch File Processor

## 1. High-Level Overview

The Batch File Processor is a desktop application designed to automate the processing of files in batches. It provides a graphical user interface (GUI) built with `tkinter` for configuring and monitoring file processing tasks. The application's architecture can be broken down into the following key components:

*   **User Interface (`interface.py`):** This is the main entry point of the application, responsible for creating the GUI, handling user interactions, and managing the overall application flow. It uses the `tkinter` library to create windows, dialogs, and widgets for user input and feedback.

*   **Business Logic (`business_logic/`):** This directory contains the core application logic, separated from the UI. It includes modules for database interactions (`db.py`), interface-related logic (`interface_logic.py`), and logging (`logging.py`). This separation of concerns is a good architectural practice that improves modularity and testability.

*   **Dispatching and Processing (`dispatch.py`):** This component is responsible for orchestrating the file processing workflow. It iterates through the configured folders, identifies new files, and processes them according to the defined rules. It uses a multi-threaded approach to handle file hashing and processing, which can improve performance on multi-core systems.

*   **Database (`folders.db`):** The application uses a SQLite database to store its configuration, including folder settings, email configurations, and a record of processed files. The `dataset` library is used to simplify database interactions.

*   **File Conversion and Tweaking:** The application supports various file conversion formats, such as CSV, XML, and custom formats. The conversion logic is implemented in separate modules (e.g., `convert_to_csv.py`, `edi_tweaks.py`), which are dynamically loaded and executed by the dispatch module.

*   **Backends:** The application supports multiple backends for sending processed files, including copying to a local directory, uploading via FTP, and sending via email. The logic for each backend is encapsulated in its own module (e.g., `copy_backend.py`, `ftp_backend.py`, `email_backend.py`).

### Component Interactions

The following diagram illustrates the high-level interactions between the components:

```mermaid
graph TD
    A[User Interface] -->|User Actions| B(Business Logic)
    B -->|Configuration| C{Database}
    A -->|Start Processing| D[Dispatch]
    D -->|Read Configuration| C
    D -->|Process Files| E(File Conversion)
    E -->|Send Files| F{Backends}
    F -->|Copy| G[Local Directory]
    F -->|FTP| H[FTP Server]
    F -->|Email| I[Email Server]
    D -->|Log Results| C