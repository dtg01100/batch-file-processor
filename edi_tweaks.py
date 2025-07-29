import time
from datetime import datetime, timedelta
from decimal import Decimal

import utils
from query_runner import query_runner

class poFetcher:
    def __init__(self, settings_dict):
        self.query_object = None
        self.settings = settings_dict

    def _db_connect(self):
        import query_runner
        self.query_object = query_runner.query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def fetch_po_number(self, invoice_number):
        if self.query_object is None:
            self._db_connect()
        if self.query_object is None:
            raise RuntimeError("Database connection could not be established.")
        qry_ret = self.query_object.run_arbitrary_query(
            f"""
            select ohhst.bte4cd
            from dacdata.ohhst ohhst
            where ohhst.bthhnb = {int(invoice_number)}
            """
        )
        if len(qry_ret) == 0:
            ret_str = "no_po_found    "
        else:
            ret_str = str(qry_ret[0][0])
        return ret_str

class cRecGenerator:
    def __init__(self, settings_dict):
        self.query_object = None
        self._invoice_number = "0"
        self.unappended_records = False
        self.settings = settings_dict

    def _db_connect(self):
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def set_invoice_number(self, invoice_number):
        self._invoice_number = invoice_number
        self.unappended_records = True

    def fetch_splitted_sales_tax_totals(self, procfile):
        if self.query_object is None:
            self._db_connect()
        if self.query_object is None:
            raise RuntimeError("Database connection could not be established.")
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
        def _write_line(typestr:str, amount:int, wprocfile):
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
            wprocfile.write(linebuilder)
        # print(qry_ret_non_prepaid,qry_ret_prepaid)
        if qry_ret_prepaid != 0 and qry_ret_prepaid is not None:
            _write_line("Prepaid Sales Tax", qry_ret_prepaid, procfile)
        if qry_ret_non_prepaid != 0 and qry_ret_non_prepaid is not None:
            _write_line("Sales Tax", qry_ret_non_prepaid, procfile)
        self.unappended_records = False


def edi_tweak(
    edi_process,
    output_filename,
    settings_dict,
    parameters_dict,
    upc_dict,
):
    """
    Processes an EDI file and writes the output to a specified file.

    Note:
        The returned `output_filename` may be modified (e.g., '.txt' appended) based on parameters.

    Args:
        edi_process (str): Path to the input EDI file.
        output_filename (str): Path to the output file (may be modified).
        settings_dict (dict): Settings for database and processing.
        parameters_dict (dict): Parameters controlling processing behavior.
        upc_dict (dict): UPC lookup dictionary.

    Returns:
        str: The (possibly modified) output filename.
    """

    pad_arec = parameters_dict['pad_a_records']
    arec_padding = parameters_dict['a_record_padding']
    arec_padding_len = parameters_dict['a_record_padding_length']
    append_arec = parameters_dict['append_a_records']
    append_arec_text = parameters_dict['a_record_append_text']
    invoice_date_custom_format = parameters_dict['invoice_date_custom_format']
    invoice_date_custom_format_string = parameters_dict['invoice_date_custom_format_string']
    force_txt_file_ext = parameters_dict['force_txt_file_ext']
    calc_upc = parameters_dict['calculate_upc_check_digit']
    invoice_date_offset = parameters_dict['invoice_date_offset']
    retail_uom = parameters_dict['retail_uom']
    override_upc = parameters_dict['override_upc_bool']
    override_upc_level = parameters_dict['override_upc_level']
    override_upc_category_filter = parameters_dict['override_upc_category_filter']
    split_prepaid_sales_tax_crec = parameters_dict['split_prepaid_sales_tax_crec']



    work_file = None
    read_attempt_counter = 1
    while work_file is None:
        try:
            work_file = open(edi_process, encoding="utf-8")  # open work file, overwriting old file
        except Exception as error:
            if read_attempt_counter >= 5:
                time.sleep(read_attempt_counter*read_attempt_counter)
                read_attempt_counter += 1
                print(f"retrying open {edi_process}")
            else:
                print(f"error opening file for read {error}")
                raise
    # work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    if force_txt_file_ext == "True":
        output_filename = output_filename + ".txt"

    write_attempt_counter = 1
    file_opened = False
    while not file_opened:
        try:
            with open(output_filename, "w", newline='\r\n') as f:  # open work file, overwriting old file
                file_opened = True

                crec_appender = cRecGenerator(settings_dict)
                po_fetcher = poFetcher(settings_dict)

                for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
                    input_edi_dict = utils.capture_records(line)
                    writeable_line = line.strip('\n')  # remove trailing newline character
                    if writeable_line.startswith("A") and input_edi_dict is not None:
                        a_rec_edi_dict = input_edi_dict
                        crec_appender.set_invoice_number(int(a_rec_edi_dict['invoice_number']))
                        if invoice_date_offset != 0:
                            invoice_date_string = a_rec_edi_dict["invoice_date"]
                            if not invoice_date_string == "000000":
                                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                                print(invoice_date_offset)
                                offset_invoice_date = invoice_date + timedelta(
                                    days=invoice_date_offset
                                )
                                a_rec_edi_dict['invoice_date'] = datetime.strftime(offset_invoice_date, "%m%d%y")
                        if invoice_date_custom_format:
                            invoice_date_string = a_rec_edi_dict["invoice_date"]
                            try:
                                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                                a_rec_edi_dict['invoice_date'] = datetime.strftime(invoice_date, invoice_date_custom_format_string)
                            except ValueError:
                                a_rec_edi_dict['invoice_date'] = "ERROR"
                        if pad_arec == "True":
                            padding = arec_padding
                            fill = ' '
                            align = '<'
                            width = arec_padding_len
                            a_rec_edi_dict['cust_vendor'] = f'{padding:{fill}{align}{width}}'
                        a_rec_line_builder = [a_rec_edi_dict['record_type'],
                                a_rec_edi_dict['cust_vendor'],
                                a_rec_edi_dict['invoice_number'],
                                a_rec_edi_dict['invoice_date'],
                                a_rec_edi_dict['invoice_total']]
                        if append_arec == "True":
                            if "%po_str%" in append_arec_text:
                                temp_append_arec_text = append_arec_text.replace("%po_str%", po_fetcher.fetch_po_number(a_rec_edi_dict['invoice_number']))
                                a_rec_line_builder.append(temp_append_arec_text)
                            else:
                                a_rec_line_builder.append(append_arec_text)
                        a_rec_line_builder.append('\n')
                        writeable_line = "".join(a_rec_line_builder)
                        f.write(writeable_line)
                    if writeable_line.startswith("B"):
                        if not input_edi_dict:
                            print(f"line {line_num} is not a valid B record, skipping")
                            raise ValueError(f"line {line_num} is not a valid B record, skipping")
                        b_rec_edi_dict = input_edi_dict
                        try:
                            if override_upc:
                                if override_upc_category_filter == "ALL":
                                    upc_entry = upc_dict.get(int(b_rec_edi_dict['vendor_item'].strip()))
                                    if upc_entry is not None:
                                        b_rec_edi_dict['upc_number'] = upc_entry[override_upc_level]
                                    else:
                                        b_rec_edi_dict['upc_number'] = ""
                                else:
                                    if upc_dict[int(b_rec_edi_dict['vendor_item'].strip())][0] in override_upc_category_filter.split(","):
                                        b_rec_edi_dict['upc_number'] = upc_dict[int(b_rec_edi_dict['vendor_item'].strip())][override_upc_level]
                        except KeyError:
                            b_rec_edi_dict['upc_number'] = ""
                        if retail_uom:
                            edi_line_pass = False
                            item_number = None
                            each_upc_string = ""  # Ensure variable is always defined
                            try:
                                item_number = int(b_rec_edi_dict['vendor_item'].strip())
                                float(b_rec_edi_dict['unit_cost'].strip())
                                test_unit_multiplier = int(b_rec_edi_dict['unit_multiplier'].strip())
                                if test_unit_multiplier == 0:
                                    raise ValueError
                                int(b_rec_edi_dict['qty_of_units'].strip())
                                edi_line_pass = True
                            except Exception:
                                print("cannot parse b record field, skipping")
                            if edi_line_pass:
                                try:
                                    each_upc_string = upc_dict[item_number][1][:11].ljust(11)
                                except KeyError:
                                    original_unit_cost = Decimal(b_rec_edi_dict['unit_cost'].strip())
                                    unit_multiplier = Decimal(b_rec_edi_dict['unit_multiplier'].strip())
                                    unit_cost_in_dollars = (original_unit_cost / 100) / unit_multiplier
                                    b_rec_edi_dict["unit_cost"] = str(unit_cost_in_dollars.quantize(Decimal('.01'))).replace(".", "").zfill(6)
                                    unit_cost_rounded = unit_cost_in_dollars.quantize(Decimal('.01'))
                                    unit_cost_str = str(unit_cost_rounded).replace(".", "")
                                    b_rec_edi_dict["unit_cost"] = unit_cost_str[-6:].rjust(6, '0')
                                try:
                                    b_rec_edi_dict["unit_cost"] = str(Decimal((Decimal(b_rec_edi_dict['unit_cost'].strip()) / 100) / Decimal(b_rec_edi_dict['unit_multiplier'].strip())).quantize(Decimal('.01'))).replace(".", "")[-6:].rjust(6,'0')
                                    b_rec_edi_dict['qty_of_units'] = str(int(b_rec_edi_dict['unit_multiplier'].strip()) * int(b_rec_edi_dict['qty_of_units'].strip())).rjust(5,'0')
                                    b_rec_edi_dict['upc_number'] = each_upc_string
                                    b_rec_edi_dict['unit_multiplier'] = '000001'
                                except Exception as error:
                                    print(error)
                        if calc_upc == "True":
                            blank_upc = False
                            try:
                                _ = int(b_rec_edi_dict["upc_number"].rstrip())
                            except ValueError:
                                blank_upc = True

                            if blank_upc is False:
                                proposed_upc = b_rec_edi_dict["upc_number"].strip()
                                if len(str(proposed_upc)) == 11:
                                    b_rec_edi_dict['upc_number'] = str(proposed_upc) + str(
                                        utils.calc_check_digit(proposed_upc)
                                    )
                                else:
                                    if len(str(proposed_upc)) == 8:
                                        b_rec_edi_dict['upc_number'] = str(
                                            utils.convert_UPCE_to_UPCA(proposed_upc)
                                        )
                            else:
                                b_rec_edi_dict['upc_number'] = "            "

                        if len(writeable_line) < 77:
                            b_rec_edi_dict["parent_item_number"] = ""

                        digits_fields = [
                        "unit_cost",
                        "unit_multiplier",
                        "qty_of_units",
                        "suggested_retail_price",
                        ]

                        for field in digits_fields:
                            tempfield = b_rec_edi_dict[field].replace("-", "")
                            if len(tempfield) != len(b_rec_edi_dict[field]):
                                b_rec_edi_dict[field] = "-" + tempfield

                        writeable_line = "".join((
                            b_rec_edi_dict["record_type"],
                            b_rec_edi_dict["upc_number"],
                            b_rec_edi_dict["description"],
                            b_rec_edi_dict["vendor_item"],
                            b_rec_edi_dict["unit_cost"],
                            b_rec_edi_dict["combo_code"],
                            b_rec_edi_dict["unit_multiplier"],
                            b_rec_edi_dict["qty_of_units"],
                            b_rec_edi_dict["suggested_retail_price"],
                            b_rec_edi_dict["price_multi_pack"],
                            b_rec_edi_dict["parent_item_number"]
                        ))
                        f.write(writeable_line)
                    if writeable_line.startswith("C"):
                        if split_prepaid_sales_tax_crec and crec_appender.unappended_records and writeable_line.startswith("CTABSales Tax"):
                            crec_appender.fetch_splitted_sales_tax_totals(f)
                        else:
                            f.write(writeable_line)
        except Exception as error:
            if write_attempt_counter >= 5:
                time.sleep(write_attempt_counter*write_attempt_counter)
                write_attempt_counter += 1
                print(f"retrying open {output_filename}")
            else:
                print(f"error opening file for write {error}")
                raise
    return output_filename
