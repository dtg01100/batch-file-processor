"""DB-Enabled Converter Mixins - Shared Base Classes for Database-Enabled Converters.

This module provides mixin classes that consolidate common functionality
across converters that require database access for customer lookups and
UOM (Unit of Measure) data.

Mixins Provided:
- DatabaseConnectionMixin: Database connection setup and management
- CustomerLookupMixin: Customer header field lookups from AS400
- UOMLookupMixin: UOM lookup and resolution
- ItemProcessingMixin: Item total calculation and UPC generation

Example:
    class MyDBConverter(BaseEDIConverter, DatabaseConnectionMixin,
                        CustomerLookupMixin, UOMLookupMixin, ItemProcessingMixin):
        def __init__(self):
            super().__init__()
            self._init_db_connection(settings)

        def process_a_record(self, record, context):
            self._init_customer_lookup(record.fields["invoice_number"])
            # ... use mixin methods

"""

import decimal
from abc import ABC
from typing import Any

from core.database import QueryRunner
from core.exceptions import CustomerLookupError
from core.structured_logging import get_logger
from core.utils import (
    calc_check_digit,
    convert_to_price,
    convert_UPCE_to_UPCA,
    safe_int,
)

logger = get_logger(__name__)


class DatabaseConnectionMixin(ABC):
    """Mixin for converters that require database connections.

    Provides common database initialization logic using QueryRunner.

    Subclasses must:
    - Call self._init_db_connection() in their _initialize_output method
    - Store the query_object as self.query_object

    Attributes:
        query_object: The database QueryRunner
        _db_initialized: Whether the database connection has been established

    """

    query_object: QueryRunner | None = None
    _db_initialized: bool = False

    def _init_db_connection(
        self,
        settings_dict: dict[str, Any],
        database: str = "QGPL",
        required_keys: tuple[str, ...] = (
            "as400_username",
            "as400_password",
            "as400_address",
        ),
    ) -> None:
        """Initialize the database connection.

        Args:
            settings_dict: Dictionary containing database connection settings
            database: Database name (default: QGPL)
            required_keys: Tuple of required settings keys

        """
        if self._db_initialized:
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

        # Use the convenience wrapper to create query runner from settings
        from core.database.query_runner import create_query_runner_from_settings

        ssh_key_filename = settings_dict.get("ssh_key_filename", "")
        self.query_object = create_query_runner_from_settings(
            settings_dict, database=database
        )
        self._db_initialized = True
        logger.debug("Database connection initialized for %s", self.__class__.__name__)

    def _close_db_connection(self) -> None:
        """Close the database connection if open."""
        if hasattr(self, "query_object") and self.query_object is not None:
            try:
                self.query_object.close()
                logger.debug(
                    "Database connection closed for %s", self.__class__.__name__
                )
            except AttributeError:
                pass
            self.query_object = None
            self._db_initialized = False


class CustomerLookupMixin(ABC):
    """Mixin for converters that perform customer header lookups.

    Provides common customer header field retrieval logic for AS400 data.

    Subclasses must:
    - Implement _get_customer_query_sql() returning the SQL template
    - Implement _build_customer_header_dict() to map query results to dict
    - Call _init_customer_lookup(invoice_number) in process_a_record

    Attributes:
        header_fields_dict: Current customer header fields

    """

    header_fields_dict: dict[str, Any] = {}

    def _get_customer_query_sql(self) -> str:
        """Return the SQL query template for customer lookup.

        Returns:
            SQL query string with :paramstyle: placeholders

        """
        raise NotImplementedError("Subclasses must implement _get_customer_query_sql()")

    def _get_customer_header_field_names(self) -> list[str]:
        """Return ordered list of field names for customer query results.

        Returns:
            List of field name strings matching query columns

        """
        raise NotImplementedError(
            "Subclasses must implement _get_customer_header_field_names()"
        )

    def _build_customer_header_dict(
        self, header_fields: dict[str, Any], header_fields_list: list[str]
    ) -> dict[str, Any]:
        """Build customer header dictionary from query results.

        Override this to add custom field processing (e.g., None fallback).

        Args:
            header_fields: Raw query result dict (keys may have spaces)
            header_fields_list: List of field names (with underscores)

        Returns:
            Dictionary mapping field names to values

        """
        # Convert spaces to underscores in keys for compatibility
        result = {}
        for key, value in header_fields.items():
            new_key = key.replace(" ", "_")
            result[new_key] = value
        return result

    def _init_customer_lookup(
        self, invoice_number: str, query_object: QueryRunner
    ) -> dict[str, Any]:
        """Initialize customer lookup and fetch header fields.

        Args:
            invoice_number: Invoice number to look up
            query_object: Database query runner (QueryRunner with dict results)

        Returns:
            Dictionary of customer header fields

        Raises:
            CustomerLookupError: If customer not found

        """
        query_sql = self._get_customer_query_sql()
        header_fields_list = self._get_customer_header_field_names()

        # Normalize invoice number for query (strip leading zeros)
        invoice_param = invoice_number.lstrip("0")

        header_fields = query_object.run_query(query_sql, (invoice_param,))

        if len(header_fields) == 0:
            logger.error(
                "%s: Cannot find order %s in AS400 history",
                self.__class__.__name__,
                invoice_number,
            )
            raise CustomerLookupError(f"Cannot Find Order {invoice_number} In History.")

        # Apply subclass's header dict builder (handles Jolley/Stewarts specifics)
        self.header_fields_dict = self._build_customer_header_dict(
            header_fields[0], header_fields_list
        )
        return self.header_fields_dict


class UOMLookupMixin(ABC):
    """Mixin for converters that perform UOM (Unit of Measure) lookups.

    Provides common UOM lookup and resolution logic.

    Attributes:
        uom_lookup_list: Cached list of UOM data from database

    """

    uom_lookup_list: list[dict[str, Any]] = []

    def _get_uom_query_sql(self) -> str:
        """Return the SQL query template for UOM lookup.

        Returns:
            SQL query string with :paramstyle: placeholders

        """
        return """
            SELECT DISTINCT bubacd AS itemno,
                           bus3qt AS uom_mult,
                           buhxtx AS uom_code
            FROM dacdata.odhst odhst
            WHERE odhst.buhhnb = ?
        """

    def _init_uom_lookup(
        self, invoice_number: str, query_object: QueryRunner
    ) -> list[dict[str, Any]]:
        """Initialize UOM lookup and fetch UOM data.

        Args:
            invoice_number: Invoice number to look up
            query_object: Database query runner (QueryRunner with dict results)

        Returns:
            List of dicts with keys: itemno, uom_mult, uom_code

        """
        self.uom_lookup_list = query_object.run_query(
            self._get_uom_query_sql(), (invoice_number,)
        )

        if not self.uom_lookup_list:
            logger.warning(
                "%s: No UOM data found for invoice %s",
                self.__class__.__name__,
                invoice_number,
            )

        return self.uom_lookup_list

    def _get_uom(self, item_number: str, packsize: str) -> str:
        """Get UOM (Unit of Measure) for an item.

        Args:
            item_number: The vendor item number
            packsize: The unit multiplier/pack size

        Returns:
            UOM code string (e.g., 'EA', 'CS') or '?' if not found

        """
        if not self.uom_lookup_list:
            return "?"

        stage_1_list = []
        stage_2_list = []

        for entry in self.uom_lookup_list:
            item_no = entry.get("itemno")
            if item_no is None:
                continue
            try:
                if int(item_no) == int(item_number):
                    stage_1_list.append(entry)
            except (ValueError, TypeError):
                continue

        for entry in stage_1_list:
            uom_mult = entry.get("uom_mult")
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
            return stage_2_list[0].get("uom_code", "?")
        except IndexError:
            return "?"


class ItemProcessingMixin(ABC):
    """Mixin for converters that process line items.

    Provides common item total calculation and UPC generation logic.

    Methods:
        _convert_to_item_total: Calculate item total from cost and quantity
        _generate_full_upc: Generate full 12-digit UPC from input

    """

    @staticmethod
    def _convert_to_item_total(unit_cost: str, qty: str) -> tuple[decimal.Decimal, int]:
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

    @staticmethod
    def _generate_full_upc(input_upc: str) -> str:
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

        upc_string = ""
        blank_upc = False
        try:
            _ = int(input_upc)
        except ValueError:
            blank_upc = True

        if blank_upc:
            return ""

        proposed_upc = input_upc
        upc_len = len(str(proposed_upc))

        if upc_len == 11:
            # Calculate and append check digit
            upc_string = str(proposed_upc) + str(calc_check_digit(proposed_upc))
        elif upc_len == 8:
            # Convert UPC-E to UPC-A
            converted = convert_UPCE_to_UPCA(proposed_upc)
            upc_string = converted if isinstance(converted, str) else ""
        elif upc_len == 12:
            upc_string = str(proposed_upc)

        return upc_string


# =============================================================================
# Shared SQL Queries for Customer Lookups
# =============================================================================

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


def _build_customer_query_sql(customer_store_number_field: str) -> str:
    return CUSTOMER_QUERY_SQL_TEMPLATE.format(
        customer_store_number_field=customer_store_number_field
    )


BASIC_CUSTOMER_QUERY_SQL = _build_customer_query_sql(CUSTOMER_STORE_NUMBER_FIELD_BASIC)
STEWARTS_CUSTOMER_QUERY_SQL = _build_customer_query_sql(
    CUSTOMER_STORE_NUMBER_FIELD_STEWARTS
)


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
