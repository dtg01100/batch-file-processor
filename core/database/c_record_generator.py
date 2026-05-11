"""C record generator for sales tax splitting.

Extracted from core/utils/utils.py to colocate database-backed generation
with the rest of the database layer.
"""

from collections.abc import Callable


class CRecGenerator:
    """Class for generating split C records for prepaid/non-prepaid sales tax.

    This class queries the database to split sales tax totals into prepaid and
    non-prepaid amounts, then writes them as separate C records.
    """

    def __init__(self, settings_dict: dict) -> None:
        """Initialize the C record generator.

        Args:
            settings_dict: Dictionary containing database connection settings.
                Must include: as400_username, as400_password, as400_address.

        """
        self.query_object = None
        self._invoice_number = "0"
        self.unappended_records = False
        self.settings = settings_dict

    def _db_connect(self) -> None:
        """Establish database connection using the configured settings.

        Creates a query runner from the stored settings dictionary for
        executing SQL queries against the AS400 database.

        """
        from core.database.query_runner import create_query_runner_from_settings

        self.query_object = create_query_runner_from_settings(self.settings)

    def set_invoice_number(self, invoice_number: str) -> None:
        """Set the current invoice number and mark records as unappended.

        Args:
            invoice_number: The invoice number to query for sales tax data.

        """
        self._invoice_number = invoice_number
        self.unappended_records = True

    def fetch_splitted_sales_tax_totals(
        self, write_func: Callable[[str], None]
    ) -> None:
        """Fetch and write split sales tax totals as C records.

        Queries the database for prepaid and non-prepaid sales tax amounts
        for the current invoice number, then writes them as separate C records.

        Args:
            write_func: A callable that accepts a string to write (e.g., file.write).

        """
        if self.query_object is None:
            self._db_connect()

        qry_ret = self.query_object.run_query(
            """
            SELECT
                SUM(
                    CASE odhst.buh6nb
                    WHEN 1 THEN 0
                    ELSE odhst.bufgpr
                    END
                ) AS non_prepaid,
                SUM(
                    CASE odhst.buh6nb
                    WHEN 1 THEN odhst.bufgpr
                    ELSE 0
                    END
                ) AS prepaid
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.BUHHNB = ?
            """,
            (self._invoice_number,),
        )

        if not qry_ret:
            return

        qry_ret_non_prepaid = qry_ret[0]["non_prepaid"]
        qry_ret_prepaid = qry_ret[0]["prepaid"]

        def _write_line(typestr: str, amount: int, wprocfile) -> None:
            descstr = typestr.ljust(25, " ")
            amount_builder = amount - amount * 2 if amount < 0 else amount

            amountstr = str(amount_builder).replace(".", "").rjust(9, "0")
            if amount < 0:
                amountstr = "-" + amountstr[1:]
            linebuilder = f"CTAB{descstr}{amountstr}\n"
            wprocfile(linebuilder)

        if qry_ret_prepaid != 0 and qry_ret_prepaid is not None:
            _write_line("Prepaid Sales Tax", qry_ret_prepaid, write_func)
        if qry_ret_non_prepaid != 0 and qry_ret_non_prepaid is not None:
            _write_line("Sales Tax", qry_ret_non_prepaid, write_func)

        self.unappended_records = False
