"""Constants for the batch file processor application."""

from datetime import datetime

# Application version - single source of truth
APP_VERSION = "(Git Branch: Master)"

# Database version - this is the single source of truth for the current
# database schema version
# Update this when adding new database migrations
CURRENT_DATABASE_VERSION = "50"

# Backend timeout constants (seconds)
SMTP_TIMEOUT_SECONDS = 30
FTP_TIMEOUT_SECONDS = 30
HASH_CALC_MAX_RETRIES = 5

# Date boundary constants for legacy date handling
MIN_DATE = datetime(1900, 1, 1)
MAX_DATE = datetime(9999, 12, 31)

# EDI field sentinel values
EMPTY_DATE_MMDDYY = "000000"
EMPTY_PARENT_ITEM = "000000"

# UPC padding pattern for EDI files (11 spaces)
UPC_PADDING_PATTERN = " " * 11

# EDI record minimum lengths
EDI_A_RECORD_MIN_LENGTH = 33
EDI_B_RECORD_MIN_LENGTH = 50
EDI_C_RECORD_MIN_LENGTH = 38

# EDI B-record standard lengths
EDI_B_RECORD_STANDARD_LENGTH = 76
EDI_B_RECORD_NO_PRICING_LENGTH = 70

# UPC/GTIN standard lengths
UPCE_SHORT_LENGTH = 6     # UPC-E middle digits (no check digit)
UPCE_7_DIGIT_LENGTH = 7   # UPC-E with 7 digits
UPCE_LENGTH = 8           # Full UPC-E
UPC_A_NO_CHECK_LENGTH = 11  # UPC-A without check digit
UPC_A_LENGTH = 12         # Full UPC-A with check digit
GTIN13_LENGTH = 13        # GTIN-13 (EAN-13)

# Price decimal places
PRICE_DECIMAL_PLACES = 2

# Barcode batch save interval (number of records between intermediate saves)
BARCODE_BATCH_SAVE_INTERVAL = 100

# Default folder configuration values for processing.
# These mirror the defaults applied when opening the edit dialog.
# Note: process_backend_* fields default to False so missing/NULL DB values
# don't raise KeyError when accessed via direct dict key.
FOLDER_DEFAULTS: dict = {
    "ftp_port": 21,
    "a_record_padding": "",
    "a_record_padding_length": 6,
    "a_record_append_text": "",
    "invoice_date_offset": 0,
    "invoice_date_custom_format": False,
    "invoice_date_custom_format_string": "%Y%m%d",
    "override_upc_level": 1,
    "override_upc_category_filter": "",
    "upc_target_length": 11,
    "upc_padding_pattern": UPC_PADDING_PATTERN,
    "simple_csv_sort_order": "",
    "split_edi_filter_categories": "ALL",
    "split_edi_filter_mode": "include",
    "rename_file": "",
    "convert_to_format": "",
    "estore_store_number": "",
    "estore_Vendor_OId": "",
    "estore_vendor_NameVendorOID": "",
    "estore_c_record_OID": "",
    "fintech_division_id": "",
    "pad_a_records": False,
    "append_a_records": False,
    "force_txt_file_ext": False,
    "calculate_upc_check_digit": False,
    "retail_uom": False,
    "override_upc_bool": False,
    "split_prepaid_sales_tax_crec": False,
    "process_backend_http": False,
    "http_url": "",
    "http_headers": "",
    "http_field_name": "",
    "http_auth_type": "",
    "http_api_key": "",
    "email_subject_line": "",
    "process_edi_output": False,
    "edi_output_folder": "",
}
