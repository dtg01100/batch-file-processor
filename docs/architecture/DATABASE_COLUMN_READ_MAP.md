# DEFINITIVE DATABASE COLUMN READ MAP
## Batch File Processor Application

---

## Table: `folders`

### REQUIRED (app crashes/misbehaves if absent or None):
- **folder_name** — used in dispatch/orchestrator.py:45; defines the folder path that will be monitored for files
- **alias** — used in dispatch/orchestrator.py:47 (fallback display name); if missing, folder_name is used
- **folder_is_active** — used in interface/qt/run_coordinator.py:23, orchestrator.py; controls whether folder is processed
- **id** — used in dispatch/orchestrator.py:1058 (folder identifier for resend tracking); also **old_id** as fallback

### OPTIONAL (app provides defaults if absent):
- **process_edi** — orchestrator.py:849 (default: False); enables EDI processing pipeline
- **tweak_edi** — orchestrator.py:847 (default: False); enables EDI tweaking
- **split_edi** — orchestrator.py:761 (default: False); enables EDI splitting
- **split_edi_include_invoices** — dispatch/pipeline/splitter.py (default: True)
- **split_edi_include_credits** — dispatch/pipeline/splitter.py (default: True)
- **convert_to_format** — orchestrator.py:849 (default: "unknown"); specifies output conversion format
- **force_edi_validation** — orchestrator.py:762 (default: False); validates EDI before processing
- **rename_file** — orchestrator.py:1034 (default: ""); template for output file renaming
- **split_edi_filter_categories** — dispatch/pipeline/splitter.py (default: "ALL"); category filter for splitting
- **split_edi_filter_mode** — dispatch/pipeline/splitter.py (default: "include"); include/exclude mode
- **upc_target_length** — orchestrator.py:770 (default from _FOLDER_DEFAULTS); UPC digit count
- **upc_padding_pattern** — FolderConfiguration.from_dict():417 (default: "           "); UPC padding chars
- **override_upc_bool** — FolderConfiguration.from_dict():411 (default: False); enables UPC override
- **override_upc_level** — FolderConfiguration.from_dict():414 (default: 1); UPC override level
- **override_upc_category_filter** — FolderConfiguration.from_dict():415 (default: ""); UPC category filter
- **calculate_upc_check_digit** — FolderConfiguration.from_dict(); UPC check digit calculation
- **process_backend_copy** — orchestrator.py:776 (default: False); enables local file copy backend
- **copy_to_directory** — orchestrator.py:777 (default: "N/A"); destination for file copy
- **process_backend_ftp** — orchestrator.py:778 (default: False); enables FTP backend
- **ftp_server** — ftp_backend.py:68; FTP server hostname (REQUIRED if process_backend_ftp=True)
- **ftp_port** — ftp_backend.py:70; FTP server port (REQUIRED if process_backend_ftp=True)
- **ftp_username** — ftp_backend.py:75; FTP username (REQUIRED if process_backend_ftp=True)
- **ftp_password** — ftp_backend.py:76; FTP password (REQUIRED if process_backend_ftp=True)
- **ftp_folder** — ftp_backend.py:81; Remote FTP directory (REQUIRED if process_backend_ftp=True)
- **process_backend_email** — orchestrator.py:780 (default: False); enables email backend
- **email_to** — email_backend.py:67; recipient email addresses (REQUIRED if process_backend_email=True)
- **email_subject_line** — email_backend.py:57 (default: filename + " Attached"); email subject template
- **pad_a_records** — FolderConfiguration.from_dict():422 (default: False); enables A-record padding
- **a_record_padding** — FolderConfiguration.from_dict():423 (default: ""); padding character(s)
- **a_record_padding_length** — FolderConfiguration.from_dict():424 (default: 6); padding length
- **append_a_records** — FolderConfiguration.from_dict():426 (default: False); append text to A-records
- **a_record_append_text** — FolderConfiguration.from_dict():425 (default: ""); text to append
- **force_txt_file_ext** — FolderConfiguration.from_dict():427 (default: False); force .txt extension
- **invoice_date_offset** — FolderConfiguration.from_dict():432 (default: 0); days to offset invoice date
- **invoice_date_custom_format** — FolderConfiguration.from_dict():433 (default: False); custom date format
- **invoice_date_custom_format_string** — FolderConfiguration.from_dict():434 (default: ""); date format string
- **retail_uom** — FolderConfiguration.from_dict():435 (default: False); retail unit-of-measure flag
- **include_headers** — FolderConfiguration.from_dict():448 (default: False); include CSV headers
- **filter_ampersand** — FolderConfiguration.from_dict():449 (default: False); filter ampersands from CSV
- **include_item_numbers** — FolderConfiguration.from_dict():450 (default: False); include item numbers in CSV
- **include_item_description** — FolderConfiguration.from_dict():451 (default: False); include descriptions
- **simple_csv_sort_order** — FolderConfiguration.from_dict():452 (default: ""); CSV sort order
- **split_prepaid_sales_tax_crec** — FolderConfiguration.from_dict():453 (default: False); split tax handling
- **estore_store_number** — FolderConfiguration.from_dict():440 (default: ""); eStore configuration
- **estore_Vendor_OId** — FolderConfiguration.from_dict():441 (default: ""); eStore vendor OID
- **estore_vendor_NameVendorOID** — FolderConfiguration.from_dict():442 (default: ""); eStore vendor name
- **fintech_division_id** — FolderConfiguration.from_dict():443 (default: ""); Fintech division ID
- **plugin_configurations** — FolderConfiguration.from_dict():475 (default: {}); JSON format plugin configs

### NOT FULLY UTILIZED (schema defines but code doesn't fully read):
- **reporting_email**, **report_email_destination** — defined in schema but read logic incomplete
- **process_edi_output**, **edi_output_folder** — defined but not yet fully implemented
- **edi_format** — added in migration v38, minimal usage in current code
- **created_at**, **updated_at** — timestamp fields, auto-managed by DB
- **estore_c_record_OID** — in schema but not accessed in FolderConfiguration.from_dict()
- **filename**, **original_path**, **processed_path**, **status**, **error_message**, **convert_format**, **sent_to** — misplaced; these belong in processed_files table

---

## Table: `settings`

### REQUIRED (app crashes if missing when feature enabled):
- **email_address** — email_backend.py:73; sender email address (REQUIRED if sending emails)
- **email_smtp_server** — email_backend.py:101; SMTP server hostname (REQUIRED if sending emails)
- **smtp_port** — email_backend.py:101; SMTP port as integer (REQUIRED if sending emails)

### OPTIONAL (app has fallbacks/defaults):
- **enable_email** — run_coordinator.py:113 (normalized to boolean); master email toggle
- **email_username** — email_backend.py:107 (default: ""); SMTP authentication username
- **email_password** — email_backend.py:108 (default: ""); SMTP authentication password
- **enable_reporting** — run_coordinator.py:113 (normalized); enables run report emails
- **enable_interval_backups** — run_coordinator.py:51 (checked); periodic backup trigger
- **backup_counter** — run_coordinator.py:52, 57 (checked/incremented); counts runs for backups
- **backup_counter_maximum** — run_coordinator.py:53 (checked); threshold for auto-backup

### NOT CURRENTLY USED (legacy fields in schema):
- **odbc_driver** — REMOVED; ODBC connection no longer used
- **as400_address**, **as400_username**, **as400_password** — used with SSH/db2ssh tunnel for DB2 connections (not legacy)
- **folder_is_active**, **copy_to_directory**, **convert_to_format**, **process_edi**, etc. — these are folder-level settings, not global settings
- **created_at**, **updated_at** — timestamp fields

---

## Table: `processed_files`

### ACTUALLY READ BY APPLICATION:
- **id** — orchestrator.py:1078; internal record identifier for tracking
- **file_checksum** — orchestrator.py:1070; MD5/SHA checksum to detect duplicate processing
- **resend_flag** — orchestrator.py:1070, 1078; indicates file marked for reprocessing
- **folder_id** — implicit in queries; links file to originating folder

### LEGACY/SUPPLEMENTARY (minimal usage):
- **file_name**, **folder_alias** — old tracking fields, superseded by filename/folder_id
- **md5** — legacy checksum field (file_checksum is preferred)
- **created_at**, **processed_at** — timestamp tracking
- **filename**, **original_path**, **processed_path**, **status**, **error_message**, **convert_format**, **sent_to**, **invoice_numbers** — newer fields added v34+; not heavily utilized yet

---

## Table: `administrative` (DEPRECATED)

**STATUS: LEGACY/DEPRECATED** — This table duplicates the `folders` table. As of migration v37, it is marked as deprecated. The application should NOT be reading from this table; all operations should use the `folders` table exclusively.

All columns in `administrative` mirror those in `folders` and should be considered deprecated.

---

## SCHEMA VERSION COMPATIBILITY

**Current Expected Version:** v32 or later (v40+ recommended for full feature support)

### Recent Migration Milestones:
- **v34** — Added filename, original_path, processed_path, status, error_message fields to processed_files
- **v35** — Added performance indexes
- **v38** — Added edi_format column
- **v39** — Rebuilt tables with proper PRIMARY KEY constraints
- **v40** — Consolidated backend columns across tables
- **v41+** — Further refinements and additions

### Fields Present in v32 Schema:

**folders:** folder_name, alias, folder_is_active, copy_to_directory, process_edi, convert_to_format, calculate_upc_check_digit, upc_target_length, upc_padding_pattern, include_a_records, include_c_records, include_headers, filter_ampersand, tweak_edi, pad_a_records, a_record_padding, a_record_padding_length, invoice_date_custom_format_string, invoice_date_custom_format, reporting_email, report_email_destination, process_backend_copy, backend_copy_destination, process_backend_email, process_backend_ftp, email_to, email_subject_line, ftp_server, ftp_port, ftp_folder, ftp_username, ftp_password, process_edi_output, edi_output_folder, split_edi, force_edi_validation, append_a_records, a_record_append_text, force_txt_file_ext, invoice_date_offset, retail_uom, force_each_upc, include_item_numbers, include_item_description, simple_csv_sort_order, split_prepaid_sales_tax_crec, estore_store_number, estore_Vendor_OId, estore_vendor_NameVendorOID, prepend_date_files, rename_file, estore_c_record_OID, override_upc_bool, override_upc_level, override_upc_category_filter, split_edi_include_invoices, split_edi_include_credits, fintech_division_id, split_edi_filter_categories, split_edi_filter_mode, plugin_config/plugin_configurations, created_at, updated_at

**settings:** id, enable_email, email_address, email_username, email_password, email_smtp_server, smtp_port, as400_address, as400_username, as400_password, backup_counter, backup_counter_maximum, enable_interval_backups, folder_is_active, copy_to_directory, convert_to_format, process_edi, calculate_upc_check_digit, upc_target_length, upc_padding_pattern, include_a_records, include_c_records, include_headers, filter_ampersand, tweak_edi, pad_a_records, a_record_padding, a_record_padding_length, invoice_date_custom_format_string, invoice_date_custom_format, reporting_email, folder_name, alias, report_email_destination, process_backend_copy, backend_copy_destination, process_edi_output, edi_output_folder, created_at, updated_at

**processed_files:** id, file_name, folder_alias, md5, file_checksum, resend_flag, folder_id, created_at, processed_at, filename, original_path, processed_path, status, error_message, convert_format, sent_to, invoice_numbers

**administrative:** (mirrors folders with same 60+ columns)

---

## CRITICAL FINDINGS

### ⚠️ Schema Issues in Current Definition:

1. **Misplaced Columns in `folders`**: The columns `filename`, `original_path`, `processed_path`, `status`, `error_message`, `convert_format`, `sent_to` are defined in schema.py for the `folders` table but should only be in `processed_files`. This is a schema error.

2. **Settings Table Duplication**: Many folder-level settings are defined in the `settings` table (copy_to_directory, convert_to_format, process_edi, etc.) but are actually folder-specific. These should NOT be in the global settings table.

3. **Legacy AS/400 Fields**: odbc_driver was removed; as400_address, as400_username, as400_password are now used with SSH/db2ssh tunnel for DB2 connections.

4. **Administrative Table**: Confirmed as deprecated by migration v37. Code should not read from it.

### ⚠️ FolderConfiguration.from_dict() Field Mismatch:

The FolderConfiguration.from_dict() method (interface/models/folder_configuration.py:355) reads these columns that ARE accessed:
- All those listed in the REQUIRED and OPTIONAL sections above

These columns are NOT read by from_dict() but ARE in the schema:
- reporting_email, report_email_destination, process_edi_output, edi_output_folder, estore_c_record_OID

### ⚠️ Email Backend Requirements:

If a folder has `process_backend_email=True`, these columns are REQUIRED (no defaults):
- email_to
- email_smtp_server (from settings)
- smtp_port (from settings)  
- email_address (from settings)

Absence of these will cause runtime exception in email_backend.py

### ⚠️ FTP Backend Requirements:

If a folder has `process_backend_ftp=True`, these columns are REQUIRED (no defaults):
- ftp_server
- ftp_port
- ftp_username
- ftp_password
- ftp_folder

Absence of these will cause runtime exception in ftp_backend.py

