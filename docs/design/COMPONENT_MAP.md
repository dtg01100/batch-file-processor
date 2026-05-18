# Component Map

**Version:** 1.1  
**Date:** 2026-05-18  
**Status:** CORRECTED

---

## 1. Overview

This document maps all modules to their responsibilities and dependencies. **Updated to reflect actual codebase structure.**

## 2. Interface Layer (interface/)

### 2.1 Qt Components

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| QtBatchFileSenderApp | `qt/app.py` | Main application window |
| EditFoldersDialog | `qt/dialogs/edit_folders_dialog.py` | Folder configuration dialog |
| EditSettingsDialog | `qt/dialogs/edit_settings_dialog.py` | Global settings dialog |
| MaintenanceDialog | `qt/dialogs/maintenance_dialog.py` | Maintenance operations |
| ResendDialog | `qt/dialogs/resend_dialog.py` | Resend failed files |
| DatabaseImportDialog | `qt/dialogs/database_import_dialog.py` | Import legacy database |
| ProcessedFilesDialog | `qt/dialogs/processed_files_dialog.py` | View processed files |
| FolderListWidget | `qt/widgets/folder_list_widget.py` | Folder list display |
| SearchWidget | `qt/widgets/search_widget.py` | Search functionality |
| QtAppBootstrapService | `qt/bootstrap.py` | Service initialization |
| QtMainWindowController | `qt/window_controller.py` | Window lifecycle |
| QtRunCoordinator | `qt/run_coordinator.py` | Processing coordination |
| QtDiagnosticsService | `qt/diagnostics.py` | Diagnostics utilities |
| Theme | `qt/theme.py` | Application styling |
| QtServices | `qt/services/qt_services.py` | Qt service layer |

### 2.2 Operations

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| FolderManager | `operations/folder_manager.py` | Folder CRUD operations |
| FolderDataExtractor | `operations/folder_data_extractor.py` | Extract folder config |
| MaintenanceFunctions | `operations/maintenance_functions.py` | Maintenance tasks |
| PluginConfigurationMapper | `operations/plugin_configuration_mapper.py` | Plugin config mapping |
| ProcessedFiles | `operations/processed_files.py` | Processed file tracking |
| TweaksFlatColumnSync | `operations/tweaks_flat_column_sync.py` | Tweak sync logic |

### 2.3 Form System

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| FormGenerator | `form/form_generator.py` | Dynamic form generation |
| SectionFactory | `form/section_factory.py` | Form section creation |
| ConfigSectionWidgets | `form/config_section_widgets.py` | Section-specific widgets |

### 2.4 Plugins

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| PluginManager | `plugins/plugin_manager.py` | Plugin discovery/loading |
| ConfigurationPlugin | `plugins/configuration_plugin.py` | Base configuration interface |
| BaseSimpleConfigurationPlugin | `plugins/base_simple_configuration_plugin.py` | Simple plugin base |
| PluginBase | `plugins/plugin_base.py` | Plugin base class |
| SectionRegistry | `plugins/section_registry.py` | Section type registry |
| PluginConfig | `plugins/plugin_config.py` | Plugin configuration |
| ConfigSchemas | `plugins/config_schemas.py` | Configuration schemas |
| ValidationFramework | `plugins/validation_framework.py` | Validation utilities |
| UIAbstraction | `plugins/ui_abstraction.py` | UI abstraction layer |
| **Format Plugins** | | |
| ScannerwareConfigurationPlugin | `plugins/scannerware_configuration_plugin.py` | Scannerware config |
| CSVConfigurationPlugin | `plugins/csv_configuration_plugin.py` | CSV config |
| EstoreEinvoiceConfigurationPlugin | `plugins/estore_einvoice_configuration_plugin.py` | eStore config |
| EstoreEinvoiceGenericConfigurationPlugin | `plugins/estore_einvoice_generic_configuration_plugin.py` | Generic eStore |
| FintechConfigurationPlugin | `plugins/fintech_configuration_plugin.py` | FinTech config |
| JolleyCustomConfigurationPlugin | `plugins/jolley_custom_configuration_plugin.py` | Jolley config |
| ScansheetTypeAConfigurationPlugin | `plugins/scansheet_type_a_configuration_plugin.py` | Scansheet config |
| SimplifiedCSVConfigurationPlugin | `plugins/simplified_csv_configuration_plugin.py` | Simplified CSV |
| StewartsCustomConfigurationPlugin | `plugins/stewarts_custom_configuration_plugin.py` | Stewart's config |
| TweaksConfigurationPlugin | `plugins/tweaks_configuration_plugin.py` | Tweaks config |
| YellowdogCSVConfigurationPlugin | `plugins/yellowdog_csv_configuration_plugin.py` | YellowDog config |

### 2.5 Services

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| ReportingService | `services/reporting_service.py` | Email reports |
| ResendService | `services/resend_service.py` | File resend logic |
| SMTPSService | `services/smtp_service.py` | Email sending |
| FTPService | `services/ftp_service.py` | FTP operations |
| ProgressService | `services/progress_service.py` | Progress tracking |

### 2.6 Validation

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| FolderSettingsValidator | `validation/folder_settings_validator.py` | Folder validation |
| EmailValidator | `validation/email_validator.py` | Email validation |

## 3. Dispatch Layer (dispatch/)

### 3.1 Orchestration

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| DispatchOrchestrator | `orchestrator.py` | Main processing coordinator |
| SendManager | `send_manager.py` | Backend dispatch |
| ErrorHandler | `error_handler.py` | Error recording/reporting |
| ErrorLogger | `error_handler.py` | Legacy error logging |
| LogSender | `log_sender.py` | Email error reports |
| PrintService | `print_service.py` | Print configuration |
| PreflightValidator | `preflight_validator.py` | Pre-flight validation |
| ProcessedFilesTracker | `processed_files_tracker.py` | File tracking |
| FileResult | `services/file_processor.py` | Processing result type |
| DispatchConfig | `results.py` | Dispatch configuration |

### 3.2 Pipeline

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| PipelineFactory | `pipeline/factory.py` | Pipeline construction |
| ValidatorStep | `pipeline/validator.py` | EDI validation |
| SplitterStep | `pipeline/splitter.py` | EDI splitting |
| ConverterStep | `pipeline/converter.py` | Format conversion |
| PipelineStep (Protocol) | `pipeline/interfaces.py` | Step interface |
| ErrorRecordingMixin | `pipeline/interfaces.py` | Error recording mixin |

### 3.3 Services

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| FileProcessor | `services/file_processor.py` | Per-file processing |
| FolderProcessor | `services/folder_processor.py` | Per-folder processing |
| FolderDiscoveryService | `services/folder_discovery.py` | File discovery |
| FileFilter | `services/file_filter.py` | Deduplication |
| ProgressReporter | `services/progress_reporter.py` | Progress updates |
| ProgressReportingService | `services/progress_reporting.py` | Progress service |
| CustomerLookupService | `services/customer_lookup_service.py` | Customer lookup |
| UPCService | `services/upc_service.py` | UPC/barcode lookup |
| UOMLookupService | `services/uom_lookup_service.py` | UOM lookup |
| DatabaseConnector | `services/database_connector.py` | DB connection |
| ItemProcessing | `services/item_processing.py` | Item processing |

### 3.4 Converters

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| ConverterRegistry | `converters/registry.py` | Format registry |
| ConvertBase | `converters/convert_base.py` | Base converter class |
| CustomerQueries | `converters/customer_queries.py` | Customer lookup |
| CSVUtrs | `converters/csv_utils.py` | CSV utilities |
| Mixins | `converters/mixins.py` | Converter mixins |
| **Format Converters** | | |
| convert_to_scannerware | `converters/convert_to_scannerware.py` | Scannerware |
| convert_to_csv | `converters/convert_to_csv.py` | CSV |
| convert_to_simplified_csv | `converters/convert_to_simplified_csv.py` | Simplified CSV |
| convert_to_estore_einvoice | `converters/convert_to_estore_einvoice.py` | eStore eInvoice |
| convert_to_estore_einvoice_generic | `converters/convert_to_estore_einvoice_generic.py` | Generic eStore |
| convert_to_fintech | `converters/convert_to_fintech.py` | FinTech |
| convert_to_jolley_custom | `converters/convert_to_jolley_custom.py` | Jolley |
| convert_to_stewarts_custom | `converters/convert_to_stewarts_custom.py` | Stewart's |
| convert_to_tweaks | `converters/convert_to_tweaks.py` | Tweaks |
| convert_to_yellowdog_csv | `converters/convert_to_yellowdog_csv.py` | YellowDog CSV |
| convert_to_scansheet_type_a | `converters/convert_to_scansheet_type_a.py` | Scansheet |

### 3.5 Observability

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| AlertDispatcher | `observability/alert_dispatcher.py` | Alert dispatching |
| AlertQueue | `observability/alert_queue.py` | Alert queue |
| AuditLogger | `observability/audit_logger.py` | Audit logging |
| BackgroundWriter | `observability/background_writer.py` | Async writes |

## 4. Backend Layer (backend/)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| EmailBackend | `email_backend.py` | SMTP email sending |
| FTPBackend | `ftp_backend.py` | FTP/FTPS upload |
| CopyBackend | `copy_backend.py` | Local file copy |
| HTTPBackend | `http_backend.py` | HTTP POST upload |
| FTPClient | `ftp_client.py` | FTP protocol |
| SMTPClient | `smtp_client.py` | SMTP protocol |
| HTTPClient | `http_client.py` | HTTP protocol |
| FileOperations | `file_operations.py` | File system ops |
| Protocols | `protocols.py` | Backend interfaces |
| BackendBase | `backend_base.py` | Base backend class |
| **Database** | | |
| DatabaseObj | `database/database_obj.py` | Main DB class |
| Table (wrapper) | `database/database_obj.py` | Table wrapper |
| SQLiteWrapper | `database/sqlite_wrapper.py` | SQLite utilities |
| DatabaseObj_ | `database/database_obj.py` | DB object type |

## 5. Core Layer (core/)

### 5.1 EDI Processing

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| EDIParser | `edi/edi_parser.py` | EDI file parsing |
| EDISplitter | `edi/edi_splitter.py` | Transaction splitting |
| EDITweaker | `edi/edi_tweaker.py` | Field tweaks |
| EDIFormatParser | `edi/edi_format_parser.py` | Format parsing |
| EDITransformer | `edi/edi_transformer.py` | EDI transformation |
| EDISplittingUtils | `edi/edi_splitting_utils.py` | Splitting utilities |
| INVFetcher | `edi/inv_fetcher.py` | Invoice data fetch |
| POFetcher | `edi/po_fetcher.py` | PO data fetch |
| CREcGenerator | `edi/c_rec_generator.py` | C-record generation |
| UPCUtils | `edi/upc_utils.py` | UPC utilities |

### 5.2 Database

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| QueryRunner | `database/query_runner.py` | SQL execution |
| Schema | `database/schema.py` | Schema definitions |
| CRecordGenerator | `database/c_record_generator.py` | C-record gen |

### 5.3 Ports

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| IFolderRepository | `ports/repositories.py` | Folder repository interface |
| ISettingsRepository | `ports/repositories.py` | Settings repository interface |
| IProcessedFilesRepository | `ports/repositories.py` | Processed files interface |
| IEmailQueueRepository | `ports/repositories.py` | Email queue interface |

### 5.4 Utils

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| StructuredLogging | `utils/structured_logging.py` | Logging utilities |
| LoggingConfig | `utils/logging_config.py` | Logging configuration |
| DateUtils | `utils/date_utils.py` | Date formatting |
| FileUtils | `utils/file_utils.py` | File operations |
| FolderUtils | `utils/folder_utils.py` | Folder operations |
| CSVUtils | `utils/csv_utils.py` | CSV utilities |
| BoolUtils | `utils/bool_utils.py` | Boolean utilities |
| FormatUtils | `utils/format_utils.py` | Format utilities |
| SafeParse | `utils/safe_parse.py` | Safe parsing |
| TimingUtils | `utils/timing_utils.py` | Timing utilities |
| Utils | `utils/utils.py` | General utilities |

## 6. Adapters Layer (adapters/)

### 6.1 SQLite Repositories

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| SqliteFolderRepository | `sqlite/repositories/sqlite_folder_repo.py` | Folder access |
| SqliteSettingsRepository | `sqlite/repositories/sqlite_settings_repo.py` | Settings access |
| SqliteProcessedFilesRepository | `sqlite/repositories/sqlite_processed_files_repo.py` | Processed files |
| SqliteEmailQueueRepository | `sqlite/repositories/sqlite_email_queue_repo.py` | Email queue |

### 6.2 DB2 SSH Adapter (Future)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| DB2SSHConnection | `db2ssh/connection.py` | DB2 over SSH connection |

## 7. Dependency Summary

```
interface/
├── qt/          → dispatch/, backend/, core/
├── form/        → plugins/, qt/
├── plugins/     → operations/, database/, core/ports/
├── operations/  → database/ (DatabaseObj), dispatch/
├── services/    → backend/, database/
└── validation/  → core/

dispatch/
├── orchestrator.py → services/, pipeline/, backend/
├── send_manager.py → backend/
├── pipeline/ → converters/, core/edi/, core/ports/
└── services/ → core/edi/, core/utils/

backend/
├── *.py → core/utils/
└── database/ → core/

core/
├── edi/ → utils/
├── database/ → utils/
└── utils/ → (standalone)

adapters/
└── sqlite/ → backend/database/, core/ports/
```

## 8. Key Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| GUI Mode | `main_interface.py` | Full PyQt5 application |
| Automatic Mode | `main_interface.py -a` | Headless batch processing |
| Desktop Shortcut | `main_qt.py` | Entry point wrapper |

## 9. Related Documents

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture principles
- [DATA_FLOW.md](DATA_FLOW.md) - Data flow
- [DESIGN_CORRECTIONS.md](DESIGN_CORRECTIONS.md) - Correction history
