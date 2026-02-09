"""
Utils Package - Domain-specific utility modules.

This package provides organized utilities for the batch file processor,
split from the original monolithic utils.py file.

Modules:
- bool_utils: Boolean normalization and database conversion
- edi_utils: EDI record parsing and processing
- upc_utils: UPC/barcode calculation and conversion
- datetime_utils: Date/time conversion between formats
- database_utils: Database query and transformation utilities
- string_utils: String and price conversion utilities

Migration Guide:
- Old: import utils; utils.normalize_bool()
- New: from utils.bool_utils import normalize_bool
"""

# Legacy compatibility - import everything from old utils module for backward compatibility
import utils.bool_utils
import utils.edi_utils
import utils.upc_utils
import utils.datetime_utils
import utils.database_utils
import utils.string_utils

# Re-export all functions for backward compatibility
from utils.bool_utils import *
from utils.edi_utils import *
from utils.upc_utils import *
from utils.datetime_utils import *
from utils.database_utils import *
from utils.string_utils import *

# Maintain backward compatibility for classes
from utils.database_utils import invFetcher, cRecGenerator

__all__ = [
    # Boolean utilities
    'normalize_bool', 'to_db_bool', 'from_db_bool',
    
    # EDI utilities
    'capture_records', 'do_split_edi', 'detect_invoice_is_credit', '_get_default_parser',
    
    # UPC utilities
    'calc_check_digit', 'convert_UPCE_to_UPCA',
    
    # DateTime utilities
    'dactime_from_datetime', 'datetime_from_dactime', 'datetime_from_invtime', 'dactime_from_invtime',
    
    # Database utilities
    'invFetcher', 'cRecGenerator', 'apply_retail_uom_transform', 'apply_upc_override',
    
    # String utilities
    'dac_str_int_to_int', 'convert_to_price', 'do_clear_old_files',
]

# Legacy alias for import compatibility
HAS_QUERY_RUNNER = utils.bool_utils.HAS_QUERY_RUNNER
query_runner = utils.bool_utils.query_runner