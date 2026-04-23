import os
import sys

# Ensure imports from legacy worktree first
legacy_path = os.path.abspath(".swarm/worktrees/estore-einvoice-regression")
if legacy_path not in sys.path:
    sys.path.insert(0, legacy_path)

# Project root for modern imports
proj_root = os.path.abspath(".")
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

# Paths
input_path = os.path.abspath("tests/_tmp/sample_input.edi")
legacy_out = os.path.abspath("tests/_tmp/legacy_output.edi")
modern_out = os.path.abspath("tests/_tmp/modern_output.edi")

# Create sample input if not exists
if not os.path.exists(input_path):
    with open(input_path, "w", encoding="utf-8", newline="\n") as f:
        # A record: record_type (1) + cust_vendor(6) + invoice_number(10) + invoice_date(6) + invoice_total(10)
        f.write("A" + "CUST01" + "0000000001" + "010126" + "0000012345" + "\n")
        # B record: upc_number(11) desc(25) vendor_item(6) unit_cost(6) combo(2) unit_mult(6) qty(5) srp(5) pm(3) parent(6)
        f.write(
            "B"
            + "12345678901"
            + "Sample Description      "
            + "000123"
            + "00"
            + "000001"
            + "00010"
            + "001234"
            + "000"
            + "PARENT"
            + "\n"
        )
        # Another B
        f.write(
            "B"
            + "          "
            + "Another Item           "
            + "000200"
            + "00"
            + "000001"
            + "00002"
            + "000500"
            + "000"
            + "      "
            + "\n"
        )
        # C record
        f.write("C" + "TAX" + "TabSales Tax            " + "000000100" + "\n")

import importlib
import sys

# Provide a dummy query_runner module to avoid pyodbc dependency in the legacy
# worktree. The legacy worktree modules import `query_runner` at top-level and
# that module depends on pyodbc which may not be available in this environment.
import types

if "query_runner" not in sys.modules:
    fake_qr = types.ModuleType("query_runner")

    class query_runner:
        def __init__(self, *a, **kw):
            pass

        def run_arbitrary_query(self, query_string):
            return []

    fake_qr.query_runner = query_runner
    sys.modules["query_runner"] = fake_qr

# Legacy: import edi_tweaks from worktree
legacy = importlib.import_module("edi_tweaks")

settings = {
    # leave AS400 creds blank to avoid DB calls
}
# Legacy expects strings for boolean flags
params = {
    "pad_a_records": "False",
    "a_record_padding": "CUST",
    "a_record_padding_length": 6,
    "append_a_records": "False",
    "a_record_append_text": "",
    "invoice_date_custom_format": False,
    "invoice_date_custom_format_string": "%Y-%m-%d",
    "force_txt_file_ext": "False",
    "calculate_upc_check_digit": "False",
    "invoice_date_offset": 0,
    "retail_uom": False,
    "override_upc_bool": False,
    "override_upc_level": 1,
    "override_upc_category_filter": "ALL",
    "split_prepaid_sales_tax_crec": False,
}
upc = {1: ("CAT", "12345678901", "123456789012")}

legacy_result = legacy.edi_tweak(input_path, legacy_out, settings, params, upc)
print("legacy_result ->", legacy_result)

# Modern: import wrapper
modern = importlib.import_module("dispatch.converters.convert_to_tweaks")
# modern.edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lut)
modern_result = modern.edi_convert(input_path, modern_out, {}, params, upc)
print("modern_result ->", modern_result)

# Read bytes
with open(legacy_result, "rb") as f:
    legacy_bytes = f.read()
with open(modern_result, "rb") as f:
    modern_bytes = f.read()

# Write hex dumps for debugging
with open("tests/_tmp/legacy.hex", "wb") as f:
    f.write(legacy_bytes)
with open("tests/_tmp/modern.hex", "wb") as f:
    f.write(modern_bytes)

# Byte-for-byte compare
if legacy_bytes == modern_bytes:
    print("MATCH")
    sys.exit(0)
else:
    # show simple diff
    import difflib

    legacy_lines = legacy_bytes.decode("utf-8", errors="replace").splitlines(
        keepends=True
    )
    modern_lines = modern_bytes.decode("utf-8", errors="replace").splitlines(
        keepends=True
    )
    for i, line in enumerate(
        difflib.unified_diff(
            legacy_lines, modern_lines, fromfile="legacy", tofile="modern"
        )
    ):
        sys.stdout.write(line)
    sys.exit(2)
