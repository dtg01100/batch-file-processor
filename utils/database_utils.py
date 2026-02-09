"""
Database query and transformation utilities.

This module provides classes for database queries and functions for
transforming records based on database lookups.
"""

from typing import Dict, Any, Callable
from decimal import Decimal

try:
    from query_runner import query_runner
except (ImportError, RuntimeError):
    query_runner = None


class invFetcher:
    """Invoice data fetcher from AS400 database.

    Fetches purchase orders, customer names, and UOM descriptions
    based on invoice numbers.
    """

    def __init__(self, settings_dict: Dict[str, Any]):
        self.query_object = None
        self.settings = settings_dict
        self.last_invoice_number = 0
        self.uom_lut = {0: "N/A"}
        self.last_invno = 0
        self.po = ""
        self.custname = ""
        self.custno = 0

    def _db_connect(self):
        """Establish database connection."""
        if query_runner is None:
            raise RuntimeError("query_runner not available")
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def _run_qry(self, qry_str: str):
        """Execute a database query."""
        if self.query_object is None:
            self._db_connect()
        qry_return = self.query_object.run_arbitrary_query(qry_str)
        return qry_return

    def fetch_po(self, invoice_number: str) -> str:
        """Fetch purchase order number for given invoice.

        Args:
            invoice_number: Invoice number to query

        Returns:
            Purchase order number as string
        """
        if invoice_number == self.last_invoice_number:
            return self.po
        else:
            # Try to convert invoice_number to int, use 0 if it fails
            try:
                invoice_number_int = int(invoice_number)
            except ValueError:
                invoice_number_int = 0
                
            qry_ret = self._run_qry(
                f"""
                SELECT
                    trim(ohhst.bte4cd),
                    trim(ohhst.bthinb),
                    ohhst.btabnb
                --PO Number
                FROM
                    dacdata.ohhst ohhst
                WHERE
                    ohhst.BTHHNB = {str(invoice_number_int)}
            """
            )
            self.last_invoice_number = invoice_number
            try:
                self.po = qry_ret[0][0]
                self.custname = qry_ret[0][1]
                self.custno = qry_ret[0][2]
            except IndexError:
                self.po = ""
            return self.po

    def fetch_cust_name(self, invoice_number: str) -> str:
        """Fetch customer name for given invoice."""
        self.fetch_po(invoice_number)
        return self.custname

    def fetch_cust_no(self, invoice_number: str) -> int:
        """Fetch customer number for given invoice."""
        self.fetch_po(invoice_number)
        return self.custno

    def fetch_uom_desc(self, itemno: str, uommult: str, lineno: int, invno: str) -> str:
        """Fetch UOM description for item."""
        if invno != self.last_invno:
            self.uom_lut = {0: "N/A"}
            # Try to convert invno to int, use 0 if it fails
            try:
                invno_int = int(invno)
            except ValueError:
                invno_int = 0
                
            qry = f"""
                SELECT
                    BUHUNB,
                    --lineno
                    BUHXTX
                    -- u/m desc
                FROM
                    dacdata.odhst odhst
                WHERE
                    odhst.BUHHNB = {str(invno_int)}
            """
            qry_ret = self._run_qry(qry)
            self.uom_lut = dict(qry_ret)
            self.last_invno = invno
            
        try:
            return self.uom_lut[lineno + 1]
        except KeyError:
            try:
                # Try to convert itemno to int, use 0 if it fails
                try:
                    itemno_int = int(itemno)
                except ValueError:
                    itemno_int = 0
                    
                if int(uommult) > 1:
                    qry = f"""select dsanrep.ANB9TX
                            from dacdata.dsanrep dsanrep
                            where dsanrep.ANBACD = {str(itemno_int)}"""
                else:
                    qry = f"""select dsanrep.ANB8TX
                            from dacdata.dsanrep dsanrep
                            where dsanrep.ANBACD = {str(itemno_int)}"""
                uomqry_ret = self._run_qry(qry)
                return uomqry_ret[0][0]
            except Exception:
                try:
                    if int(uommult) > 1:
                        return "HI"
                    else:
                        return "LO"
                except ValueError:
                    return "NA"


class cRecGenerator:
    """Class for generating split C records for prepaid/non-prepaid sales tax.

    This class queries the database to split sales tax totals into prepaid and
    non-prepaid amounts, then writes them as separate C records.
    """

    def __init__(self, settings_dict: Dict[str, Any]):
        """Initialize the C record generator.

        Args:
            settings_dict: Dictionary containing database connection settings.
                Must include: as400_username, as400_password, as400_address, odbc_driver
        """
        self.query_object = None
        self._invoice_number = "0"
        self.unappended_records = False
        self.settings = settings_dict

    def _db_connect(self):
        """Establish database connection."""
        if query_runner is None:
            raise RuntimeError("query_runner not available")
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def set_invoice_number(self, invoice_number: str) -> None:
        """Set the current invoice number and mark records as unappended.

        Args:
            invoice_number: The invoice number to query for sales tax data.
        """
        self._invoice_number = invoice_number
        self.unappended_records = True

    def fetch_splitted_sales_tax_totals(self, write_func: Callable[[str], None]) -> None:
        """Fetch and write split sales tax totals as C records.

        Queries the database for prepaid and non-prepaid sales tax amounts
        for the current invoice number, then writes them as separate C records.

        Args:
            write_func: A callable that accepts a string to write (e.g., file.write).
        """
        if self.query_object is None:
            self._db_connect()

        qry_ret = self.query_object.run_arbitrary_query(
            f"""
            SELECT
                sum(CASE odhst.buh6nb WHEN 1 THEN 0 ELSE odhst.bufgpr END),
                sum(CASE odhst.buh6nb WHEN 1 THEN odhst.bufgpr ELSE 0 END)
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.BUHHNB = {self._invoice_number}
            """
        )

        qry_ret_non_prepaid, qry_ret_prepaid = qry_ret[0]

        def _write_line(typestr: str, amount: int, wprocfile: Callable[[str], None]):
            descstr = typestr.ljust(25, " ")
            if amount < 0:
                amount_builder = amount - (amount * 2)
            else:
                amount_builder = amount

            amountstr = str(amount_builder).replace(".", "").rjust(9, "0")
            if amount < 0:
                temp_amount_list = list(amountstr)
                temp_amount_list[0] = "-"
                amountstr = "".join(temp_amount_list)
            linebuilder = f"CTAB{descstr}{amountstr}\n"
            wprocfile(linebuilder)

        if qry_ret_prepaid != 0 and qry_ret_prepaid is not None:
            _write_line("Prepaid Sales Tax", qry_ret_prepaid, write_func)
        if qry_ret_non_prepaid != 0 and qry_ret_non_prepaid is not None:
            _write_line("Sales Tax", qry_ret_non_prepaid, write_func)

        self.unappended_records = False


def apply_retail_uom_transform(record: Dict[str, Any], upc_lookup: Dict[str, Any]) -> bool:
    """Apply retail UOM transformation to a B record.

    Transforms B record from case-level to each-level retail UOM.
    Modifies record in place: unit_cost, qty_of_units, upc_number, unit_multiplier.

    Args:
        record: The B record dictionary to transform in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, each_upc, ...]}

    Returns:
        True if transformation was applied, False otherwise.
    """
    # Validate record fields can be parsed
    try:
        item_number = int(record["vendor_item"].strip())
        float(record["unit_cost"].strip())
        test_unit_multiplier = int(record["unit_multiplier"].strip())
        if test_unit_multiplier == 0:
            raise ValueError("unit_multiplier cannot be zero")
        int(record["qty_of_units"].strip())
    except Exception:
        print("cannot parse b record field, skipping")
        return False

    # Get the each-level UPC from lookup
    try:
        each_upc_string = upc_lookup[item_number][1][:11].ljust(11)
    except (KeyError, IndexError):
        each_upc_string = "           "

    # Apply the transformation
    try:
        record["unit_cost"] = (
            str(
                Decimal(
                    (Decimal(record["unit_cost"].strip()) / 100)
                    / Decimal(record["unit_multiplier"].strip())
                ).quantize(Decimal(".01"))
            )
            .replace(".", "")[-6:]
            .rjust(6, "0")
        )
        record["qty_of_units"] = str(
            int(record["unit_multiplier"].strip()) * int(record["qty_of_units"].strip())
        ).rjust(5, "0")
        record["upc_number"] = each_upc_string
        record["unit_multiplier"] = "000001"
        return True
    except Exception as error:
        print(error)
        return False


def apply_upc_override(
    record: Dict[str, Any],
    upc_lookup: Dict[str, Any],
    override_level: int = 1,
    category_filter: str = "ALL",
) -> bool:
    """Override UPC from lookup table based on vendor_item.

    Modifies record in place: upc_number.

    Args:
        record: The B record dictionary to modify in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, upc_level_1, upc_level_2, ...]}
        override_level: Which UPC level to use from lookup table (default: 1).
        category_filter: Comma-separated list of categories to filter by,
            or "ALL" to apply to all categories (default: "ALL").

    Returns:
        True if override was applied, False otherwise.
    """
    try:
        if not upc_lookup:
            return False

        vendor_item_int = int(record["vendor_item"].strip())

        if vendor_item_int not in upc_lookup:
            record["upc_number"] = ""
            return False

        do_updateupc = False
        if category_filter == "ALL":
            do_updateupc = True
        else:
            # Check if item's category is in the filter list
            item_category = upc_lookup[vendor_item_int][0]
            if item_category in category_filter.split(","):
                do_updateupc = True

        if do_updateupc:
            record["upc_number"] = upc_lookup[vendor_item_int][override_level]
            return True
        else:
            return False

    except (KeyError, ValueError, IndexError):
        record["upc_number"] = ""
        return False