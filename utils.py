from datetime import datetime
import os

try:
    from query_runner import query_runner

    HAS_QUERY_RUNNER = True
except (ImportError, RuntimeError):
    HAS_QUERY_RUNNER = False
    query_runner = None


class invFetcher:
    def __init__(self, settings_dict):
        self.query_object = None
        self.settings = settings_dict
        self.last_invoice_number = 0
        self.uom_lut = {0: "N/A"}
        self.last_invno = 0
        self.po = ""
        self.custname = ""
        self.custno = 0

    def _db_connect(self):
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def _run_qry(self, qry_str):
        if self.query_object is None:
            self._db_connect()
        qry_return = self.query_object.run_arbitrary_query(qry_str)
        return qry_return

    def fetch_po(self, invoice_number):
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

    def fetch_cust_name(self, invoice_number):
        self.fetch_po(invoice_number)
        return self.custname

    def fetch_cust_no(self, invoice_number):
        self.fetch_po(invoice_number)
        return self.custno

    def fetch_uom_desc(self, itemno, uommult, lineno, invno):
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
        except KeyError as error:
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
            except Exception as error:
                try:
                    if int(uommult) > 1:
                        return "HI"
                    else:
                        return "LO"
                except ValueError:
                    return "NA"


def dac_str_int_to_int(dacstr: str) -> int:
    if dacstr.strip() == "":
        return 0
    try:
        if dacstr.startswith("-"):
            return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
        else:
            return int(dacstr)
    except ValueError:
        return 0


def convert_to_price(value):
    return (
        (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
        + "."
        + value[-2:]
    )


def dactime_from_datetime(date_time: datetime) -> str:
    dactime_date_century_digit = str(int(datetime.strftime(date_time, "%Y")[:2]) - 19)
    dactime_date = dactime_date_century_digit + str(
        datetime.strftime(date_time.date(), "%y%m%d")
    )
    return dactime_date


def datetime_from_dactime(dac_time: int) -> datetime:
    dac_time_int = int(dac_time)
    return datetime.strptime(str(dac_time_int + 19000000), "%Y%m%d")


def datetime_from_invtime(invtime: str) -> datetime:
    return datetime.strptime(invtime, "%m%d%y")


def dactime_from_invtime(inv_no: str):
    datetime_obj = datetime_from_invtime(inv_no)
    dactime = dactime_from_datetime(datetime_obj)
    return dactime


def detect_invoice_is_credit(edi_process):
    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        fields = capture_records(work_file.readline())
        if fields["record_type"] != "A":
            raise ValueError(
                "[Invoice Type Detection]: Somehow ended up in the middle of a file, this should not happen"
            )
        if dac_str_int_to_int(fields["invoice_total"]) >= 0:
            return False
        else:
            return True


_default_parser = None


def _get_default_parser():
    global _default_parser
    if _default_parser is None:
        try:
            from edi_format_parser import EDIFormatParser

            _default_parser = EDIFormatParser.get_default_parser()
        except Exception:
            _default_parser = False
    return _default_parser if _default_parser is not False else None


def capture_records(line, parser=None):
    if parser is None:
        parser = _get_default_parser()

    if parser is not None:
        result = parser.parse_line(line)
        if result is None and line and not line.startswith(""):
            raise Exception("Not An EDI")
        return result

    if line.startswith("A"):
        fields = {
            "record_type": line[0],
            "cust_vendor": line[1:7],
            "invoice_number": line[7:17],
            "invoice_date": line[17:23],
            "invoice_total": line[23:33],
        }
        return fields
    elif line.startswith("B"):
        fields = {
            "record_type": line[0],
            "upc_number": line[1:12],
            "description": line[12:37],
            "vendor_item": line[37:43],
            "unit_cost": line[43:49],
            "combo_code": line[49:51],
            "unit_multiplier": line[51:57],
            "qty_of_units": line[57:62],
            "suggested_retail_price": line[62:67],
            "price_multi_pack": line[67:70],
            "parent_item_number": line[70:76],
        }
        return fields
    elif line.startswith("C"):
        fields = {
            "record_type": line[0],
            "charge_type": line[1:4],
            "description": line[4:29],
            "amount": line[29:38],
        }
        return fields
    elif line.startswith(""):
        return None
    else:
        raise Exception("Not An EDI")


def calc_check_digit(value):
    """calculate check digit, they are the same for both UPCA and UPCE
    Code in this module is from: http://code.activestate.com/recipes/528911-barcodes-convert-upc-e-to-upc-a/
    Author's handle is: greg p
    This code is GPL3"""
    check_digit = 0
    odd_pos = True
    for char in str(value)[::-1]:
        if odd_pos:
            check_digit += int(char) * 3
        else:
            check_digit += int(char)
        odd_pos = not odd_pos  # alternate
    check_digit = check_digit % 10
    check_digit = 10 - check_digit
    check_digit = check_digit % 10
    return check_digit


def convert_UPCE_to_UPCA(upce_value):
    """Test value 04182635 -> 041800000265
    Code in this module is from: http://code.activestate.com/recipes/528911-barcodes-convert-upc-e-to-upc-a/
    Author's handle is: greg p
    This code is GPL3"""
    if len(upce_value) == 6:
        middle_digits = upce_value  # assume we're getting just middle 6 digits
    elif len(upce_value) == 7:
        # truncate last digit, assume it is just check digit
        middle_digits = upce_value[:6]
    elif len(upce_value) == 8:
        # truncate first and last digit,
        # assume first digit is number system digit
        # last digit is check digit
        middle_digits = upce_value[1:7]
    else:
        return False
    d1, d2, d3, d4, d5, d6 = list(middle_digits)
    if d6 in ["0", "1", "2"]:
        mfrnum = d1 + d2 + d6 + "00"
        itemnum = "00" + d3 + d4 + d5
    elif d6 == "3":
        mfrnum = d1 + d2 + d3 + "00"
        itemnum = "000" + d4 + d5
    elif d6 == "4":
        mfrnum = d1 + d2 + d3 + d4 + "0"
        itemnum = "0000" + d5
    else:
        mfrnum = d1 + d2 + d3 + d4 + d5
        itemnum = "0000" + d6
    newmsg = "0" + mfrnum + itemnum
    # calculate check digit, they are the same for both UPCA and UPCE
    check_digit = calc_check_digit(newmsg)
    return newmsg + str(check_digit)


def do_split_edi(edi_process, work_directory, parameters_dict):
    """credit for the col_to_excel goes to Nodebody on stackoverflow, at this link: http://stackoverflow.com/a/19154642"""

    def col_to_excel(col):  # col is 1 based
        excel_col = str()
        div = col
        while div:
            (div, mod) = divmod(div - 1, 26)  # will return (x, 0 .. 25)
            excel_col = chr(mod + 65) + excel_col
        return excel_col

    f = None
    output_file_path = None
    count = 0
    write_counter = 0
    edi_send_list = []
    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        lines_in_edi = sum(1 for _ in work_file)
        work_file.seek(0)
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        list_of_first_characters = []
        for line in work_file_lined:
            list_of_first_characters.append(line[0])
        if list_of_first_characters.count("A") > 700:
            return edi_send_list
        for line_mum, line in enumerate(
            work_file_lined
        ):  # iterate over work file contents
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                prepend_letters = col_to_excel(count)
                line_dict = capture_records(writeable_line)
                if int(line_dict["invoice_total"]) < 0:
                    file_name_suffix = ".cr"
                else:
                    file_name_suffix = ".inv"
                if len(edi_send_list) != 0:
                    f.close()
                file_name_prefix = prepend_letters + "_"
                if parameters_dict["prepend_date_files"]:
                    datetime_from_arec = datetime.strptime(
                        line_dict["invoice_date"], "%m%d%y"
                    )
                    inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
                    file_name_prefix = inv_date + "_" + file_name_prefix
                output_file_path = os.path.join(
                    work_directory,
                    file_name_prefix + os.path.basename(edi_process) + file_name_suffix,
                )
                edi_send_list.append(
                    (output_file_path, file_name_prefix, file_name_suffix)
                )
                f = open(output_file_path, "wb")
            f.write(writeable_line.replace("\n", "\r\n").encode())
            write_counter += 1
        f.close()  # close output file
        # edi_send_list.append((output_file_path, file_name_prefix, file_name_suffix))
        # edi_send_list.pop(0)
        edi_send_list_lines = 0
        for output_file, _, _ in edi_send_list:
            with open(output_file, encoding="utf-8") as file_handle:
                edi_send_list_lines += sum(1 for _ in file_handle)
        if not lines_in_edi == write_counter:
            raise Exception("not all lines in input were written out")
        if not lines_in_edi == edi_send_list_lines:
            raise Exception("total lines in output files do not match input file")
        if not len(edi_send_list) == list_of_first_characters.count("A"):
            raise Exception('mismatched number of "A" records')
        if len(edi_send_list) < 1:
            raise Exception("No Split EDIs")
    return edi_send_list


def do_clear_old_files(folder_path, maximum_files):
    while len(os.listdir(folder_path)) > maximum_files:
        os.remove(
            os.path.join(
                folder_path,
                min(
                    os.listdir(folder_path),
                    key=lambda f: os.path.getctime("{}/{}".format(folder_path, f)),
                ),
            )
        )


class cRecGenerator:
    """Class for generating split C records for prepaid/non-prepaid sales tax.

    This class queries the database to split sales tax totals into prepaid and
    non-prepaid amounts, then writes them as separate C records.
    """

    def __init__(self, settings_dict):
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
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def set_invoice_number(self, invoice_number):
        """Set the current invoice number and mark records as unappended.

        Args:
            invoice_number: The invoice number to query for sales tax data.
        """
        self._invoice_number = invoice_number
        self.unappended_records = True

    def fetch_splitted_sales_tax_totals(self, write_func):
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

        def _write_line(typestr: str, amount: int, wprocfile):
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


def apply_retail_uom_transform(record: dict, upc_lookup: dict) -> bool:
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
    from decimal import Decimal

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
    record: dict,
    upc_lookup: dict,
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
