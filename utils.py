from datetime import datetime
import os
from query_runner import query_runner

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
        if self.query_object is None:
            raise RuntimeError("Database connection could not be established.")
        qry_return = self.query_object.run_arbitrary_query(qry_str)
        return qry_return

    def fetch_po(self, invoice_number):
        if invoice_number == self.last_invoice_number:
            return self.po
        else:
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
            ohhst.BTHHNB = {str(int(invoice_number))}
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
            qry = f"""
                SELECT
                    BUHUNB,
                    --lineno
                    BUHXTX
                    -- u/m desc
                FROM
                    dacdata.odhst odhst
                WHERE
                    odhst.BUHHNB = {str(int(invno))}
            """
            qry_ret = self._run_qry(qry)
            self.uom_lut = dict(qry_ret)
            self.last_invno = invno
        try:
            return self.uom_lut[lineno + 1]
        except KeyError as error:
            try:
                if int(uommult) > 1:
                    qry = f"""select dsanrep.ANB9TX
                            from dacdata.dsanrep dsanrep
                            where dsanrep.ANBACD = {str(int(itemno))}"""
                else:
                    qry = f"""select dsanrep.ANB8TX
                            from dacdata.dsanrep dsanrep
                            where dsanrep.ANBACD = {str(int(itemno))}"""
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
    print(f"DEBUG: Converting dacstr='{dacstr}'")
    if dacstr.strip() == "":
        return 0
    if dacstr.startswith('-'):
        result = -int(dacstr[1:])
    else:
        result = int(dacstr)
    print(f"DEBUG: Converted dacstr='{dacstr}' to result={result}")
    return result


def convert_to_price(value):
    return (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0") + "." + value[-2:]


def dactime_from_datetime(date_time: datetime) -> str:
    dactime_date_century_digit = str(int(datetime.strftime(date_time, "%Y")[:2]) - 19)
    dactime_date = dactime_date_century_digit + str(
        date_time.date().strftime("%y%m%d")
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
        line = work_file.readline()
        print(f"DEBUG: Read line='{line.strip()}'")
        fields = capture_records(line)
        if fields is None or fields.get("record_type") != 'A':
            raise ValueError("[Invoice Type Detection]: No A record found at the start of the file")
        invoice_total = fields["invoice_total"].strip()
        print(f"DEBUG: Raw invoice_total='{invoice_total}'")
        interpreted_total = dac_str_int_to_int(invoice_total)
        print(f"DEBUG: invoice_total='{invoice_total}', interpreted_total={interpreted_total}")
        return interpreted_total < 0

def capture_records(line):
    if line.startswith("A"):
        fields = {
            "record_type":line[0],
            "cust_vendor":line[1:7],
            "invoice_number":line[7:17],
            "invoice_date":line[17:23],
            "invoice_total":line[23:34],  # 11 chars for invoice_total
            }
        print(f"DEBUG: Extracted fields={fields}")
        return fields
    elif line.startswith("B"):
        fields = {
            "record_type":line[0],
            "upc_number":line[1:12],
            "description":line[12:37],
            "vendor_item":line[37:43],
            "unit_cost":line[43:49],
            "combo_code":line[49:51],
            "unit_multiplier":line[51:57],
            "qty_of_units":line[57:62],
            "suggested_retail_price":line[62:67],
            "price_multi_pack": line[67:70],
            "parent_item_number": line[70:76],
            }
        return fields
    elif line.startswith("C"):
        fields = {
            "record_type":line[0],
            "charge_type":line[1:4],
            "description":line[4:29],
            "amount":line[29:38],
            }
        return fields
    elif line.startswith(""):
        return None
    else:
        raise Exception("Not An EDI")


def calc_check_digit(value):
    """Calculate check digit for UPCA and UPCE codes."""
    value_str = str(value)
    # If UPC-E (8 digits), expand to UPC-A (11 digits) if possible
    if len(value_str) == 8:
        # Try to expand using convert_UPCE_to_UPCA if available
        try:
            from utils import convert_UPCE_to_UPCA
            upca = convert_UPCE_to_UPCA(value_str)
            if upca and len(upca) == 12:
                value_str = upca[:-1]  # Use first 11 digits
        except Exception as e:
            print(f"DEBUG: Could not expand UPC-E: {e}")
    # Pad to 11 digits for UPC-A if needed
    if len(value_str) < 11:
        value_str = value_str.zfill(11)
    print(f"DEBUG: Starting calculation for value: {value_str}")
    check_digit = 0
    for i, char in enumerate(value_str):
        digit = int(char)
        if (i % 2) == 0:  # Odd position from the left (0-based)
            check_digit += digit * 3
            print(f"DEBUG: Adding {digit * 3} (odd position, index {i}) to check_digit, new value: {check_digit}")
        else:
            check_digit += digit
            print(f"DEBUG: Adding {digit} (even position, index {i}) to check_digit, new value: {check_digit}")
    check_digit = (10 - (check_digit % 10)) % 10
    print(f"DEBUG: Final calculated check digit for {value_str} is {check_digit}")
    return check_digit


def convert_UPCE_to_UPCA(upce_value):
    """Convert a UPC-E code to a UPC-A code."""
    upce_len = len(upce_value)
    # If already 11 or 12 digits, treat as UPC-A
    if upce_len == 12 and upce_value.isdigit():
        return upce_value
    if upce_len == 11 and upce_value.isdigit():
        check_digit = calc_check_digit(upce_value)
        return upce_value + str(check_digit)
    # Only convert 6, 7, or 8 digit UPC-E
    if upce_len == 6:
        middle_digits = upce_value
    elif upce_len == 7:
        middle_digits = upce_value[:6]
    elif upce_len == 8:
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
        for line_mum, line in enumerate(work_file_lined):  # iterate over work file contents
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                prepend_letters = col_to_excel(count)
                line_dict = capture_records(writeable_line)
                if line_dict is None:
                    continue
                if int(line_dict['invoice_total']) < 0:
                    file_name_suffix = '.cr'
                else:
                    file_name_suffix = '.inv'
                if len(edi_send_list) != 0 and f is not None:
                    f.close()
                file_name_prefix = prepend_letters + "_"
                if parameters_dict['prepend_date_files']:
                    datetime_from_arec = datetime.strptime(line_dict['invoice_date'], "%m%d%y")
                    inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
                    file_name_prefix = inv_date + "_" + file_name_prefix
                output_file_path = os.path.join(work_directory, file_name_prefix + os.path.basename(edi_process) + file_name_suffix)
                edi_send_list.append((output_file_path, file_name_prefix, file_name_suffix))
                f = open(output_file_path, 'wb')
            if f is not None:
                f.write(writeable_line.replace('\n', "\r\n").encode())
                write_counter += 1
        if f is not None:
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
        os.remove(os.path.join(folder_path, min(os.listdir(folder_path),
                                                key=lambda f: os.path.getctime("{}/{}".format(folder_path, f)))))
