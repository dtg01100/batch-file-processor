# Batch File Processor - Design Documentation

Welcome to the design documentation for the Batch File Processor. This directory contains detailed technical specifications covering the system's architecture, user interface, data flow, and component interfaces.

## Purpose

These documents serve as the authoritative reference for the system's design. They are intended for developers maintaining, extending, or refactoring the application. The goal is to provide a clear understanding of *how* the system works and *why* specific design decisions were made.

## Document Index

| Document | Summary |
| :--- | :--- |
| [**System Architecture**](SYSTEM_ARCHITECTURE.md) | A high-level overview of the system's layered architecture, core principles (Dependency Injection, Separation of Concerns), and component organization. |
| [**User Interface Design**](USER_INTERFACE_DESIGN.md) | Comprehensive specifications for the Tkinter-based GUI, detailing window layouts, dialog interactions, and custom widget behaviors. |
| [**Widget Layout Specification**](WIDGET_LAYOUT_SPECIFICATION.md) | **Historic/Reference** specification of the visual hierarchy, layout management, and widget configuration. Use this for visual layout details, but refer to other docs for architecture. |
| [**Edit Folders Dialog Design**](EDIT_FOLDERS_DIALOG_DESIGN.md) | **Current Architecture** design for the Edit Folders Dialog, covering the modular design (UI, Model, Validator, Extractor). |
| [**Output Formats Design**](OUTPUT_FORMATS_DESIGN.md) | Detailed definitions of all supported output formats (CSV, Custom, etc.), including field mappings, file naming conventions, and specific conversion logic. |
| [**Data Flow Design**](DATA_FLOW_DESIGN.md) | Traces the lifecycle of a file through the system, from ingestion in monitored folders to processing in the pipeline and final delivery. |
| [**API / Interface Design**](API_INTERFACE_DESIGN.md) | Defines the internal Python Protocols and interfaces used for dependency injection, testing, and backend abstraction. |

## Navigation Guide

Use the following guide to find the information relevant to your task:

*   **Adding a new Output Format?**
    *   Consult [`OUTPUT_FORMATS_DESIGN.md`](OUTPUT_FORMATS_DESIGN.md) to understand existing patterns and requirements.
    *   Review the "Converter Modules" section in [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md).

*   **Modifying the User Interface?**
    *   Refer to [`USER_INTERFACE_DESIGN.md`](USER_INTERFACE_DESIGN.md) for widget specifications and layout hierarchies.
    *   Check [`API_INTERFACE_DESIGN.md`](API_INTERFACE_DESIGN.md) for UI-related protocols (`MessageBoxProtocol`, `FileDialogProtocol`) if you need to mock UI interactions.

*   **Debugging File Processing Issues?**
    *   Follow the flow in [`DATA_FLOW_DESIGN.md`](DATA_FLOW_DESIGN.md) to understand the pipeline steps (Validation -> Splitting -> Tweaking -> Conversion -> Sending).
    *   See [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) for details on the `DispatchOrchestrator`.

*   **Refactoring Backend Logic?**
    *   Review [`API_INTERFACE_DESIGN.md`](API_INTERFACE_DESIGN.md) to understand the contracts your new backend must fulfill (e.g., `FTPClientProtocol`, `DatabaseInterface`).
    *   Check [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) for the architectural boundaries between the Core, Backend, and Dispatch layers.
