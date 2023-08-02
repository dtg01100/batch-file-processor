import upc_e_to_upc_a
import line_from_mtc_edi_to_dict
from query_runner import query_runner
from datetime import datetime, timedelta
from decimal import *
import time



def edi_tweak(
    edi_process,
    output_filename,
    each_upc_dict,
    parameters_dict,
    settings_dict
):

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
    force_each_upc = parameters_dict['force_each_upc']

    class cRecGenerator:
        def __init__(self, settings_dict) -> None:
            self.query_object = query_runner(
                settings_dict["as400_username"],
                settings_dict["as400_password"],
                settings_dict["as400_address"],
                f"{settings_dict['odbc_driver']}",
            )
            self._invoice_number = 0
            self.unappended_records = False

        def set_invoice_number(self, invoice_number):
            self._invoice_number = invoice_number
            self.unappended_records = True

        def fetch_splitted_sales_tax_totals(self, procfile):
            qry_ret_non_prepaid, qry_ret_prepaid = self.query_object.run_arbitrary_query(
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
            def _write_line(typestr:str, amount:int, wprocfile):
                descstr = typestr.ljust(25, " ")
                if amount < 0:
                    amount_builder = amount - (amount * 2)
                else:
                    amount_builder = amount
                
                amountstr = str(amount_builder).rjust(8, "0")
                if amount < 0:
                    temp_amount_list = amountstr.split()
                    temp_amount_list[0] = "-"
                    amountstr = "".join(temp_amount_list)
                linebuilder = f"CTAB{decstr}{amountstr}"
                wprocfile.write(linebuilder)
            if qry_ret_prepaid != 0:
                _write_line("Prepaid Sales Tax", qry_ret_prepaid, procfile)
            if qry_ret_non_prepaid != 0:
                _write_line("Sales Tax", qry_ret_non_prepaid, procfile)
            self.unappended_records = False


    work_file = None
    read_attempt_counter = 1
    while work_file is None:
        try:
            work_file = open(edi_process)  # open work file, overwriting old file
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

    f = None

    write_attempt_counter = 1
    while f is None:
        try:
            f = open(output_filename, "w", newline='\r\n')  # open work file, overwriting old file
        except Exception as error:
            if write_attempt_counter >= 5:
                time.sleep(write_attempt_counter*write_attempt_counter)
                write_attempt_counter += 1
                print(f"retrying open {output_filename}")
            else:
                print(f"error opening file for write {error}")
                raise

    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
        writeable_line = line
        if writeable_line.startswith("A"):
            a_rec_edi_dict = input_edi_dict
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
                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                a_rec_edi_dict['invoice_date'] = datetime.strftime(invoice_date, invoice_date_custom_format_string)
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
                a_rec_line_builder.append(append_arec_text)
            a_rec_line_builder.append("\n")
            writeable_line = "".join(a_rec_line_builder)
        if writeable_line.startswith("B"):
            b_rec_edi_dict = input_edi_dict
            try:
                if force_each_upc:
                    b_rec_edi_dict['upc_number'] = each_upc_dict[int(b_rec_edi_dict['vendor_item'].strip())]
            except KeyError:
                b_rec_edi_dict['upc_number'] = ""
            if retail_uom:
                edi_line_pass = False
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
                        each_upc_string = each_upc_dict[item_number][:11].ljust(11)
                    except KeyError:
                        each_upc_string = "           "
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
                            upc_e_to_upc_a.calc_check_digit(proposed_upc)
                        )
                    else:
                        if len(str(proposed_upc)) == 8:
                            b_rec_edi_dict['upc_number'] = str(
                                upc_e_to_upc_a.convert_UPCE_to_UPCA(proposed_upc)
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
                b_rec_edi_dict["parent_item_number"],
                "\n")
            )
        f.write(writeable_line)
    else:
        f.write(chr(26))

    f.close()  # close output file
    return output_filename
