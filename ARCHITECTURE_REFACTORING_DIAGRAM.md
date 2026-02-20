# Batch File Processor - Architecture & Refactoring Diagram

## Current Architecture Overview

```mermaid
graph TD
    A[Main Application] --> B[Legacy Tkinter Interface<br/>interface/app.py<br/>(43,213 chars)]
    A --> C[Qt Interface<br/>interface/qt/app.py<br/>(35,291 chars)]
    
    B --> D[Edit Folders Dialog<br/>interface/ui/dialogs/edit_folders_dialog.py<br/>(75,218 chars)]
    C --> E[Qt Edit Folders Dialog<br/>interface/qt/dialogs/edit_folders_dialog.py<br/>(58,539 chars)]
    
    A --> F[Dispatch System]
    F --> G[Legacy Dispatch<br/>dispatch_process.py<br/>(33,332 chars)]
    F --> H[New Pipeline<br/>dispatch/orchestrator.py<br/>(22,068 chars)]
    
    H --> I[Converter Step<br/>dispatch/pipeline/converter.py<br/>(12,654 chars)]
    H --> J[Splitter Step<br/>dispatch/pipeline/splitter.py<br/>(17,205 chars)]
    H --> K[Tweaker Step<br/>dispatch/pipeline/tweaker.py<br/>(9,220 chars)]
    H --> L[Validator Step<br/>dispatch/pipeline/validator.py<br/>(9,416 chars)]
    
    I --> M[Convert Backends]
    M --> N[convert_to_csv.py<br/>(8,809 chars)]
    M --> O[convert_to_simplified_csv.py<br/>(6,115 chars)]
    M --> P[convert_to_estore_einvoice.py<br/>(9,897 chars)]
    M --> Q[convert_to_estore_einvoice_generic.py<br/>(14,426 chars)]
    M --> R[convert_to_fintech.py<br/>(3,311 chars)]
    M --> S[convert_to_jolley_custom.py<br/>(12,379 chars)]
    M --> T[convert_to_stewarts_custom.py<br/>(12,099 chars)]
    M --> U[convert_to_scansheet_type_a.py<br/>(9,452 chars)]
    
    F --> V[Core Services]
    V --> W[Database Abstraction<br/>core/database/query_runner.py<br/>(7,048 chars)]
    V --> X[EDI Parsing<br/>core/edi/edi_parser.py<br/>(6,970 chars)]
    V --> Y[Utils Module<br/>utils.py<br/>(785 lines)]
    
    style B fill:#f96,stroke:#333,stroke-width:2px,color:#fff
    style D fill:#f96,stroke:#333,stroke-width:2px,color:#fff
    style M fill:#ff6,stroke:#333,stroke-width:2px
    style Y fill:#ff6,stroke:#333,stroke-width:2px
```

## Convert Backend Code Duplication

```mermaid
graph TD
    A[convert_to_csv.py] --> B[convert_to_price()]
    C[convert_to_simplified_csv.py] --> B
    D[convert_to_stewarts_custom.py] --> B
    E[convert_to_jolley_custom.py] --> B
    F[convert_to_estore_einvoice.py] --> B
    G[convert_to_estore_einvoice_generic.py] --> B
    
    H[convert_to_stewarts_custom.py] --> I[prettify_dates()]
    J[convert_to_jolley_custom.py] --> I
    
    K[convert_to_simplified_csv.py] --> L[CustomerLookupError]
    H --> L
    
    M[utils.py] --> N[invFetcher]
    G --> O[invFetcher<br/>(duplicate)]
    
    style B fill:#ff6,stroke:#333,stroke-width:2px
    style I fill:#ff6,stroke:#333,stroke-width:2px
    style L fill:#ff6,stroke:#333,stroke-width:2px
    style O fill:#f96,stroke:#333,stroke-width:2px,color:#fff
```

## UI Layer Architecture

```mermaid
graph TD
    A[User Interface Layer] --> B[Tkinter Interface<br/>(Legacy)]
    A --> C[Qt Interface<br/>(Modern)]
    
    B --> D[EditFoldersDialog<br/>(75,218 chars)]
    C --> E[QtEditFoldersDialog<br/>(58,539 chars)]
    
    D --> F[Validation Logic]
    E --> G[Validation Logic<br/>(Duplicate)]
    
    D --> H[Data Extraction]
    E --> I[Data Extraction<br/>(Duplicate)]
    
    D --> J[UI Rendering<br/>(Tkinter)]
    E --> K[UI Rendering<br/>(Qt)]
    
    D --> L[Business Logic<br/>(Folder Management)]
    E --> M[Business Logic<br/>(Duplicate)]
    
    style D fill:#f96,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#f96,stroke:#333,stroke-width:2px,color:#fff
    style G fill:#ff6,stroke:#333,stroke-width:2px
    style I fill:#ff6,stroke:#333,stroke-width:2px
    style M fill:#ff6,stroke:#333,stroke-width:2px
```

## Proposed Refactored Architecture

```mermaid
graph TD
    A[Main Application] --> B[Qt Interface<br/>interface/qt/app.py<br/>(35,291 chars)]
    
    B --> C[Edit Folders Dialog<br/>(UI Layer)]
    C --> D[Shared Business Logic<br/>(interface/operations/folder_manager.py)]
    D --> E[Validation Service<br/>(interface/validation/folder_settings_validator.py)]
    D --> F[Data Extraction Service<br/>(interface/operations/folder_data_extractor.py)]
    D --> G[Folder Configuration Model<br/>(interface/models/folder_configuration.py)]
    
    A --> H[Dispatch System<br/>dispatch/orchestrator.py<br/>(22,068 chars)]
    
    H --> I[Converter Step<br/>(Modular)]
    I --> J[Convert Backends<br/>(With Base Class)]
    J --> K[BaseConvertBackend<br/>(Shared Logic)]
    K --> L[convert_to_price()]
    K --> M[File I/O Handling]
    K --> N[Date/Time Utils]
    
    J --> O[CSVConverter<br/>convert_to_csv.py<br/>(Simplified)]
    J --> P[SimplifiedCSVConverter<br/>convert_to_simplified_csv.py<br/>(Simplified)]
    J --> Q[EStoreConverter<br/>convert_to_estore_einvoice.py<br/>(Simplified)]
    J --> R[CustomConverters<br/>(Specific Logic)]
    
    H --> S[Core Services]
    S --> T[Database Abstraction<br/>(modern interface)]
    S --> U[EDI Parsing<br/>(core/edi/)]
    S --> V[Utils Modules<br/>(Logical Organization)]
    V --> W[utils/edi<br/>(EDI-specific)]
    V --> X[utils/database<br/>(Database-specific)]
    V --> Y[utils/files<br/>(File operations)]
    V --> Z[utils/validators<br/>(Validation helpers)]
    
    style K fill:#6f6,stroke:#333,stroke-width:2px
    style D fill:#6f6,stroke:#333,stroke-width:2px
    style G fill:#6f6,stroke:#333,stroke-width:2px
```

## Refactoring Priority Zones

```mermaid
graph TD
    A[High Priority<br/>(Critical)] --> B[Convert Backend Duplication<br/>(6+ files)]
    A --> C[UI Layer Duplication<br/>(Tkinter/Qt)]
    A --> D[Large Dialog Files<br/>(75K+ chars)]
    A --> E[Utils Module Bloat<br/>(785 lines)]
    
    F[Medium Priority<br/>(Important)] --> G[Orchestrator Complexity<br/>(22,000 chars)]
    F --> H[Pipeline Modularity<br/>(Improve interfaces)]
    F --> I[Validation Logic<br/>(Decomposition)]
    F --> J[File Services<br/>(Consolidation)]
    
    K[Low Priority<br/>(Optional)] --> L[Legacy Code Removal<br/>(Deprecated modules)]
    K --> M[Design Pattern Modernization<br/>(Outdated practices)]
    K --> N[Error Handling<br/>(Consistency)]
    
    style A fill:#f00,stroke:#333,stroke-width:2px,color:#fff
    style B fill:#f66,stroke:#333,stroke-width:2px
    style C fill:#f66,stroke:#333,stroke-width:2px
    style D fill:#f66,stroke:#333,stroke-width:2px
    style E fill:#f66,stroke:#333,stroke-width:2px
    style F fill:#ff6,stroke:#333,stroke-width:2px
    style G fill:#ff6,stroke:#333,stroke-width:2px
    style H fill:#ff6,stroke:#333,stroke-width:2px
    style I fill:#ff6,stroke:#333,stroke-width:2px
    style J fill:#ff6,stroke:#333,stroke-width:2px
    style K fill:#6f6,stroke:#333,stroke-width:2px
    style L fill:#6f6,stroke:#333,stroke-width:2px
    style M fill:#6f6,stroke:#333,stroke-width:2px
    style N fill:#6f6,stroke:#333,stroke-width:2px
```

## Files by Complexity

```mermaid
graph TD
    A[>50,000 chars] --> B[interface/ui/dialogs/edit_folders_dialog.py<br/>(75,218)]
    A --> C[interface/qt/dialogs/edit_folders_dialog.py<br/>(58,539)]
    
    D[30,000-50,000 chars] --> E[interface/app.py<br/>(43,213)]
    
    F[20,000-30,000 chars] --> G[dispatch/orchestrator.py<br/>(22,068)]
    
    H[10,000-20,000 chars] --> I[dispatch/pipeline/splitter.py<br/>(17,205)]
    H --> J[dispatch/services/file_processor.py<br/>(17,706)]
    H --> K[interface/qt/app.py<br/>(35,291)]
    H --> L[convert_to_estore_einvoice_generic.py<br/>(14,426)]
    H --> M[interface/services/reporting_service.py<br/>(16,222)]
    H --> N[dispatch/processed_files_tracker.py<br/>(15,491)]
    H --> O[interface/operations/folder_data_extractor.py<br/>(8,736)]
    
    I[<10,000 chars] --> P[convert_to_scansheet_type_a.py<br/>(9,452)]
    I --> Q[convert_to_estore_einvoice.py<br/>(9,897)]
    I --> R[convert_to_jolley_custom.py<br/>(12,379)]
    I --> S[convert_to_stewarts_custom.py<br/>(12,099)]
    
    style B fill:#f00,stroke:#333,stroke-width:2px,color:#fff
    style C fill:#f00,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#f66,stroke:#333,stroke-width:2px
    style G fill:#f66,stroke:#333,stroke-width:2px
```

The diagrams above provide a visual representation of the current architecture, highlighting areas with code duplication, complex files, and architectural inconsistencies. The proposed refactored architecture shows how shared logic can be centralized and the codebase can be modularized for better maintainability and testability.
