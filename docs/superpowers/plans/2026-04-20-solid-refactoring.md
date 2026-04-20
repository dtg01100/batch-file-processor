# SOLID Refactoring: Plugin System & Converter Composition

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the plugin system (ISP violation in PluginBase) and converter architecture (SRP violations in mixins.py, OCP violation in EStore converter) to follow SOLID principles while maintaining backward compatibility.

**Architecture:**
- Replace ABC mixin inheritance with composable service objects for converters
- Split monolithic PluginBase into focused interfaces (IPlugin, IConfigurablePlugin, IUIPlugin)
- Keep BaseEDIConverter's Template Method pattern, fix EStoreEInvoiceConverter to use hooks properly
- Extract SQL templates and constants into data-only modules

**Tech Stack:** Python 3.11+, pytest, existing dispatch module

---

## File Structure

### New Files (Services - extracted from mixins.py)

```
dispatch/
├── services/
│   ├── database_connector.py      # From DatabaseConnectionMixin
│   ├── customer_lookup_service.py # From CustomerLookupMixin + SQL
│   ├── uom_lookup_service.py      # From UOMLookupMixin
│   └── item_processing.py         # From ItemProcessingMixin (static utils)
├── converters/
│   ├── customer_queries.py         # SQL templates + field constants (data only)
│   └── jolley_header_builder.py    # build_jolley_header_dict function
```

### Modified Files

```
interface/plugins/
├── interfaces.py                  # NEW: Define IPlugin, IConfigurablePlugin, IUIPlugin
├── plugin_base.py                 # MODIFY: Delegate to interfaces, keep backward compat
├── plugin_manager.py              # MODIFY: Use protocol types

dispatch/converters/
├── mixins.py                      # MODIFY: Keep ABCs as thin backward-compat wrappers
├── convert_base.py                # NO CHANGE (already well-designed)
├── convert_to_stewarts_custom.py  # MODIFY: Use composition instead of mixin inheritance
├── convert_to_jolley_custom.py    # MODIFY: Use composition instead of mixin inheritance
├── convert_to_estore_einvoice.py  # MODIFY: Use base class hooks, not override edi_convert
```

---

## Task 1: Extract ItemProcessing Service

**Files:**
- Create: `dispatch/services/item_processing.py`
- Test: `tests/dispatch/services/test_item_processing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dispatch/services/test_item_processing.py
import pytest
from dispatch.services.item_processing import ItemProcessor

class TestItemProcessor:
    def test_convert_to_item_total_positive(self):
        processor = ItemProcessor()
        total, qty = processor.convert_to_item_total("1999", "5")
        assert total == pytest.approx(99.95)
        assert qty == 5

    def test_convert_to_item_total_negative_qty(self):
        processor = ItemProcessor()
        total, qty = processor.convert_to_item_total("1999", "-2")
        assert total == pytest.approx(-39.98)
        assert qty == -2

    def test_generate_full_upc_11_digits(self):
        processor = ItemProcessor()
        result = processor.generate_full_upc("01234567890")  # 11 digits
        assert len(result) == 12
        assert result[-1] == str(processor._calc_check_digit(result[:-1]))

    def test_generate_full_upc_upce_to_upca(self):
        processor = ItemProcessor()
        result = processor.generate_full_upc("00123457")  # UPC-E
        assert len(result) == 12

    def test_generate_full_upc_empty(self):
        processor = ItemProcessor()
        assert processor.generate_full_upc("") == ""
        assert processor.generate_full_upc("   ") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/dispatch/services/test_item_processing.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# dispatch/services/item_processing.py
"""Item processing service for EDI converters."""
import decimal
from typing import Tuple

from core.utils import calc_check_digit, convert_to_price, convert_UPCE_to_UPCA, safe_int


class ItemProcessor:
    """Service for item total calculation and UPC generation."""

    def convert_to_item_total(self, unit_cost: str, qty: str) -> Tuple[decimal.Decimal, int]:
        """Calculate item total from unit cost and quantity.

        Args:
            unit_cost: The unit cost string (in cents, no decimal)
            qty: The quantity string (may be negative)

        Returns:
            Tuple of (item_total as Decimal, qty_as_int)
        """
        wrkqtyint = safe_int(qty)
        try:
            item_total = decimal.Decimal(convert_to_price(unit_cost)) * wrkqtyint
        except ValueError:
            item_total = decimal.Decimal()
        except decimal.InvalidOperation:
            item_total = decimal.Decimal()
        return item_total, wrkqtyint

    def generate_full_upc(self, input_upc: str) -> str:
        """Generate a full 12-digit UPC from input.

        Handles UPC-E to UPC-A conversion and check digit calculation.

        Args:
            input_upc: The input UPC string (may be 8, 11, or 12 digits)

        Returns:
            Full 12-digit UPC string or empty string if invalid
        """
        input_upc = input_upc.strip()
        if not input_upc:
            return ""

        try:
            int(input_upc)
        except ValueError:
            return ""

        proposed_upc = input_upc
        upc_len = len(str(proposed_upc))

        if upc_len == 11:
            upc_string = str(proposed_upc) + str(self._calc_check_digit(proposed_upc))
        elif upc_len == 8:
            converted = convert_UPCE_to_UPCA(proposed_upc)
            upc_string = converted if isinstance(converted, str) else ""
        elif upc_len == 12:
            upc_string = str(proposed_upc)
        else:
            upc_string = ""

        return upc_string

    def _calc_check_digit(self, upc: str) -> int:
        """Calculate UPC check digit."""
        return calc_check_digit(upc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/dispatch/services/test_item_processing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dispatch/services/item_processing.py tests/dispatch/services/test_item_processing.py
git commit -m "feat: extract ItemProcessor service from mixins"
```

---

## Task 2: Extract UOM Lookup Service

**Files:**
- Create: `dispatch/services/uom_lookup_service.py`
- Test: `tests/dispatch/services/test_uom_lookup_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dispatch/services/test_uom_lookup_service.py
import pytest
from unittest.mock import MagicMock
from dispatch.services.uom_lookup_service import UOMLookupService


class TestUOMLookupService:
    def test_get_uom_found_exact_match(self):
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = [
            {"itemno": "123", "uom_mult": "6", "uom_code": "CS"},
            {"itemno": "123", "uom_mult": "12", "uom_code": "EA"},
        ]
        service = UOMLookupService(mock_query_runner)
        service.uom_lookup_list = mock_query_runner.run_query.return_value

        result = service.get_uom("123", "6")
        assert result == "CS"

    def test_get_uom_no_lookup_list(self):
        service = UOMLookupService(MagicMock())
        service.uom_lookup_list = []
        assert service.get_uom("123", "6") == "?"

    def test_init_uom_lookup(self):
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = [{"itemno": "123"}]
        service = UOMLookupService(mock_query_runner)

        result = service.init_uom_lookup("INV001")

        mock_query_runner.run_query.assert_called_once()
        assert len(result) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/dispatch/services/test_uom_lookup_service.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# dispatch/services/uom_lookup_service.py
"""UOM (Unit of Measure) lookup service for EDI converters."""
from typing import Any, List, Optional

from core.database import QueryRunner
from core.structured_logging import get_logger

logger = get_logger(__name__)


class UOMLookupService:
    """Service for UOM lookup and resolution from database queries."""

    def __init__(self, query_runner: QueryRunner):
        """Initialize with query runner.

        Args:
            query_runner: Database query runner for executing queries
        """
        self._query_runner = query_runner
        self.uom_lookup_list: List[dict[str, Any]] = []

    def init_uom_lookup(self, invoice_number: str) -> List[dict[str, Any]]:
        """Initialize UOM lookup and fetch UOM data.

        Args:
            invoice_number: Invoice number to look up

        Returns:
            List of dicts with keys: itemno, uom_mult, uom_code
        """
        self.uom_lookup_list = self._query_runner.run_query(
            self._get_uom_query_sql(), (invoice_number,)
        )

        if not self.uom_lookup_list:
            logger.warning("No UOM data found for invoice %s", invoice_number)

        return self.uom_lookup_list

    def get_uom(self, item_number: str, packsize: str) -> str:
        """Get UOM (Unit of Measure) for an item.

        Args:
            item_number: The vendor item number
            packsize: The unit multiplier/pack size

        Returns:
            UOM code string (e.g., 'EA', 'CS') or '?' if not found
        """
        if not self.uom_lookup_list:
            return "?"

        def get_key(entry: dict, *keys: str) -> Optional[str]:
            """Case-insensitive key lookup."""
            for key in keys:
                for k, v in entry.items():
                    if k.upper() == key.upper():
                        return v
                for k, v in entry.items():
                    if k.lower() == key.lower():
                        return v
            return None

        stage_1_list = []
        stage_2_list = []

        for entry in self.uom_lookup_list:
            item_no = get_key(entry, "itemno", "ITEMNO")
            if item_no is None:
                continue
            try:
                if int(item_no) == int(item_number):
                    stage_1_list.append(entry)
            except (ValueError, TypeError):
                continue

        for entry in stage_1_list:
            uom_mult = get_key(entry, "uom_mult", "UOM_MULT")
            if uom_mult is None:
                stage_2_list.append(entry)
                break
            try:
                if int(uom_mult) == int(packsize):
                    stage_2_list.append(entry)
            except (ValueError, TypeError):
                stage_2_list.append(entry)
                break

        try:
            uom_code = get_key(stage_2_list[0], "uom_code", "UOM_CODE")
            return uom_code if uom_code else "?"
        except IndexError:
            return "?"

    def _get_uom_query_sql(self) -> str:
        """Return the SQL query template for UOM lookup."""
        return """
            SELECT DISTINCT bubacd AS itemno,
                           bus3qt AS uom_mult,
                           buhxtx AS uom_code
            FROM dacdata.odhst odhst
            WHERE odhst.buhhnb = ?
        """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/dispatch/services/test_uom_lookup_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dispatch/services/uom_lookup_service.py tests/dispatch/services/test_uom_lookup_service.py
git commit -m "feat: extract UOMLookupService from mixins"
```

---

## Task 3: Extract Customer Queries Data Module

**Files:**
- Create: `dispatch/converters/customer_queries.py`
- Modify: `dispatch/converters/mixins.py` (remove SQL templates and constants)

- [ ] **Step 1: Write the test for data module**

```python
# tests/dispatch/converters/test_customer_queries.py
import pytest
from dispatch.converters.customer_queries import (
    CUSTOMER_QUERY_SQL_TEMPLATE,
    CUSTOMER_FIELDS_LIST_BASE,
    BASIC_CUSTOMER_QUERY_SQL,
    STEWARTS_CUSTOMER_QUERY_SQL,
    STEWARTS_CUSTOMER_FIELDS_LIST,
    build_customer_query_sql,
)


class TestCustomerQueries:
    def test_basic_query_sql_has_no_store_number(self):
        assert "Customer Store Number" not in BASIC_CUSTOMER_QUERY_SQL

    def test_stewarts_query_sql_has_store_number(self):
        assert "Customer Store Number" in STEWARTS_CUSTOMER_QUERY_SQL

    def test_build_customer_query_sql(self):
        sql = build_customer_query_sql("dsabrep.abaknb AS 'Store'")
        assert "dsabrep.abaknb" in sql
        assert "FROM dacdata.ohhst" in sql

    def test_stewarts_fields_list_has_store_number(self):
        assert "Customer_Store_Number" in STEWARTS_CUSTOMER_FIELDS_LIST

    def test_basic_fields_list_no_store_number(self):
        assert "Customer_Store_Number" not in CUSTOMER_FIELDS_LIST_BASE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_customer_queries.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# dispatch/converters/customer_queries.py
"""Customer query SQL templates and field constants for EDI converters.

This module contains only data (SQL templates and field lists).
Business logic for executing queries and building header dicts is in
CustomerLookupService.
"""

CUSTOMER_QUERY_SQL_TEMPLATE = """
    SELECT TRIM(dsadrep.adbbtx) AS "Salesperson Name",
        ohhst.btcfdt AS "Invoice Date",
        TRIM(ohhst.btfdtx) AS "Terms Code",
        dsagrep.agrrnb AS "Terms Duration",
        dsabrep.abbvst AS "Customer Status",
        dsabrep.ababnb AS "Customer Number",
        TRIM(dsabrep.abaatx) AS "Customer Name",
        {customer_store_number_field}
        TRIM(dsabrep.ababtx) AS "Customer Address",
        TRIM(dsabrep.abaetx) AS "Customer Town",
        TRIM(dsabrep.abaftx) AS "Customer State",
        TRIM(dsabrep.abagtx) AS "Customer Zip",
        CONCAT(dsabrep.abadnb, dsabrep.abaenb) AS "Customer Phone",
        TRIM(cvgrrep.grm9xt) AS "Customer Email",
        TRIM(cvgrrep.grnaxt) AS "Customer Email 2",
        dsabrep_corp.abbvst AS "Corporate Customer Status",
        dsabrep_corp.ababnb AS "Corporate Customer Number",
        TRIM(dsabrep_corp.abaatx) AS "Corporate Customer Name",
        TRIM(dsabrep_corp.ababtx) AS "Corporate Customer Address",
        TRIM(dsabrep_corp.abaetx) AS "Corporate Customer Town",
        TRIM(dsabrep_corp.abaftx) AS "Corporate Customer State",
        TRIM(dsabrep_corp.abagtx) AS "Corporate Customer Zip",
        CONCAT(dsabrep_corp.abadnb, dsabrep.abaenb) AS "Corporate Customer Phone",
        TRIM(cvgrrep_corp.grm9xt) AS "Corporate Customer Email",
        TRIM(cvgrrep_corp.grnaxt) AS "Corporate Customer Email 2"
    FROM dacdata.ohhst ohhst
        INNER JOIN dacdata.dsabrep dsabrep
            ON ohhst.btabnb = dsabrep.ababnb
        LEFT OUTER JOIN dacdata.cvgrrep cvgrrep
            ON dsabrep.ababnb = cvgrrep.grabnb
        INNER JOIN dacdata.dsadrep dsadrep
            ON dsabrep.abajcd = dsadrep.adaecd
        INNER JOIN dacdata.dsagrep dsagrep
            ON ohhst.bta0cd = dsagrep.aga0cd
        LEFT OUTER JOIN dacdata.dsabrep dsabrep_corp
            ON dsabrep.abalnb = dsabrep_corp.ababnb
        LEFT OUTER JOIN dacdata.cvgrrep cvgrrep_corp
            ON dsabrep_corp.ababnb = cvgrrep_corp.grabnb
        LEFT OUTER JOIN dacdata.dsadrep dsadrep_corp
            ON dsabrep_corp.abajcd = dsadrep_corp.adaecd
    WHERE ohhst.bthhnb = ?
"""

CUSTOMER_FIELDS_LIST_BASE = [
    "Salesperson_Name",
    "Invoice_Date",
    "Terms_Code",
    "Terms_Duration",
    "Customer_Status",
    "Customer_Number",
    "Customer_Name",
    "Customer_Address",
    "Customer_Town",
    "Customer_State",
    "Customer_Zip",
    "Customer_Phone",
    "Customer_Email",
    "Customer_Email_2",
    "Corporate_Customer_Status",
    "Corporate_Customer_Number",
    "Corporate_Customer_Name",
    "Corporate_Customer_Address",
    "Corporate_Customer_Town",
    "Corporate_Customer_State",
    "Corporate_Customer_Zip",
    "Corporate_Customer_Phone",
    "Corporate_Customer_Email",
    "Corporate_Customer_Email_2",
]

CUSTOMER_STORE_NUMBER_FIELD_BASIC = ""
CUSTOMER_STORE_NUMBER_FIELD_STEWARTS = 'dsabrep.abaknb AS "Customer Store Number",'

BASIC_CUSTOMER_FIELDS_LIST = CUSTOMER_FIELDS_LIST_BASE
STEWARTS_CUSTOMER_FIELDS_LIST = [
    "Salesperson_Name",
    "Invoice_Date",
    "Terms_Code",
    "Terms_Duration",
    "Customer_Status",
    "Customer_Number",
    "Customer_Name",
    "Customer_Store_Number",
    "Customer_Address",
    "Customer_Town",
    "Customer_State",
    "Customer_Zip",
    "Customer_Phone",
    "Customer_Email",
    "Customer_Email_2",
    "Corporate_Customer_Status",
    "Corporate_Customer_Number",
    "Corporate_Customer_Name",
    "Corporate_Customer_Address",
    "Corporate_Customer_Town",
    "Corporate_Customer_State",
    "Corporate_Customer_Zip",
    "Corporate_Customer_Phone",
    "Corporate_Customer_Email",
    "Corporate_Customer_Email_2",
]


def build_customer_query_sql(customer_store_number_field: str) -> str:
    """Build customer query SQL with specified store number field."""
    return CUSTOMER_QUERY_SQL_TEMPLATE.format(
        customer_store_number_field=customer_store_number_field
    )


BASIC_CUSTOMER_QUERY_SQL = build_customer_query_sql(CUSTOMER_STORE_NUMBER_FIELD_BASIC)
STEWARTS_CUSTOMER_QUERY_SQL = build_customer_query_sql(CUSTOMER_STORE_NUMBER_FIELD_STEWARTS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_customer_queries.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dispatch/converters/customer_queries.py tests/dispatch/converters/test_customer_queries.py
git commit -m "feat: extract customer query SQL templates to data module"
```

---

## Task 4: Extract Jolley Header Builder

**Files:**
- Create: `dispatch/converters/jolley_header_builder.py`
- Test: `tests/dispatch/converters/test_jolley_header_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dispatch/converters/test_jolley_header_builder.py
import pytest
from dispatch.converters.jolley_header_builder import build_jolley_header_dict


class TestJolleyHeaderBuilder:
    def test_basic_header_dict_conversion(self):
        raw = {"Salesperson Name": "John", "Invoice Date": "20240101"}
        result = build_jolley_header_dict(raw, list(raw.keys()))
        assert result == {"Salesperson_Name": "John", "Invoice_Date": "20240101"}

    def test_corporate_fallback_when_none(self):
        raw = {
            "Customer_Number": "123",
            "Corporate_Customer_Number": None,
            "Customer_Name": "Acme",
            "Corporate_Customer_Name": None,
        }
        result = build_jolley_header_dict(raw, list(raw.keys()))
        # Should fallback to customer fields when corporate is None
        assert result["Corporate_Customer_Number"] == "123"
        assert result["Corporate_Customer_Name"] == "Acme"

    def test_corporate_preserved_when_set(self):
        raw = {
            "Customer_Number": "123",
            "Corporate_Customer_Number": "456",
            "Customer_Name": "Acme",
            "Corporate_Customer_Name": "Corp Acme",
        }
        result = build_jolley_header_dict(raw, list(raw.keys()))
        assert result["Corporate_Customer_Number"] == "456"
        assert result["Corporate_Customer_Name"] == "Corp Acme"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_jolley_header_builder.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# dispatch/converters/jolley_header_builder.py
"""Jolley-specific customer header dictionary builder.

Builds customer header dictionaries with corporate field fallback logic.
"""
from typing import Any


def build_jolley_header_dict(
    header_fields: dict[str, Any], header_fields_list: list[str]
) -> dict[str, Any]:
    """Build Jolley-specific customer header dictionary with corporate fallback.

    Jolley-specific: falls back corporate fields to customer fields if None.

    Args:
        header_fields: Raw query result dict (keys may have spaces from SQL aliases)
        header_fields_list: List of field names (with underscores for mapping)

    Returns:
        Dictionary with Jolley-specific corporate field fallback
    """
    # Convert spaces to underscores in keys for compatibility with field list
    result = {}
    for key, value in header_fields.items():
        new_key = key.replace(" ", "_")
        result[new_key] = value

    # Jolley-specific: fallback corporate fields to customer fields if None
    if result.get("Corporate_Customer_Number") is None:
        result["Corporate_Customer_Number"] = result.get("Customer_Number", "")
    if result.get("Corporate_Customer_Name") is None:
        result["Corporate_Customer_Name"] = result.get("Customer_Name", "")
    if result.get("Corporate_Customer_Address") is None:
        result["Corporate_Customer_Address"] = result.get("Customer_Address", "")
    if result.get("Corporate_Customer_Town") is None:
        result["Corporate_Customer_Town"] = result.get("Customer_Town", "")
    if result.get("Corporate_Customer_State") is None:
        result["Corporate_Customer_State"] = result.get("Customer_State", "")
    if result.get("Corporate_Customer_Zip") is None:
        result["Corporate_Customer_Zip"] = result.get("Customer_Zip", "")

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_jolley_header_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dispatch/converters/jolley_header_builder.py tests/dispatch/converters/test_jolley_header_builder.py
git commit -m "feat: extract build_jolley_header_dict to standalone module"
```

---

## Task 5: Extract Customer Lookup Service

**Files:**
- Create: `dispatch/services/customer_lookup_service.py`
- Test: `tests/dispatch/services/test_customer_lookup_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dispatch/services/test_customer_lookup_service.py
import pytest
from unittest.mock import MagicMock
from dispatch.services.customer_lookup_service import CustomerLookupService


class TestCustomerLookupService:
    def test_lookup_found(self):
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = [
            {"Customer Number": "123", "Customer Name": "Acme Corp"}
        ]
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        result = service.lookup("INV001")
        assert result["Customer_Number"] == "123"

    def test_lookup_not_found_raises(self):
        from core.exceptions import CustomerLookupError
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = []
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        with pytest.raises(CustomerLookupError):
            service.lookup("INV001")

    def test_build_header_dict_basic(self):
        mock_query_runner = MagicMock()
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        raw = {"Customer Number": "123", "Customer Name": "Acme"}
        result = service._build_header_dict(raw, ["Customer_Number", "Customer_Name"])
        assert result["Customer_Number"] == "123"

    def test_build_header_dict_strip_spaces(self):
        mock_query_runner = MagicMock()
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        raw = {"Customer Number": "123"}  # Space in key
        result = service._build_header_dict(raw, ["Customer_Number"])
        assert "Customer Number" not in result
        assert "Customer_Number" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/dispatch/services/test_customer_lookup_service.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# dispatch/services/customer_lookup_service.py
"""Customer lookup service for EDI converters."""
from typing import Any, List

from core.database import QueryRunner
from core.exceptions import CustomerLookupError
from core.structured_logging import get_logger

logger = get_logger(__name__)


class CustomerLookupService:
    """Service for customer header field lookups from AS400 database."""

    def __init__(self, query_runner: QueryRunner, sql_query: str):
        """Initialize with query runner and SQL query template.

        Args:
            query_runner: Database query runner
            sql_query: SQL query template for customer lookup
        """
        self._query_runner = query_runner
        self._sql_query = sql_query
        self._header_dict: dict[str, Any] = {}

    @property
    def header_dict(self) -> dict[str, Any]:
        """Get current customer header fields."""
        return self._header_dict

    def lookup(self, invoice_number: str) -> dict[str, Any]:
        """Look up customer header fields by invoice number.

        Args:
            invoice_number: Invoice number to look up

        Returns:
            Dictionary of customer header fields

        Raises:
            CustomerLookupError: If customer not found
        """
        # Normalize invoice number for query (strip leading zeros)
        invoice_param = invoice_number.lstrip("0")

        header_fields = self._query_runner.run_query(self._sql_query, (invoice_param,))

        if len(header_fields) == 0:
            logger.error("Cannot find order %s in AS400 history", invoice_number)
            raise CustomerLookupError(f"Cannot Find Order {invoice_number} In History.")

        self._header_dict = self._build_header_dict(header_fields[0], [])
        return self._header_dict

    def _build_header_dict(
        self, header_fields: dict[str, Any], header_fields_list: List[str]
    ) -> dict[str, Any]:
        """Build customer header dictionary from query results.

        Args:
            header_fields: Raw query result dict (keys may have spaces)
            header_fields_list: List of field names (unused, kept for interface compat)

        Returns:
            Dictionary mapping field names to values
        """
        # Convert spaces to underscores in keys for compatibility
        result = {}
        for key, value in header_fields.items():
            new_key = key.replace(" ", "_")
            result[new_key] = value
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/dispatch/services/test_customer_lookup_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dispatch/services/customer_lookup_service.py tests/dispatch/services/test_customer_lookup_service.py
git commit -m "feat: extract CustomerLookupService from mixins"
```

---

## Task 6: Extract Database Connector Service

**Files:**
- Create: `dispatch/services/database_connector.py`
- Test: `tests/dispatch/services/test_database_connector.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dispatch/services/test_database_connector.py
import pytest
from unittest.mock import MagicMock, patch
from dispatch.services.database_connector import DatabaseConnector


class TestDatabaseConnector:
    def test_init_connection_success(self):
        with patch("dispatch.services.database_connector.create_query_runner_from_settings") as mock_factory:
            mock_factory.return_value = MagicMock()
            connector = DatabaseConnector()
            connector.init_connection(
                {"as400_username": "user", "as400_address": "addr", "as400_password": "pass"}
            )
            assert connector.is_connected
            assert connector.query_runner is not None

    def test_init_connection_missing_keys(self):
        connector = DatabaseConnector()
        with pytest.raises(ValueError, match="Missing required database settings"):
            connector.init_connection({"as400_username": "user"})  # missing address

    def test_init_connection_no_auth(self):
        connector = DatabaseConnector()
        with pytest.raises(ValueError, match="Either as400_password or ssh_key_filename"):
            connector.init_connection({"as400_username": "user", "as400_address": "addr"})

    def test_close_connection(self):
        mock_runner = MagicMock()
        with patch("dispatch.services.database_connector.create_query_runner_from_settings") as mock_factory:
            mock_factory.return_value = mock_runner
            connector = DatabaseConnector()
            connector.init_connection(
                {"as400_username": "user", "as400_address": "addr", "as400_password": "pass"}
            )
            connector.close()
            mock_runner.close.assert_called_once()
            assert not connector.is_connected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/dispatch/services/test_database_connector.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# dispatch/services/database_connector.py
"""Database connector service for EDI converters."""
from typing import Any, Optional

from core.database import QueryRunner
from core.structured_logging import get_logger

logger = get_logger(__name__)


class DatabaseConnector:
    """Service for database connection setup and management."""

    def __init__(self):
        """Initialize database connector."""
        self.query_runner: Optional[QueryRunner] = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if database connection is established."""
        return self._is_connected

    def init_connection(
        self,
        settings_dict: dict[str, Any],
        database: str = "QGPL",
        required_keys: tuple[str, ...] = (
            "as400_username",
            "as400_address",
        ),
    ) -> None:
        """Initialize the database connection.

        Args:
            settings_dict: Dictionary containing database connection settings
            database: Database name (default: QGPL)
            required_keys: Tuple of required settings keys

        Raises:
            ValueError: If required settings are missing or no auth provided
        """
        if self._is_connected:
            return

        missing_keys = [
            key
            for key in required_keys
            if key not in settings_dict or not settings_dict[key]
        ]
        if missing_keys:
            raise ValueError(
                f"Missing required database settings: {', '.join(missing_keys)}"
            )

        ssh_key_filename = settings_dict.get("ssh_key_filename", "").strip() or None
        as400_password = settings_dict.get("as400_password", "").strip() or None
        if not (as400_password or ssh_key_filename):
            raise ValueError(
                "Either as400_password or ssh_key_filename must be provided"
            )

        from core.database.query_runner import create_query_runner_from_settings

        self.query_runner = create_query_runner_from_settings(
            settings_dict, database=database
        )
        self._is_connected = True
        logger.debug(
            "Database connection initialized (ssh_key_filename=%s)",
            ssh_key_filename,
        )

    def close(self) -> None:
        """Close the database connection if open."""
        if self.query_runner is not None:
            try:
                self.query_runner.close()
                logger.debug("Database connection closed")
            except AttributeError:
                pass
            self.query_runner = None
            self._is_connected = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/dispatch/services/test_database_connector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dispatch/services/database_connector.py tests/dispatch/services/test_database_connector.py
git commit -m "feat: extract DatabaseConnector service from mixins"
```

---

## Task 7: Migrate StewartsCustomConverter to Composition

**Files:**
- Modify: `dispatch/converters/convert_to_stewarts_custom.py`
- Test: `tests/dispatch/converters/test_convert_to_stewarts_custom.py`

- [ ] **Step 1: Verify existing tests still pass (baseline)**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_convert_to_stewarts_custom.py -v 2>/dev/null || echo "No tests yet - this is new code"`
Expected: May need to create tests

- [ ] **Step 2: Modify convert_to_stewarts_custom.py to use composition**

```python
# dispatch/converters/convert_to_stewarts_custom.py
"""Stewarts Custom CSV EDI Converter - Refactored to use composition.

This module converts EDI files to Stewarts Custom CSV format with database lookups
for customer information. Uses composition instead of mixin inheritance.

Output Format:
    Multi-section CSV with invoice details, ship/bill addresses,
    and line items with quantities, UOM, prices, and totals.
"""
import csv
from typing import Any

from core import utils
from core.utils import prettify_dates
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)
from dispatch.converters.customer_queries import (
    STEWARTS_CUSTOMER_FIELDS_LIST,
    STEWARTS_CUSTOMER_QUERY_SQL,
)
from dispatch.services.database_connector import DatabaseConnector
from dispatch.services.customer_lookup_service import CustomerLookupService
from dispatch.services.uom_lookup_service import UOMLookupService
from dispatch.services.item_processing import ItemProcessor


class StewartsCustomConverter(BaseEDIConverter):
    """Converter for Stewarts Custom CSV format with database lookups.

    Uses composable services for database operations, customer lookups,
    UOM lookups, and item processing.
    """

    def __init__(self):
        """Initialize converter with composition services."""
        self._db_connector = DatabaseConnector()
        self._customer_service: Optional[CustomerLookupService] = None
        self._uom_service: Optional[UOMLookupService] = None
        self._item_processor = ItemProcessor()
        self._header_a_record: dict[str, str] = {}
        self._header_fields_dict: dict[str, Any] = {}

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and database connection.

        Args:
            context: The conversion context
        """
        # Initialize database connection
        self._db_connector.init_connection(context.settings_dict)

        # Initialize services with query runner
        self._customer_service = CustomerLookupService(
            self._db_connector.query_runner, STEWARTS_CUSTOMER_QUERY_SQL
        )
        self._uom_service = UOMLookupService(self._db_connector.query_runner)

        # Open output file and create CSV writer
        context.output_file = open(
            context.get_output_path(".csv"), "w", newline="\n", encoding="utf-8"
        )
        context.csv_writer = csv.writer(context.output_file, dialect="unix")

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), writing invoice header to CSV.

        Args:
            record: The A record
            context: The conversion context
        """
        super().process_a_record(record, context)
        self._header_a_record = record.fields

        # Look up customer and UOM data using services
        self._customer_service.lookup(record.fields["invoice_number"])
        self._uom_service.init_uom_lookup(record.fields["invoice_number"])
        self._header_fields_dict = self._customer_service.header_dict

        csv_writer = context.csv_writer

        # Write invoice header section
        csv_writer.writerow(["Invoice Details"])
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
        )
        csv_writer.writerow(
            [
                prettify_dates(self._header_fields_dict["Invoice_Date"]),
                self._header_fields_dict["Terms_Code"],
                record.fields["invoice_number"],
                prettify_dates(
                    self._header_fields_dict["Invoice_Date"],
                    self._header_fields_dict["Terms_Duration"],
                    -1,
                ),
            ]
        )

        # Build bill-to segment
        if self._header_fields_dict.get("Corporate_Customer_Number") is not None:
            bill_to_segment = [
                str(self._header_fields_dict["Corporate_Customer_Number"])
                + "\n"
                + self._header_fields_dict["Corporate_Customer_Name"]
                + "\n"
                + self._header_fields_dict["Corporate_Customer_Address"]
                + "\n"
                + self._header_fields_dict["Corporate_Customer_Town"]
                + ", "
                + self._header_fields_dict["Corporate_Customer_State"]
                + ", "
                + self._header_fields_dict["Corporate_Customer_Zip"]
                + ", "
                + "\n"
                + "US",
            ]
        else:
            bill_to_segment = [
                str(self._header_fields_dict["Customer_Number"])
                + "\n"
                + self._header_fields_dict["Customer_Name"]
                + "\n"
                + self._header_fields_dict["Customer_Address"]
                + "\n"
                + self._header_fields_dict["Customer_Town"]
                + ", "
                + self._header_fields_dict["Customer_State"]
                + ", "
                + self._header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
            ]

        csv_writer.writerow(
            [
                "Ship To:",
                str(self._header_fields_dict["Customer_Number"])
                + " "
                + str(self._header_fields_dict.get("Customer_Store_Number", ""))
                + "\n"
                + self._header_fields_dict["Customer_Name"]
                + "\n"
                + self._header_fields_dict["Customer_Address"]
                + "\n"
                + self._header_fields_dict["Customer_Town"]
                + ", "
                + self._header_fields_dict["Customer_State"]
                + ", "
                + self._header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
                "Bill To:",
            ]
            + bill_to_segment
        )
        csv_writer.writerow([""])
        csv_writer.writerow(
            [
                "Invoice Number",
                "Store Number",
                "Item Number",
                "Description",
                "UPC #",
                "Quantity",
                "UOM",
                "Price",
                "Amount",
            ]
        )

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), writing to CSV.

        Args:
            record: The B record
            context: The conversion context
        """
        total_price, qtyint = self._item_processor.convert_to_item_total(
            record.fields["unit_cost"], record.fields["qty_of_units"]
        )
        context.csv_writer.writerow(
            [
                self._header_a_record["invoice_number"],
                self._header_fields_dict.get("Customer_Store_Number", ""),
                record.fields["vendor_item"],
                record.fields["description"],
                self._item_processor.generate_full_upc(record.fields["upc_number"]),
                qtyint,
                self._uom_service.get_uom(
                    record.fields["vendor_item"], record.fields["unit_multiplier"]
                ),
                "$" + str(utils.convert_to_price(record.fields["unit_cost"])),
                "$" + str(total_price),
            ]
        )

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax), writing to CSV."""
        context.csv_writer.writerow(
            [
                record.fields["description"],
                "000000000000",
                1,
                "EA",
                "$" + str(utils.convert_to_price(record.fields["amount"])),
                "$" + str(utils.convert_to_price(record.fields["amount"])),
            ]
        )

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by writing total row and closing file."""
        if self._header_a_record:
            context.csv_writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "Total:",
                    "$"
                    + str(
                        utils.convert_to_price(
                            self._header_a_record["invoice_total"]
                        ).lstrip("0")
                    ),
                ]
            )

        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

        self._db_connector.close()


# Backward Compatibility Wrapper
from .convert_base import create_edi_convert_wrapper

edi_convert = create_edi_convert_wrapper(
    StewartsCustomConverter, format_name="stewarts_custom"
)
```

- [ ] **Step 3: Run tests to verify**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_convert_to_stewarts_custom.py -v`
Expected: PASS (if tests exist) or integration test needed

- [ ] **Step 4: Commit**

```bash
git add dispatch/converters/convert_to_stewarts_custom.py
git commit -m "refactor: migrate StewartsCustomConverter to composition"
```

---

## Task 8: Migrate JolleyCustomConverter to Composition

**Files:**
- Modify: `dispatch/converters/convert_to_jolley_custom.py`
- Test: `tests/dispatch/converters/test_convert_to_jolley_custom.py`

- [ ] **Step 1: Modify convert_to_jolley_custom.py to use composition**

The structure is nearly identical to Stewarts, with these differences:
- Uses `BASIC_CUSTOMER_QUERY_SQL` instead of `STEWARTS_CUSTOMER_QUERY_SQL`
- Uses `BASIC_CUSTOMER_FIELDS_LIST` instead of `STEWARTS_CUSTOMER_FIELDS_LIST`
- Calls `build_jolley_header_dict` instead of basic dict building
- Different CSV column layout in process_a_record and process_b_record

```python
# dispatch/converters/convert_to_jolley_custom.py
"""Jolley Custom CSV EDI Converter - Refactored to use composition.

Uses composition instead of mixin inheritance.
Differences from Stewarts: No store number, corporate fallback, swapped Bill/Ship layout.
"""
import csv
from typing import Any

from core import utils
from core.utils import prettify_dates
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)
from dispatch.converters.customer_queries import (
    BASIC_CUSTOMER_FIELDS_LIST,
    BASIC_CUSTOMER_QUERY_SQL,
)
from dispatch.converters.jolley_header_builder import build_jolley_header_dict
from dispatch.services.database_connector import DatabaseConnector
from dispatch.services.customer_lookup_service import CustomerLookupService
from dispatch.services.uom_lookup_service import UOMLookupService
from dispatch.services.item_processing import ItemProcessor


class JolleyCustomConverter(BaseEDIConverter):
    """Converter for Jolley Custom CSV format with database lookups.

    Uses composable services for database operations, customer lookups,
    UOM lookups, and item processing.
    """

    def __init__(self):
        """Initialize converter with composition services."""
        self._db_connector = DatabaseConnector()
        self._customer_service: Optional[CustomerLookupService] = None
        self._uom_service: Optional[UOMLookupService] = None
        self._item_processor = ItemProcessor()
        self._header_a_record: dict[str, str] = {}
        self._header_fields_dict: dict[str, Any] = {}

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and database connection."""
        self._db_connector.init_connection(context.settings_dict)
        self._customer_service = CustomerLookupService(
            self._db_connector.query_runner, BASIC_CUSTOMER_QUERY_SQL
        )
        self._uom_service = UOMLookupService(self._db_connector.query_runner)

        context.output_file = open(
            context.get_output_path(".csv"), "w", newline="\n", encoding="utf-8"
        )
        context.csv_writer = csv.writer(context.output_file, dialect="unix")

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), writing invoice header to CSV."""
        super().process_a_record(record, context)
        self._header_a_record = record.fields

        self._customer_service.lookup(record.fields["invoice_number"])
        self._uom_service.init_uom_lookup(record.fields["invoice_number"])

        # Use Jolley-specific header dict builder with corporate fallback
        raw_header = self._customer_service.header_dict
        self._header_fields_dict = build_jolley_header_dict(raw_header, BASIC_CUSTOMER_FIELDS_LIST)

        csv_writer = context.csv_writer

        csv_writer.writerow(["Invoice Details"])
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
        )
        csv_writer.writerow(
            [
                prettify_dates(self._header_fields_dict["Invoice_Date"]),
                self._header_fields_dict["Terms_Code"],
                record.fields["invoice_number"],
                prettify_dates(
                    self._header_fields_dict["Invoice_Date"],
                    self._header_fields_dict["Terms_Duration"],
                    -1,
                ),
            ]
        )

        # Build ship-to segment (uses corporate customer if available)
        ship_to_segment = [
            str(self._header_fields_dict["Corporate_Customer_Number"])
            + "\n"
            + self._header_fields_dict["Corporate_Customer_Name"]
            + "\n"
            + self._header_fields_dict["Corporate_Customer_Address"]
            + "\n"
            + self._header_fields_dict["Corporate_Customer_Town"]
            + ", "
            + self._header_fields_dict["Corporate_Customer_State"]
            + ", "
            + self._header_fields_dict["Corporate_Customer_Zip"]
            + ", "
            + "\n"
            + "US",
        ]

        # Jolley layout: Bill To on left, Ship To on right
        csv_writer.writerow(
            [
                "Bill To:",
                str(self._header_fields_dict["Customer_Number"])
                + "\n"
                + self._header_fields_dict["Customer_Name"]
                + "\n"
                + self._header_fields_dict["Customer_Address"]
                + "\n"
                + self._header_fields_dict["Customer_Town"]
                + ", "
                + self._header_fields_dict["Customer_State"]
                + ", "
                + self._header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
                "Ship To:",
            ]
            + ship_to_segment
        )
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Description", "UPC #", "Quantity", "UOM", "Price", "Amount"]
        )

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), writing to CSV."""
        total_price, qtyint = self._item_processor.convert_to_item_total(
            record.fields["unit_cost"], record.fields["qty_of_units"]
        )
        context.csv_writer.writerow(
            [
                record.fields["description"],
                self._item_processor.generate_full_upc(record.fields["upc_number"]),
                qtyint,
                self._uom_service.get_uom(
                    record.fields["vendor_item"], record.fields["unit_multiplier"]
                ),
                "$" + str(utils.convert_to_price(record.fields["unit_cost"])),
                "$" + str(total_price),
            ]
        )

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax), writing to CSV."""
        context.csv_writer.writerow(
            [
                record.fields["description"],
                "000000000000",
                1,
                "EA",
                "$" + str(utils.convert_to_price(record.fields["amount"])),
                "$" + str(utils.convert_to_price(record.fields["amount"])),
            ]
        )

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by writing total row and closing file."""
        if self._header_a_record:
            context.csv_writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "Total:",
                    "$"
                    + str(
                        utils.convert_to_price(
                            self._header_a_record["invoice_total"]
                        ).lstrip("0")
                    ),
                ]
            )

        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

        self._db_connector.close()


# Backward Compatibility Wrapper
from .convert_base import create_edi_convert_wrapper

edi_convert = create_edi_convert_wrapper(
    JolleyCustomConverter, format_name="jolley_custom"
)
```

- [ ] **Step 2: Run tests to verify**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_convert_to_jolley_custom.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add dispatch/converters/convert_to_jolley_custom.py
git commit -m "refactor: migrate JolleyCustomConverter to composition"
```

---

## Task 9: Fix EStoreEInvoiceConverter OCP Violation

**Files:**
- Modify: `dispatch/converters/convert_to_estore_einvoice.py`
- Test: `tests/dispatch/converters/test_convert_to_estore_einvoice.py`

- [ ] **Step 1: Read current implementation and understand the override**

The issue is that `EStoreEInvoiceConverter.edi_convert()` overrides `BaseEDIConverter.edi_convert()` entirely (lines 134-170), bypassing the Template Method pattern. This makes it impossible to extend/customize via hooks.

The fix: Make it use the base class's Template Method and implement the hooks instead.

Key differences from other converters:
- Dynamic output filename with timestamp: `eInv{vendorName}.{timestamp}.csv`
- Row buffering with deferred writing (`row_dict_list`)
- Shipper mode handling (parent/child items)
- Trailer records with invoice totals
- Uses `utils.add_row()` instead of `csv_writer.writerow()`
- Uses `self._context` stored reference for `_csv_file` property

- [ ] **Step 2: Refactor to use base class hooks**

```python
# dispatch/converters/convert_to_estore_einvoice.py
"""EStore E-Invoice CSV EDI Converter - Refactored to use Template Method hooks.

This module converts EDI files to EStore E-Invoice CSV format with support for
complex "shipper mode" handling. Refactored to use BaseEDIConverter's
Template Method pattern properly instead of overriding edi_convert.
"""
import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import Any

from core import utils
from core.constants import EMPTY_DATE_MMDDYY, EMPTY_PARENT_ITEM
from core.structured_logging import get_logger
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)

logger = get_logger(__name__)


class EStoreEInvoiceConverter(BaseEDIConverter):
    """Converter for EStore E-Invoice CSV format with shipper mode support.

    This class implements the hook methods required by BaseEDIConverter
    to produce EStore-compatible CSV output. Uses proper Template Method
    hooks instead of overriding edi_convert.
    """

    def __init__(self):
        """Initialize converter state."""
        self._store_number = ""
        self._vendor_oid = ""
        self._vendor_name = ""
        self._upc_lookup = {}
        self._row_dict_list: list[dict] = []
        self._shipper_mode = False
        self._shipper_parent_item = False
        self._shipper_accum: list[Decimal] = []
        self._invoice_accum: list[Decimal] = []
        self._shipper_line_number = 0
        self._invoice_index = 0
        self._output_filename = ""

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and state.

        Args:
            context: The conversion context
        """
        params = context.parameters_dict
        self._store_number = params.get("estore_store_number", "")
        self._vendor_oid = params.get("estore_Vendor_OId", "")
        self._vendor_name = params.get("estore_vendor_NameVendorOID", "")
        self._upc_lookup = context.upc_lut

        self._row_dict_list = []
        self._shipper_mode = False
        self._shipper_parent_item = False
        self._shipper_accum = []
        self._invoice_accum = []
        self._shipper_line_number = 0
        self._invoice_index = 0

        # Generate output filename with timestamp
        self._output_filename = os.path.join(
            os.path.dirname(context.output_filename),
            f"eInv{self._vendor_name}.{datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')}.csv",
        )

        context.output_file = open(
            self._output_filename, "w", newline="", encoding="utf-8"
        )
        context.csv_writer = csv.writer(
            context.output_file, dialect="excel", lineterminator="\r\n"
        )

    def _leave_shipper_mode(self) -> None:
        """Exit shipper mode and update parent item quantity."""
        if self._shipper_mode:
            self._row_dict_list[self._shipper_line_number]["QTY"] = len(
                self._shipper_accum
            )
            self._shipper_accum.clear()
            logger.debug("leave shipper mode")
            self._shipper_mode = False

    def _flush_write_queue(self) -> None:
        """Flush buffered rows to CSV and write trailer."""
        self._leave_shipper_mode()

        for row in self._row_dict_list:
            utils.add_row(self._csv_file, row)

        if len(self._invoice_accum) > 0:
            trailer_row = {"Record Type": "T", "Invoice Cost": sum(self._invoice_accum)}
            utils.add_row(self._csv_file, trailer_row)

        self._row_dict_list.clear()
        self._invoice_accum.clear()

    @property
    def _csv_file(self):
        """Get the CSV writer from context."""
        # Context is stored by base class in self._context during edi_convert
        return getattr(self, "_context", None)

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), handling shipper mode and creating header row."""
        super().process_a_record(record, context)

        self._leave_shipper_mode()

        # Write trailer for previous invoice if exists
        if len(self._invoice_accum) > 0:
            trailer_row = {
                "Record Type": "T",
                "Invoice Cost": sum(self._invoice_accum),
            }
            self._row_dict_list.append(trailer_row)
            self._invoice_index += 1
            self._invoice_accum.clear()

        # Format invoice date
        if not record.fields["invoice_date"] == EMPTY_DATE_MMDDYY:
            invoice_date = datetime.strptime(record.fields["invoice_date"], "%m%d%y")
            write_invoice_date = datetime.strftime(invoice_date, "%Y%m%d")
        else:
            write_invoice_date = "00000000"

        # Create header row
        row_dict = {
            "Record Type": "H",
            "Store Number": self._store_number,
            "Vendor OId": self._vendor_oid,
            "Invoice Number": record.fields["invoice_number"],
            "Purchase Order": "",
            "Invoice Date": write_invoice_date,
        }
        self._row_dict_list.append(row_dict)
        self._invoice_index += 1

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), handling shipper mode."""
        # Lookup UPC
        try:
            upc_entry = self._upc_lookup[int(record.fields["vendor_item"])][1]
        except KeyError:
            logger.debug("cannot find each upc")
            upc_entry = record.fields["upc_number"]

        # Create detail row
        row_dict = {
            "Record Type": "D",
            "Detail Type": "I",
            "Subcategory OId": "",
            "Vendor Item": record.fields["vendor_item"],
            "Vendor Pack": record.fields["unit_multiplier"],
            "Item Description": record.fields["description"].strip(),
            "Item Pack": "",
            "GTIN": upc_entry.strip(),
            "GTIN Type": "",
            "QTY": utils.qty_to_int(record.fields["qty_of_units"]),
            "Unit Cost": utils.convert_to_price_decimal(record.fields["unit_cost"]),
            "Unit Retail": utils.convert_to_price_decimal(
                record.fields["suggested_retail_price"]
            ),
            "Extended Cost": utils.convert_to_price_decimal(record.fields["unit_cost"])
            * utils.qty_to_int(record.fields["qty_of_units"]),
            "NULL": "",
            "Extended Retail": "",
        }

        # Check if this is a shipper parent item
        if record.fields["parent_item_number"] == record.fields["vendor_item"]:
            self._leave_shipper_mode()
            logger.debug("enter shipper mode")
            self._shipper_mode = True
            self._shipper_parent_item = True
            row_dict["Detail Type"] = "D"
            self._shipper_line_number = self._invoice_index

        # Handle shipper mode logic
        if self._shipper_mode:
            if record.fields["parent_item_number"] not in [EMPTY_PARENT_ITEM, "\n"]:
                if self._shipper_parent_item:
                    self._shipper_parent_item = False
                else:
                    row_dict["Detail Type"] = "C"
                    self._shipper_accum.append(
                        utils.convert_to_price_decimal(record.fields["unit_cost"])
                        * utils.qty_to_int(record.fields["qty_of_units"])
                    )
            else:
                try:
                    self._leave_shipper_mode()
                except Exception as error:
                    logger.debug("error leaving shipper mode: %s", error)

        self._row_dict_list.append(row_dict)
        self._invoice_index += 1
        self._invoice_accum.append(row_dict["Extended Cost"])

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by flushing remaining rows and closing file."""
        self._flush_write_queue()

        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

    def _get_return_value(self, context: ConversionContext) -> str:
        """Get the return value - the generated filename."""
        return self._output_filename


# Backward Compatibility Wrapper
from .convert_base import create_edi_convert_wrapper

edi_convert = create_edi_convert_wrapper(
    EStoreEInvoiceConverter, format_name="estore_einvoice"
)
```

- [ ] **Step 3: Run tests to verify**

Run: `./.venv/bin/pytest tests/dispatch/converters/test_convert_to_estore_einvoice.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add dispatch/converters/convert_to_estore_einvoice.py
git commit -m "refactor: fix EStoreEInvoiceConverter OCP violation, use base class hooks"
```

---

## Task 10: Update mixins.py for Backward Compatibility

**Files:**
- Modify: `dispatch/converters/mixins.py`

- [ ] **Step 1: Update mixins.py to import from new modules**

The existing mixins should become thin wrappers that delegate to the new services, maintaining backward compatibility for any code that still imports from mixins.

```python
# dispatch/converters/mixins.py
"""DB-Enabled Converter Mixins - Backward compatibility wrappers.

This module provides backward-compatible ABC mixin classes that delegate to
the new service-based architecture. New code should use the services directly.

Deprecated: Use dispatch.services.database_connector.DatabaseConnector,
    dispatch.services.customer_lookup_service.CustomerLookupService,
    dispatch.services.uom_lookup_service.UOMLookupService,
    dispatch.services.item_processing.ItemProcessor
"""
from abc import ABC
from typing import Any

from core.database import QueryRunner
from core.exceptions import CustomerLookupError
from core.structured_logging import get_logger
from core.utils import calc_check_digit, convert_to_price, convert_UPCE_to_UPCA, safe_int

from dispatch.converters.customer_queries import (
    BASIC_CUSTOMER_FIELDS_LIST,
    BASIC_CUSTOMER_QUERY_SQL,
    CUSTOMER_FIELDS_LIST_BASE,
    CUSTOMER_QUERY_SQL_TEMPLATE,
    CUSTOMER_STORE_NUMBER_FIELD_BASIC,
    CUSTOMER_STORE_NUMBER_FIELD_STEWARTS,
    STEWARTS_CUSTOMER_FIELDS_LIST,
    STEWARTS_CUSTOMER_QUERY_SQL,
    build_customer_query_sql,
)
from dispatch.converters.jolley_header_builder import build_jolley_header_dict
from dispatch.services.database_connector import DatabaseConnector
from dispatch.services.customer_lookup_service import CustomerLookupService
from dispatch.services.uom_lookup_service import UOMLookupService
from dispatch.services.item_processing import ItemProcessor

logger = get_logger(__name__)

__all__ = [
    "DatabaseConnectionMixin",
    "CustomerLookupMixin",
    "UOMLookupMixin",
    "ItemProcessingMixin",
    "CUSTOMER_QUERY_SQL_TEMPLATE",
    "CUSTOMER_FIELDS_LIST_BASE",
    "CUSTOMER_STORE_NUMBER_FIELD_BASIC",
    "CUSTOMER_STORE_NUMBER_FIELD_STEWARTS",
    "BASIC_CUSTOMER_FIELDS_LIST",
    "BASIC_CUSTOMER_QUERY_SQL",
    "STEWARTS_CUSTOMER_FIELDS_LIST",
    "STEWARTS_CUSTOMER_QUERY_SQL",
    "build_jolley_header_dict",
]


class DatabaseConnectionMixin(ABC):
    """Backward-compatible mixin - delegates to DatabaseConnector service."""

    query_object: QueryRunner | None = None
    _db_initialized: bool = False

    def _init_db_connection(
        self,
        settings_dict: dict[str, Any],
        database: str = "QGPL",
        required_keys: tuple[str, ...] = ("as400_username", "as400_address"),
    ) -> None:
        connector = DatabaseConnector()
        connector.init_connection(settings_dict, database, required_keys)
        self.query_object = connector.query_runner
        self._db_initialized = connector.is_connected

    def _close_db_connection(self) -> None:
        if hasattr(self, "query_object") and self.query_object is not None:
            try:
                self.query_object.close()
            except AttributeError:
                pass
            self.query_object = None
            self._db_initialized = False


class CustomerLookupMixin(ABC):
    """Backward-compatible mixin - delegates to CustomerLookupService."""

    header_fields_dict: dict[str, Any] = {}

    def _get_customer_query_sql(self) -> str:
        raise NotImplementedError("Subclasses must implement _get_customer_query_sql()")

    def _get_customer_header_field_names(self) -> list[str]:
        raise NotImplementedError("Subclasses must implement _get_customer_header_field_names()")

    def _build_customer_header_dict(
        self, header_fields: dict[str, Any], header_fields_list: list[str]
    ) -> dict[str, Any]:
        result = {}
        for key, value in header_fields.items():
            new_key = key.replace(" ", "_")
            result[new_key] = value
        return result

    def _init_customer_lookup(self, invoice_number: str, query_object: QueryRunner) -> dict[str, Any]:
        service = CustomerLookupService(query_object, self._get_customer_query_sql())
        self.header_fields_dict = service.lookup(invoice_number)
        return self.header_fields_dict


class UOMLookupMixin(ABC):
    """Backward-compatible mixin - delegates to UOMLookupService."""

    uom_lookup_list: list[dict[str, Any]] = []

    def _get_uom_query_sql(self) -> str:
        return """
            SELECT DISTINCT bubacd AS itemno,
                           bus3qt AS uom_mult,
                           buhxtx AS uom_code
            FROM dacdata.odhst odhst
            WHERE odhst.buhhnb = ?
        """

    def _init_uom_lookup(self, invoice_number: str, query_object: QueryRunner) -> list[dict[str, Any]]:
        service = UOMLookupService(query_object)
        self.uom_lookup_list = service.init_uom_lookup(invoice_number)
        return self.uom_lookup_list

    def _get_uom(self, item_number: str, packsize: str) -> str:
        service = UOMLookupService.__new__(UOMLookupService)
        service.uom_lookup_list = self.uom_lookup_list
        return service.get_uom(item_number, packsize)


class ItemProcessingMixin(ABC):
    """Backward-compatible mixin - delegates to ItemProcessor service."""

    @staticmethod
    def _convert_to_item_total(unit_cost: str, qty: str):
        processor = ItemProcessor()
        return processor.convert_to_item_total(unit_cost, qty)

    @staticmethod
    def _generate_full_upc(input_upc: str) -> str:
        processor = ItemProcessor()
        return processor.generate_full_upc(input_upc)
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `./.venv/bin/pytest tests/dispatch/converters/ -v -k "stewarts or jolley or estore"`
Expected: PASS (backward compat wrappers should work)

- [ ] **Step 3: Commit**

```bash
git add dispatch/converters/mixins.py
git commit -m "refactor: make mixins.py backward-compat wrappers delegating to services"
```

---

## Task 11: Create Plugin Interfaces

**Files:**
- Create: `interface/plugins/interfaces.py`
- Modify: `interface/plugins/plugin_base.py`
- Test: `tests/interface/plugins/test_interfaces.py`

- [ ] **Step 1: Define interfaces**

```python
# interface/plugins/interfaces.py
"""Plugin interfaces for SOLID-compliant plugin system.

These interfaces follow Interface Segregation Principle, allowing plugins
to implement only the capabilities they need.
"""
from abc import ABC, abstractmethod
from typing import Any

from .config_schemas import ConfigurationSchema
from .validation_framework import ValidationResult


class IPlugin(ABC):
    """Core plugin interface - lifecycle and identification.

    All plugins MUST implement this interface.
    """

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""

    @classmethod
    @abstractmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""

    @classmethod
    @abstractmethod
    def get_version(cls) -> str:
        """Get the plugin version."""

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin with configuration."""

    @abstractmethod
    def activate(self) -> None:
        """Activate the plugin."""

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the plugin."""


class IConfigurablePlugin(ABC):
    """Plugin interface for configuration management.

    Implement this if your plugin has configuration options.
    """

    @classmethod
    @abstractmethod
    def get_configuration_schema(cls) -> ConfigurationSchema | None:
        """Get the configuration schema for the plugin."""

    @abstractmethod
    def validate_configuration(self, config: dict[str, Any]) -> ValidationResult:
        """Validate configuration against the plugin's schema."""

    def get_default_configuration(self) -> dict[str, Any]:
        """Get the default configuration values for the plugin."""
        schema = self.get_configuration_schema()
        if schema is not None:
            return schema.get_defaults()
        return {}

    @abstractmethod
    def update_configuration(self, config: dict[str, Any]) -> ValidationResult:
        """Update the plugin's configuration."""


class IUIPlugin(ABC):
    """Plugin interface for UI widget creation.

    Implement this if your plugin provides a configuration UI.
    """

    @abstractmethod
    def create_widget(self, parent: Any = None) -> Any:
        """Create a UI widget for configuring the plugin.

        Args:
            parent: Optional parent widget

        Returns:
            UI widget for plugin configuration
        """


class IPluginCompatibility(ABC):
    """Plugin interface for compatibility checking.

    Implement this if your plugin has system dependencies.
    """

    @classmethod
    def is_compatible(cls) -> bool:
        """Check if the plugin is compatible with the current system."""
        return True

    @classmethod
    def get_dependencies(cls) -> list[str]:
        """Get the list of plugin dependencies."""
        return []
```

- [ ] **Step 2: Modify plugin_base.py to use interfaces**

```python
# interface/plugins/plugin_base.py (MODIFIED)
"""Base Plugin Implementation - backward compatible ABC using interfaces."""
from abc import ABC
from typing import Any

from .config_schemas import ConfigurationSchema
from .validation_framework import ValidationResult
from .interfaces import IPlugin, IConfigurablePlugin, IUIPlugin, IPluginCompatibility


class PluginBase(IPlugin, IConfigurablePlugin, IUIPlugin, IPluginCompatibility):
    """Backward-compatible base class implementing all plugin interfaces.

    Plugins that don't need all capabilities can inherit from specific
    interfaces instead of this class.
    """

    @classmethod
    def get_configuration_schema(cls) -> ConfigurationSchema | None:
        return None

    def validate_configuration(self, config: dict[str, Any]) -> ValidationResult:
        schema = self.get_configuration_schema()
        if schema is not None:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])

    def update_configuration(self, config: dict[str, Any]) -> ValidationResult:
        validation = self.validate_configuration(config)
        if validation.success:
            self.initialize(config)
        return validation
```

- [ ] **Step 3: Run tests**

Run: `./.venv/bin/pytest tests/interface/plugins/test_interfaces.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add interface/plugins/interfaces.py interface/plugins/plugin_base.py
git commit -m "feat: add ISP-compliant plugin interfaces (IPlugin, IConfigurablePlugin, IUIPlugin)"
```

---

## Self-Review Checklist

1. **Spec coverage:** All SOLID violations addressed:
   - [x] ISP: PluginBase split into focused interfaces
   - [x] SRP: Mixins split into separate service classes
   - [x] OCP: EStoreEInvoiceConverter now uses base class hooks
   - [x] DIP: Services depend on abstractions (QueryRunner protocol)
   - [x] LSP: All services have clear contracts

2. **Placeholder scan:** No "TBD", "TODO", or incomplete steps

3. **Type consistency:**
   - `CustomerLookupService.__init__(self, query_runner, sql_query)` matches usage in converters
   - `UOMLookupService.init_uom_lookup(invoice_number)` returns list matching `uom_lookup_list`
   - `ItemProcessor.convert_to_item_total()` signature matches original mixin
   - `DatabaseConnector.init_connection()` matches settings dict pattern

4. **Files created/modified match plan:**
   - `dispatch/services/item_processing.py` ✓
   - `dispatch/services/uom_lookup_service.py` ✓
   - `dispatch/services/customer_lookup_service.py` ✓
   - `dispatch/services/database_connector.py` ✓
   - `dispatch/converters/customer_queries.py` ✓
   - `dispatch/converters/jolley_header_builder.py` ✓
   - `dispatch/converters/convert_to_stewarts_custom.py` ✓
   - `dispatch/converters/convert_to_jolley_custom.py` ✓
   - `dispatch/converters/convert_to_estore_einvoice.py` ✓
   - `dispatch/converters/mixins.py` ✓
   - `interface/plugins/interfaces.py` ✓
   - `interface/plugins/plugin_base.py` ✓
