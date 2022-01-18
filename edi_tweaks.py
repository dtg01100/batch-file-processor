import upc_e_to_upc_a
import line_from_mtc_edi_to_dict
from datetime import datetime, timedelta
from decimal import *
import time
import mtc_edi_validator



def edi_tweak(
    edi_process,
    output_filename,
    each_upc_dict,
    pad_arec,
    arec_padding,
    append_arec,
    append_arec_text,
    force_txt_file_ext,
    calc_upc,
    invoice_date_offset,
    retail_uom
):
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
            f = open(output_filename, "wb")  # open work file, overwriting old file
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
            if invoice_date_offset != 0:
                invoice_date_string = line_from_mtc_edi_to_dict.capture_records(
                    writeable_line
                )["invoice_date"]
                if not invoice_date_string == "000000":
                    invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                    offset_invoice_date = invoice_date + timedelta(
                        days=invoice_date_offset
                    )
                    writeable_line = (
                        writeable_line[0:17]
                        + datetime.strftime(offset_invoice_date, "%m%d%y")
                        + writeable_line[23:]
                    )
            if pad_arec == "True":
                writeable_line = (
                    writeable_line[0:1] + arec_padding[0:6] + writeable_line[7:]
                )  # write "A" line
            if append_arec == "True":
                writeable_line = writeable_line.rstrip() + append_arec_text + "\r\n"
        if writeable_line.startswith("B"):
            b_rec_edi_dict = input_edi_dict
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
                        b_rec_edi_dict["unit_cost"] = str(Decimal(float(b_rec_edi_dict['unit_cost'].strip()) / float(b_rec_edi_dict['unit_multiplier'].strip())).quantize(Decimal('.01'))).replace(".", "")[-6:].rjust(6,'0')
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
                "\r\n")
            )
        f.write(writeable_line.encode())
    else:
        f.write(chr(26).encode())

    f.close()  # close output file
    return output_filename
