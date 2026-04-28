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

from abc import ABC
from typing import Any

from core.database import QueryRunner
from core.exceptions import CustomerLookupError
from core.structured_logging import get_logger
from dispatch.services.database_connector import DatabaseConnector
from dispatch.services.item_processing import ItemProcessor

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
            "as400_address",
        ),
    ) -> None:
        """Initialize the database connection.

        Args:
            settings_dict: Dictionary containing database connection settings
            database: Database name (default: QGPL)
            required_keys: Tuple of required settings keys

        """
        connector = DatabaseConnector()
        connector.init_connection(settings_dict, database, required_keys)
        self.query_object = connector.query_runner
        self._db_initialized = connector.is_initialized
        self._db_connector = connector
        # Expose ssh_key_filename on the mixin for backward compatibility
        self.ssh_key_filename = connector.ssh_key_filename
        self.as400_password = connector.as400_password
        logger.debug(
            "Database connection initialized for %s (ssh_key_filename=%s)",
            self.__class__.__name__,
            connector.ssh_key_filename,
        )

    def _close_db_connection(self) -> None:
        """Close the database connection if open."""
        if hasattr(self, "_db_connector") and self._db_connector is not None:
            self._db_connector.close()
        if hasattr(self, "query_object"):
            self.query_object = None
        self._db_initialized = False


class CustomerLookupMixin(ABC):
    """Mixin for converters that perform customer header lookups.

    Provides common customer header field retrieval logic for AS400 data.

    Subclasses must:
    - Implement _get_customer_query_sql() returning the SQL template
    - Implement _get_customer_header_field_names() to map query results to dict
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

        invoice_param = invoice_number.lstrip("0")

        header_fields = query_object.run_query(query_sql, (invoice_param,))

        if len(header_fields) == 0:
            logger.error(
                "%s: Cannot find order %s in AS400 history",
                self.__class__.__name__,
                invoice_number,
            )
            raise CustomerLookupError(f"Cannot Find Order {invoice_number} In History.")

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

    def _uom_get_key(self, entry: dict[str, Any], *keys: str) -> str | None:
        """Case-insensitive key lookup for UOM entries."""
        for key in keys:
            for k, v in entry.items():
                if k.upper() == key.upper():
                    return v
            for k, v in entry.items():
                if k.lower() == key.lower():
                    return v
        return None

    def _uom_build_stage_1_list(self, item_number: str) -> list[dict[str, Any]]:
        """Build list of entries matching the given item_number."""
        res: list[dict[str, Any]] = []
        for entry in self.uom_lookup_list:
            item_no = self._uom_get_key(entry, "itemno", "ITEMNO")
            if item_no is None:
                continue
            try:
                if int(item_no) == int(item_number):
                    res.append(entry)
            except (ValueError, TypeError):
                continue
        return res

    def _uom_select_stage_2_list(
        self, stage_1_list: list[dict[str, Any]], packsize: str
    ) -> list[dict[str, Any]]:
        """From stage_1_list select entries matching packsize or
        fallback entries.
        """
        res: list[dict[str, Any]] = []
        for entry in stage_1_list:
            uom_mult = self._uom_get_key(entry, "uom_mult", "UOM_MULT")
            if uom_mult is None:
                res.append(entry)
                break
            try:
                if int(uom_mult) == int(packsize):
                    res.append(entry)
            except (ValueError, TypeError):
                res.append(entry)
                break
        return res

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

        # Use class-level helpers to keep this method simple
        stage_1_list = self._uom_build_stage_1_list(item_number)
        stage_2_list = self._uom_select_stage_2_list(stage_1_list, packsize)

        try:
            uom_code = self._uom_get_key(stage_2_list[0], "uom_code", "UOM_CODE")
            return uom_code if uom_code else "?"
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
    def _convert_to_item_total(unit_cost: str, qty: str):
        processor = ItemProcessor()
        return processor.convert_to_item_total(unit_cost, qty)

    @staticmethod
    def _generate_full_upc(input_upc: str) -> str:
        processor = ItemProcessor()
        return processor.generate_full_upc(input_upc)


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
    result = {}
    for key, value in header_fields.items():
        new_key = key.replace(" ", "_")
        result[new_key] = value

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
